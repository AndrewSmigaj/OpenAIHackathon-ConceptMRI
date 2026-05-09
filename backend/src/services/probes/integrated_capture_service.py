#!/usr/bin/env python3
"""
IntegratedCaptureService — thin facade over SessionManager, ProbeProcessor,
and CaptureOrchestrator.

Public API is unchanged: same methods, same signatures. All existing callers
(routers, experiments endpoint) continue working without modification.
"""

import gc
import torch
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from core.parquet_writer import BatchWriter
from services.probes.probe_ids import generate_probe_id
from utils.memory_utils import cleanup_gpu_memory

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

    # ====================================================================
    # NEW UNIFIED PRIMITIVES (capture_step + generate)
    #
    # These replace capture_probe and probe_tick. Callers tokenize their
    # own input via apply_chat_template (the input shape — single message,
    # cumulative-with-cache-on-splice via HarmonyKVChain, or messages list
    # — is intrinsic to each caller), then call these primitives.
    #
    # capture_step semantics:
    #   - target_occurrence="last": one ProbeRecord per target_word at the
    #     last in-window occurrence (sentence-experiment, temporal-capture)
    #   - target_occurrence="all": one ProbeRecord per (target_word, occurrence)
    #     for every in-window occurrence (agent loop, /agent/generate)
    #   - target_position_window=(min, max): restrict target search
    #   - prompt_token_count > 0: positions >= count get capture_type="generation"
    #     (overrides metadata.capture_type for those records). Lets agent
    #     do prompt+generation labeling in one forward pass.
    #   - capture_static_substring: extra residuals at every token of the
    #     substring's last occurrence; only valid with target_occurrence="last".
    #   - target_char_offset is computed from input_text + occurrence_idx and
    #     populated on EVERY record (was previously probe_tick-only — caused
    #     last_occurrence_only filter to "always keep" sentence/temporal records).
    # ====================================================================

    def capture_step(
        self,
        session_id: str,
        token_ids: List[int],
        target_words: List[str],
        *,
        past_kv=None,
        use_cache: bool = False,
        capture_static_substring: Optional[str] = None,
        target_position_window: Optional[Tuple[int, int]] = None,
        target_occurrence: str = "last",
        prompt_token_count: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Tuple[list, any]:
        """One capture forward pass with hooks ON; finds target words; writes
        ProbeRecord(s); returns (records, new_past_kv)."""
        if metadata is None:
            metadata = {}
        if target_occurrence not in ("last", "all"):
            raise ValueError(f"target_occurrence must be 'last' or 'all', got {target_occurrence!r}")
        if capture_static_substring and target_occurrence != "last":
            raise ValueError("capture_static_substring requires target_occurrence='last'")

        # Session + writers
        self.session_mgr.validate_active_session(session_id)
        if session_id not in self.session_writers:
            self.session_writers[session_id] = SessionBatchWriters(
                session_id, self.session_mgr.data_lake_path, self.session_mgr.batch_size
            )

        # Hooks lazy
        self.orchestrator.initialize_hooks(session_id)

        # Substring positions (validated before forward pass)
        extra_positions: Optional[List[int]] = None
        if capture_static_substring:
            extra_positions = self.processor.find_substring_token_range(
                token_ids, capture_static_substring
            )
            if extra_positions is None:
                raise ValueError(
                    f"capture_static_substring '{capture_static_substring}' not found "
                    f"in tokenized input ({len(token_ids)} tokens)"
                )

        # Forward pass
        self.orchestrator.clear_captured_data()
        input_tensor = torch.tensor([token_ids], device=self.orchestrator.model.device)
        outputs, new_past_kv = self.orchestrator.run_forward_pass(
            input_tensor, past_kv, use_cache
        )
        routing_data, embedding_data, residual_data = self.orchestrator.get_captured_data()

        # input_text: caller can override (e.g. agent stores game_text); default = decoded
        decoded = self.processor.tokenizer.decode(token_ids, skip_special_tokens=True)
        input_text = metadata.get("input_text") or decoded

        def _char_offset(text: str, word: str, occurrence_idx: int) -> Optional[int]:
            start = 0
            tlow, wlow = text.lower(), word.lower()
            for i in range(occurrence_idx + 1):
                pos = tlow.find(wlow, start)
                if pos == -1:
                    return None
                if i == occurrence_idx:
                    return pos
                start = pos + 1
            return None

        records = []
        first_record_for_call = True  # extra_positions attaches to first record only

        for target_word in target_words:
            # Find ALL occurrences first (gives us absolute occurrence_idx for char_offset)
            all_positions = self.processor.find_all_word_token_positions(token_ids, target_word)
            if not all_positions:
                logger.debug(f"Target word '{target_word}' not found in token_ids")
                continue

            indexed = list(enumerate(all_positions))  # [(abs_idx, (pos, tid)), ...]

            # Apply window filter
            if target_position_window is not None:
                min_pos, max_pos = target_position_window
                indexed = [(i, (p, t)) for i, (p, t) in indexed if min_pos <= p < max_pos]

            if not indexed:
                continue

            # Pick last or all
            if target_occurrence == "last":
                indexed = indexed[-1:]

            for abs_idx, (pos, token_id) in indexed:
                # capture_type: per-position override for prompt/generation labeling
                cap_type = metadata.get("capture_type")
                if prompt_token_count > 0 and pos >= prompt_token_count:
                    cap_type = "generation"

                char_offset = _char_offset(input_text, target_word, abs_idx)

                probe_id = generate_probe_id()
                probe_data = self.processor.convert_to_schemas(
                    probe_id=probe_id, session_id=session_id,
                    input_text=input_text, target_word=target_word,
                    target_token_id=token_id, target_token_position=pos,
                    total_tokens=len(token_ids),
                    routing_data=routing_data, embedding_data=embedding_data,
                    residual_stream_data=residual_data,
                    experiment_id=metadata.get("experiment_id"),
                    sequence_id=metadata.get("sequence_id"),
                    sentence_index=metadata.get("sentence_index"),
                    label=metadata.get("label"),
                    label2=metadata.get("label2"),
                    categories=metadata.get("categories"),
                    transition_step=metadata.get("transition_step"),
                    turn_id=metadata.get("turn_id"),
                    scenario_id=metadata.get("scenario_id"),
                    capture_type=cap_type,
                    target_char_offset=char_offset,
                    extra_positions=extra_positions if first_record_for_call else None,
                )
                # Optional: attach generated_text (caller-supplied via metadata)
                gen_text = metadata.get("generated_text")
                if gen_text is not None:
                    probe_data.probe_record.generated_text = gen_text

                self.session_writers[session_id].write_probe_data(probe_data)
                self.session_mgr.record_probe_success(session_id)
                records.append(probe_data.probe_record)
                first_record_for_call = False

        # GPU cleanup — prevents allocator fragmentation accumulating across many probes
        del input_tensor, outputs
        gc.collect()
        cleanup_gpu_memory()

        return records, new_past_kv

    def generate(
        self,
        token_ids: List[int],
        max_new_tokens: int,
        *,
        attention_mask=None,
        skip_special_tokens: bool = True,
    ) -> Tuple[str, List[int]]:
        """Generation forward pass with hooks OFF. Returns (text, generated_ids).
        Wraps orchestrator.generate_continuation_with_ids; lifts hook
        management responsibility into the service tier so callers don't
        need to know about it."""
        input_tensor = torch.tensor([token_ids], device=self.orchestrator.model.device)
        text, gen_ids = self.orchestrator.generate_continuation_with_ids(
            input_tensor,
            max_new_tokens=max_new_tokens,
            attention_mask=attention_mask,
            skip_special_tokens=skip_special_tokens,
        )
        del input_tensor
        gc.collect()
        cleanup_gpu_memory()
        return text, gen_ids

    # ====================================================================
    # END NEW PRIMITIVES
    # ====================================================================

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
