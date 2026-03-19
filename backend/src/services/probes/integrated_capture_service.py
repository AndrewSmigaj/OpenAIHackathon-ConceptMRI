#!/usr/bin/env python3
"""
IntegratedCaptureService - Complete MoE capture with session management.
Coordinates all 5 schemas with proper lifecycle management and error handling.
"""

import torch
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
import json
from datetime import datetime
import uuid

# Schema imports
from schemas.tokens import ProbeRecord, create_probe_record
from schemas.routing import RoutingRecord, create_routing_record
from schemas.embedding import EmbeddingRecord, create_embedding_record
from schemas.residual_stream import ResidualStreamState, create_residual_stream_state
from schemas.capture_manifest import CaptureManifest, create_capture_manifest

# Core services
from services.probes.routing_capture import EnhancedRoutingCapture
from services.probes.probe_ids import generate_probe_id, generate_capture_id
from core.parquet_writer import BatchWriter


class SessionState(Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class SessionStatus:
    """Session status information for UI integration."""
    session_id: str
    state: SessionState
    total_pairs: int
    completed_pairs: int
    failed_pairs: int
    current_probe: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        """Calculate completion percentage."""
        if self.total_pairs == 0:
            return 0.0
        return (self.completed_pairs / self.total_pairs) * 100.0


@dataclass
class ProbeCapture:
    """Complete capture data for a single probe."""
    probe_id: str
    session_id: str

    # Schema records
    probe_record: ProbeRecord
    routing_records: List[RoutingRecord]
    embedding_records: List[EmbeddingRecord]
    residual_stream_records: List[ResidualStreamState]


class SessionBatchWriters:
    """Coordinated batch writers for all 5 schemas."""

    def __init__(self, session_id: str, data_lake_path: str = "data/lake", batch_size: int = 1000):
        self.session_id = session_id
        self.session_dir = Path(data_lake_path) / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize batch writers for all schemas
        self.tokens_writer = BatchWriter(self.session_dir / "tokens.parquet", batch_size)
        self.routing_writer = BatchWriter(self.session_dir / "routing.parquet", batch_size)
        self.embedding_writer = BatchWriter(self.session_dir / "embeddings.parquet", batch_size)
        self.residual_stream_writer = BatchWriter(self.session_dir / "residual_streams.parquet", batch_size)

        self.writers_active = True

    def write_probe_data(self, probe_data: ProbeCapture) -> None:
        """Write complete probe capture to all relevant schemas."""
        if not self.writers_active:
            raise RuntimeError("Writers have been closed")

        try:
            # Write to each schema
            self.tokens_writer.add_record(probe_data.probe_record)

            for routing_record in probe_data.routing_records:
                self.routing_writer.add_record(routing_record)

            for embedding_record in probe_data.embedding_records:
                self.embedding_writer.add_record(embedding_record)

            for residual_record in probe_data.residual_stream_records:
                self.residual_stream_writer.add_record(residual_record)

        except Exception as e:
            print(f"Failed to write probe {probe_data.probe_id}: {e}")
            raise

    def flush_all(self) -> None:
        """Flush all batch writers."""
        if not self.writers_active:
            return

        self.tokens_writer.flush()
        self.routing_writer.flush()
        self.embedding_writer.flush()
        self.residual_stream_writer.flush()

    def close_all(self) -> None:
        """Close all batch writers and mark inactive."""
        if not self.writers_active:
            return

        self.flush_all()
        self.writers_active = False
        print(f"Closed all batch writers for session {self.session_id}")


class IntegratedCaptureService:
    """
    Integrated MoE capture service with session management.
    Coordinates EnhancedRoutingCapture with schema conversion and batch writing.
    """

    def __init__(self, model, tokenizer, layers_to_capture: Optional[List[int]] = None,
                 data_lake_path: str = "data/lake", batch_size: int = 1000,
                 wordnet_miner=None,
                 adapter=None):
        self.model = model
        self.tokenizer = tokenizer
        self.adapter = adapter
        self.data_lake_path = data_lake_path
        self.batch_size = batch_size

        # Use adapter for defaults, fall back to legacy hardcoded values
        if layers_to_capture is None:
            layers_to_capture = adapter.layers_range() if adapter else list(range(24))
        self.layers_to_capture = layers_to_capture

        # Session management
        self.active_sessions: Dict[str, SessionStatus] = {}
        self.session_writers: Dict[str, SessionBatchWriters] = {}
        self.routing_capture: Optional[EnhancedRoutingCapture] = None

        # Session state persistence
        self.sessions_dir = Path(data_lake_path) / "_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        print(f"IntegratedCaptureService initialized for layers {self.layers_to_capture}")

    def create_sentence_session(
        self,
        session_name: str,
        total_probes: int,
        target_word: str,
        labels: List[str],
        experiment_id: str = None,
    ) -> str:
        """
        Create a session for sentence-based experiments.

        Args:
            session_name: Human-readable name
            total_probes: Number of sentences to capture
            target_word: Shared target word for all sentences
            labels: List of labels (e.g. ["aquatic", "military"])
            experiment_id: Optional experiment identifier

        Returns:
            Unique session ID
        """
        session_id = generate_capture_id("session")

        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=total_probes,
            completed_pairs=0,
            failed_pairs=0
        )

        batch_writers = SessionBatchWriters(session_id, self.data_lake_path, self.batch_size)

        self.active_sessions[session_id] = session_status
        self.session_writers[session_id] = batch_writers

        session_metadata = {
            "session_id": session_id,
            "session_name": session_name,
            "target_word": target_word,
            "labels": labels,
            "layers_captured": self.layers_to_capture,
            "total_pairs": total_probes,
            "model_name": self.adapter.topology.model_name if self.adapter else "gpt-oss-20b",
            "created_at": datetime.now().isoformat(),
            "state": session_status.state.value,
            "experiment_type": "sentence",
            "experiment_id": experiment_id,
        }

        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_metadata, f, indent=2)

        print(f"Created sentence session {session_id} ({session_name}): {total_probes} probes")
        return session_id

    def get_session_status(self, session_id: str) -> SessionStatus:
        """Get current session status."""
        if session_id not in self.active_sessions:
            # Try to load from persistence
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    metadata = json.load(f)
                    return SessionStatus(
                        session_id=session_id,
                        state=SessionState(metadata["state"]),
                        total_pairs=metadata["total_pairs"],
                        completed_pairs=metadata.get("completed_pairs", 0),
                        failed_pairs=metadata.get("failed_pairs", 0)
                    )
            else:
                raise ValueError(f"Session {session_id} not found")

        return self.active_sessions[session_id]

    def _initialize_routing_capture(self, session_id: str) -> None:
        """Initialize routing capture for session if needed."""
        if self.routing_capture is None:
            self.routing_capture = EnhancedRoutingCapture(self.model, self.layers_to_capture, adapter=self.adapter)
            self.routing_capture.register_hooks()
            print(f"Registered hooks for session {session_id}")

    def _cleanup_routing_capture(self) -> None:
        """Clean up routing capture hooks."""
        if self.routing_capture is not None:
            self.routing_capture.remove_hooks()
            self.routing_capture = None

            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("Cleaned up routing capture and GPU memory")

    def _find_word_token_position(self, token_ids: list, word: str) -> Tuple[int, int]:
        """
        Find a word's token position in a tokenized sequence.

        Returns (position, token_id). Picks last occurrence if multiple matches.
        Handles BPE whitespace sensitivity by trying both 'word' and ' word'.

        Raises ValueError if word is multi-token or not found.
        """
        # Try tokenizing with and without leading space (BPE sensitivity)
        word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
        space_word_tokens = self.tokenizer.encode(f" {word}", add_special_tokens=False)

        # Determine which tokenization to use
        if len(word_tokens) == 1:
            target_token_id = word_tokens[0]
        elif len(space_word_tokens) == 1:
            target_token_id = space_word_tokens[0]
        else:
            raise ValueError(
                f"Word '{word}' must be a single token. "
                f"Got {len(word_tokens)} tokens without space, "
                f"{len(space_word_tokens)} tokens with space."
            )

        # Find last occurrence in the sequence
        positions = [i for i, tid in enumerate(token_ids) if tid == target_token_id]
        if not positions:
            # Try the other tokenization as fallback
            alt_id = space_word_tokens[0] if len(word_tokens) == 1 else word_tokens[0]
            positions = [i for i, tid in enumerate(token_ids) if tid == alt_id]
            if positions:
                target_token_id = alt_id

        if not positions:
            raise ValueError(f"Word '{word}' (token_id={target_token_id}) not found in tokenized input")

        return positions[-1], target_token_id  # Last occurrence

    def capture_probe(
        self, session_id: str, input_text: str, target_word: str,
        target_token_position: int = None,
        context_word: str = None,
        context_token_position: int = None,
        past_key_values=None, use_cache: bool = False,
        experiment_id: str = None, sequence_id: str = None,
        sentence_index: int = None, label: str = None,
        transition_step: int = None,
    ) -> Tuple[str, any]:
        """
        Capture a probe for any-length text input, tracking a target word.

        Args:
            session_id: Active session ID
            input_text: Full text to feed the model
            target_word: Word to track within input_text
            target_token_position: Optional explicit position (auto-detected if None)
            context_word: Optional disambiguating word to also track
            context_token_position: Optional explicit position for context word
            past_key_values: KV cache from previous capture (for temporal experiments)
            use_cache: Whether to return updated KV cache
            experiment_id..transition_step: Temporal experiment metadata
            label: Optional label for this probe (e.g. "aquatic", "military")

        Returns:
            Tuple of (probe_id, past_key_values or None)
        """
        if session_id not in self.active_sessions:
            # Try to load session from disk and restore it
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    metadata = json.load(f)
                if metadata["state"] == "active":
                    self._restore_session(session_id, metadata)
                else:
                    raise ValueError(f"Session {session_id} is not active (state: {metadata['state']})")
            else:
                raise ValueError(f"Session {session_id} not found")

        session_status = self.active_sessions[session_id]
        if session_status.state != SessionState.ACTIVE:
            raise ValueError(f"Session {session_id} is not in ACTIVE state: {session_status.state}")

        probe_id = generate_probe_id()
        session_status.current_probe = probe_id

        try:
            self._initialize_routing_capture(session_id)

            # Tokenize full input text
            token_ids = self.tokenizer.encode(input_text, add_special_tokens=False)
            total_tokens = len(token_ids)

            # Find target word position
            if target_token_position is None:
                target_token_position, target_token_id = self._find_word_token_position(token_ids, target_word)
            else:
                target_token_id = token_ids[target_token_position]

            # Find context word position if provided
            context_token_pos = None
            if context_word is not None:
                if context_token_position is not None:
                    context_token_pos = context_token_position
                else:
                    context_token_pos, _ = self._find_word_token_position(token_ids, context_word)

            # Clear previous capture data
            self.routing_capture.clear_data()

            # Create input tensor and run forward pass
            input_tensor = torch.tensor([token_ids], device=self.model.device)

            with torch.no_grad():
                forward_kwargs = {"input_ids": input_tensor}
                if past_key_values is not None:
                    forward_kwargs["past_key_values"] = past_key_values
                if use_cache:
                    forward_kwargs["use_cache"] = True
                outputs = self.model(**forward_kwargs)

            # Get updated KV cache if requested
            new_past_key_values = None
            if use_cache and hasattr(outputs, 'past_key_values'):
                new_past_key_values = outputs.past_key_values

            # Convert hook data to schema records
            probe_data = self._convert_probe_to_schemas(
                probe_id=probe_id,
                session_id=session_id,
                input_text=input_text,
                target_word=target_word,
                target_token_id=target_token_id,
                target_token_position=target_token_position,
                total_tokens=total_tokens,
                context_word=context_word,
                context_token_position=context_token_pos,
                experiment_id=experiment_id,
                sequence_id=sequence_id,
                sentence_index=sentence_index,
                label=label,
                transition_step=transition_step,
            )

            # Write to data lake
            writers = self.session_writers[session_id]
            writers.write_probe_data(probe_data)

            # Update session progress
            session_status.completed_pairs += 1
            session_status.current_probe = None

            ctx_info = f", context='{context_word}'" if context_word else ""
            print(f"Captured probe {probe_id}: '{target_word}' in '{input_text[:40]}...'{ctx_info} (session {session_id})")
            return probe_id, new_past_key_values

        except Exception as e:
            session_status.failed_pairs += 1
            session_status.current_probe = None
            session_status.error_message = str(e)

            print(f"Failed to capture '{target_word}' in '{input_text[:40]}...': {e}")
            raise

    def _convert_probe_to_schemas(
        self, probe_id: str, session_id: str,
        input_text: str, target_word: str,
        target_token_id: int, target_token_position: int,
        total_tokens: int,
        context_word: str = None, context_token_position: int = None,
        experiment_id: str = None, sequence_id: str = None,
        sentence_index: int = None, label: str = None,
        transition_step: int = None,
    ) -> ProbeCapture:
        """Convert raw routing capture data to schema records.

        Extracts activation data at the target position (always) and
        context position (if context_word provided). Stores with semantic
        token_position: 0=context, 1=target.
        """
        from datetime import datetime

        probe_record = create_probe_record(
            probe_id=probe_id,
            session_id=session_id,
            input_text=input_text,
            target_word=target_word,
            target_token_id=target_token_id,
            target_token_position=target_token_position,
            total_tokens=total_tokens,
            context_word=context_word,
            context_token_position=context_token_position,
            experiment_id=experiment_id,
            sequence_id=sequence_id,
            sentence_index=sentence_index,
            label=label,
            transition_step=transition_step,
            created_at=datetime.now().isoformat(),
        )

        routing_records = []
        embedding_records = []
        residual_stream_records = []

        # Build list of (actual_position, semantic_position) pairs to extract
        positions_to_extract = [(target_token_position, 1)]  # target always at semantic position 1
        if context_token_position is not None:
            positions_to_extract.append((context_token_position, 0))  # context at semantic position 0

        for layer in self.layers_to_capture:
            layer_key = f"layer_{layer}"

            if layer_key not in self.routing_capture.routing_data:
                print(f"No routing data for layer {layer}")
                continue

            routing_data = self.routing_capture.routing_data[layer_key]

            for actual_pos, semantic_pos in positions_to_extract:
                # Routing weights
                routing_weights = routing_data["routing_weights"][0, actual_pos, :]
                routing_records.append(create_routing_record(
                    probe_id=probe_id, layer=layer,
                    token_position=semantic_pos,
                    routing_weights=routing_weights.numpy()
                ))

            # Embeddings (MLP output)
            if layer_key in self.routing_capture.embedding_data:
                emb_data = self.routing_capture.embedding_data[layer_key]

                for actual_pos, semantic_pos in positions_to_extract:
                    emb_vec = emb_data["embedding"][0, actual_pos, :]
                    embedding_records.append(create_embedding_record(
                        probe_id=probe_id, layer=layer,
                        token_position=semantic_pos,
                        embedding=emb_vec.numpy()
                    ))

            # Residual stream states
            if layer_key in self.routing_capture.residual_stream_data:
                residual_data = self.routing_capture.residual_stream_data[layer_key]

                for actual_pos, semantic_pos in positions_to_extract:
                    residual_state = residual_data["residual_stream"][0, actual_pos, :]
                    residual_stream_records.append(create_residual_stream_state(
                        probe_id=probe_id, layer=layer,
                        token_position=semantic_pos,
                        residual_stream=residual_state.numpy()
                    ))

        return ProbeCapture(
            probe_id=probe_id,
            session_id=session_id,
            probe_record=probe_record,
            routing_records=routing_records,
            embedding_records=embedding_records,
            residual_stream_records=residual_stream_records
        )

    def finalize_session(self, session_id: str) -> CaptureManifest:
        """
        Finalize session and generate capture manifest.

        Args:
            session_id: Session to finalize

        Returns:
            Generated CaptureManifest
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not active")

        session_status = self.active_sessions[session_id]

        # Load session metadata
        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, 'r') as f:
            metadata = json.load(f)

        try:
            # Flush and close batch writers
            writers = self.session_writers[session_id]
            writers.close_all()

            # Create capture manifest
            topology = self.adapter.topology if self.adapter else None
            manifest = create_capture_manifest(
                capture_session_id=session_id,
                session_name=metadata["session_name"],
                target_word=metadata.get("target_word", ""),
                labels=metadata.get("labels", []),
                layers_captured=self.layers_to_capture,
                probe_count=session_status.completed_pairs,
                model_name=topology.model_name if topology else "gpt-oss-20b",
                num_experts=topology.num_experts if topology else 0,
                num_layers=topology.num_layers if topology else 0,
                hidden_size=topology.hidden_size if topology else 0,
            )

            # Write manifest to data lake
            manifest_path = Path(self.data_lake_path) / session_id / "capture_manifest.parquet"
            manifest_dict = manifest.to_parquet_dict()

            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.Table.from_pylist([manifest_dict])
            pq.write_table(table, manifest_path)

            # Update session state
            session_status.state = SessionState.COMPLETED
            metadata["state"] = SessionState.COMPLETED.value
            metadata["completed_pairs"] = session_status.completed_pairs
            metadata["failed_pairs"] = session_status.failed_pairs

            # Save updated metadata
            with open(session_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Cleanup
            del self.active_sessions[session_id]
            del self.session_writers[session_id]
            self._cleanup_routing_capture()

            print(f"Session {session_id} finalized: {session_status.completed_pairs} successful probes")
            return manifest

        except Exception as e:
            session_status.state = SessionState.FAILED
            session_status.error_message = str(e)
            print(f"Failed to finalize session {session_id}: {e}")
            raise

    def abort_session(self, session_id: str) -> None:
        """Abort active session and clean up resources."""
        if session_id in self.active_sessions:
            session_status = self.active_sessions[session_id]
            session_status.state = SessionState.FAILED
            session_status.error_message = "Aborted by user"

            # Clean up writers
            if session_id in self.session_writers:
                writers = self.session_writers[session_id]
                writers.close_all()
                del self.session_writers[session_id]

            del self.active_sessions[session_id]

        # Always cleanup routing capture on abort
        self._cleanup_routing_capture()

        print(f"Session {session_id} aborted")

    def _restore_session(self, session_id: str, metadata: dict) -> None:
        """Restore an active session from persisted metadata."""
        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=metadata["total_pairs"],
            completed_pairs=metadata.get("completed_pairs", 0),
            failed_pairs=metadata.get("failed_pairs", 0),
        )
        batch_writers = SessionBatchWriters(session_id, self.data_lake_path, self.batch_size)

        self.active_sessions[session_id] = session_status
        self.session_writers[session_id] = batch_writers
        print(f"Restored session {session_id} from disk ({session_status.completed_pairs}/{session_status.total_pairs} completed)")
