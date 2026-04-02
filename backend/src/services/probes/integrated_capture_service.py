#!/usr/bin/env python3
"""
IntegratedCaptureService — thin facade over SessionManager, ProbeProcessor,
and CaptureOrchestrator.

Public API is unchanged: same methods, same signatures. All existing callers
(routers, experiments endpoint) continue working without modification.
"""

import torch
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from core.parquet_writer import BatchWriter
from services.probes.probe_ids import generate_probe_id

# Sub-components
from services.probes.session_manager import SessionManager, SessionState, SessionStatus
from services.probes.probe_processor import ProbeProcessor, ProbeCapture
from services.probes.capture_orchestrator import CaptureOrchestrator

# Schema imports needed by SessionBatchWriters
from schemas.tokens import ProbeRecord
from schemas.routing import RoutingRecord
from schemas.embedding import EmbeddingRecord
from schemas.residual_stream import ResidualStreamState

logger = logging.getLogger(__name__)


class SessionBatchWriters:
    """Coordinated batch writers for all 5 schemas."""

    def __init__(self, session_id: str, data_lake_path: str, batch_size: int = 1000):
        self.session_id = session_id
        self.session_dir = Path(data_lake_path) / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.tokens_writer = BatchWriter(self.session_dir / "tokens.parquet", batch_size)
        self.routing_writer = BatchWriter(self.session_dir / "routing.parquet", batch_size)
        self.embedding_writer = BatchWriter(self.session_dir / "embeddings.parquet", batch_size)
        self.residual_stream_writer = BatchWriter(self.session_dir / "residual_streams.parquet", batch_size)

        self.writers_active = True

    def write_probe_data(self, probe_data: ProbeCapture) -> None:
        if not self.writers_active:
            raise RuntimeError("Writers have been closed")
        try:
            self.tokens_writer.add_record(probe_data.probe_record)
            for r in probe_data.routing_records:
                self.routing_writer.add_record(r)
            for r in probe_data.embedding_records:
                self.embedding_writer.add_record(r)
            for r in probe_data.residual_stream_records:
                self.residual_stream_writer.add_record(r)
        except Exception as e:
            logger.error(f"Failed to write probe {probe_data.probe_id}: {e}")
            raise

    def flush_all(self) -> None:
        if not self.writers_active:
            return
        self.tokens_writer.flush()
        self.routing_writer.flush()
        self.embedding_writer.flush()
        self.residual_stream_writer.flush()

    def close_all(self) -> None:
        if not self.writers_active:
            return
        self.flush_all()
        self.writers_active = False
        logger.debug(f"Closed all batch writers for session {self.session_id}")


class IntegratedCaptureService:
    """
    Facade coordinating session management, probe processing, and model capture.

    Delegates to:
      - SessionManager: session lifecycle (create, track, restore, finalize, abort)
      - ProbeProcessor: tokenization and schema conversion
      - CaptureOrchestrator: model inference, hooks, GPU memory
    """

    def __init__(self, model, tokenizer, layers_to_capture: Optional[List[int]] = None,
                 *, data_lake_path: str, batch_size: int = 1000,
                 wordnet_miner=None, adapter=None):
        self.adapter = adapter

        if layers_to_capture is None:
            layers_to_capture = adapter.layers_range() if adapter else list(range(24))

        topology = adapter.topology if adapter else None
        self.session_mgr = SessionManager(
            data_lake_path=data_lake_path,
            batch_size=batch_size,
            layers_to_capture=layers_to_capture,
            model_name=topology.model_name if topology else "gpt-oss-20b",
            num_experts=topology.num_experts if topology else 0,
            num_layers=topology.num_layers if topology else 0,
            hidden_size=topology.hidden_size if topology else 0,
        )
        self.processor = ProbeProcessor(tokenizer, adapter, layers_to_capture)
        self.orchestrator = CaptureOrchestrator(model, tokenizer, adapter, layers_to_capture)
        self.session_writers: Dict[str, SessionBatchWriters] = {}

        logger.info(f"IntegratedCaptureService initialized for layers {layers_to_capture}")

    # --- Property delegates for router compatibility ---
    @property
    def data_lake_path(self):
        return self.session_mgr.data_lake_path

    @property
    def sessions_dir(self):
        return self.session_mgr.sessions_dir

    @property
    def active_sessions(self):
        return self.session_mgr.active_sessions

    def create_sentence_session(
        self, session_name: str, total_probes: int, target_word: str,
        labels: List[str], experiment_id: str = None, sentence_set_name: str = None,
    ) -> str:
        session_id = self.session_mgr.create_session(
            session_name, total_probes, target_word, labels, experiment_id, sentence_set_name
        )
        self.session_writers[session_id] = SessionBatchWriters(
            session_id, self.session_mgr.data_lake_path, self.session_mgr.batch_size
        )
        return session_id

    def get_session_status(self, session_id: str) -> SessionStatus:
        return self.session_mgr.get_session_status(session_id)

    def capture_probe(
        self, session_id: str, input_text: str, target_word: str,
        target_token_position: int = None,
        context_word: str = None, context_token_position: int = None,
        past_key_values=None, use_cache: bool = False,
        experiment_id: str = None, sequence_id: str = None,
        sentence_index: int = None, label: str = None,
        label2: str = None,
        categories: Optional[Dict[str, str]] = None,
        transition_step: int = None,
        generate_output: bool = False,
    ) -> Tuple[str, any]:
        # 1. Validate session (restores from disk if needed)
        session_status = self.session_mgr.validate_active_session(session_id)
        if session_id not in self.session_writers:
            self.session_writers[session_id] = SessionBatchWriters(
                session_id, self.session_mgr.data_lake_path, self.session_mgr.batch_size
            )

        probe_id = generate_probe_id()
        session_status.current_probe = probe_id

        try:
            # 2. Initialize hooks (lazy)
            self.orchestrator.initialize_hooks(session_id)

            # 3. Tokenize and find positions
            token_ids = self.processor.tokenizer.encode(input_text, add_special_tokens=False)
            total_tokens = len(token_ids)

            if target_token_position is None:
                target_token_position, target_token_id = self.processor.find_word_token_position(
                    token_ids, target_word
                )
            else:
                target_token_id = token_ids[target_token_position]

            context_token_pos = None
            if context_word is not None:
                if context_token_position is not None:
                    context_token_pos = context_token_position
                else:
                    context_token_pos, _ = self.processor.find_word_token_position(token_ids, context_word)

            # 4. Clear previous data and run forward pass
            self.orchestrator.clear_captured_data()
            input_tensor = torch.tensor([token_ids], device=self.orchestrator.model.device)
            outputs, new_past_key_values = self.orchestrator.run_forward_pass(
                input_tensor, past_key_values, use_cache
            )

            # 5. Get captured data and convert to schemas
            routing_data, embedding_data, residual_data = self.orchestrator.get_captured_data()
            probe_data = self.processor.convert_to_schemas(
                probe_id=probe_id, session_id=session_id,
                input_text=input_text, target_word=target_word,
                target_token_id=target_token_id, target_token_position=target_token_position,
                total_tokens=total_tokens,
                routing_data=routing_data, embedding_data=embedding_data,
                residual_stream_data=residual_data,
                context_word=context_word, context_token_position=context_token_pos,
                experiment_id=experiment_id, sequence_id=sequence_id,
                sentence_index=sentence_index, label=label, label2=label2,
                categories=categories, transition_step=transition_step,
            )

            # 6. Generate continuation if requested
            if generate_output:
                try:
                    probe_data.probe_record.generated_text = self.orchestrator.generate_continuation(
                        input_tensor
                    )
                except Exception as e:
                    logger.error(f"Generation failed for probe {probe_id}: {e}", exc_info=True)

            # 7. Write to data lake
            self.session_writers[session_id].write_probe_data(probe_data)

            # 8. Update progress
            self.session_mgr.record_probe_success(session_id)

            ctx_info = f", context='{context_word}'" if context_word else ""
            logger.info(
                f"Captured probe {probe_id}: '{target_word}' in "
                f"'{input_text[:40]}...'{ctx_info} (session {session_id})"
            )
            return probe_id, new_past_key_values

        except Exception as e:
            self.session_mgr.record_probe_failure(session_id, str(e))
            logger.error(f"Failed to capture '{target_word}' in '{input_text[:40]}...': {e}")
            raise

    def finalize_session(self, session_id: str):
        if session_id not in self.session_mgr.active_sessions:
            raise ValueError(f"Session {session_id} not active")

        try:
            if session_id in self.session_writers:
                self.session_writers[session_id].close_all()
                del self.session_writers[session_id]

            manifest = self.session_mgr.finalize_session(session_id)
            self.orchestrator.cleanup_hooks()
            return manifest

        except Exception as e:
            if session_id in self.session_mgr.active_sessions:
                status = self.session_mgr.active_sessions[session_id]
                status.state = SessionState.FAILED
                status.error_message = str(e)
            logger.error(f"Failed to finalize session {session_id}: {e}")
            raise

    def abort_session(self, session_id: str) -> None:
        self.session_mgr.abort_session(session_id)
        if session_id in self.session_writers:
            self.session_writers[session_id].close_all()
            del self.session_writers[session_id]
        self.orchestrator.cleanup_hooks()
