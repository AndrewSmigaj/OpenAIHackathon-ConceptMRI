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
from schemas.expert_internal_activations import ExpertInternalActivation, create_expert_internal_activation
from schemas.expert_output_states import ExpertOutputState, create_expert_output_state
from schemas.residual_stream import ResidualStreamState, create_residual_stream_state
from schemas.capture_manifest import CaptureManifest, create_capture_manifest

# Core services
from services.probes.routing_capture import EnhancedRoutingCapture
from services.probes.probe_ids import generate_probe_id, generate_capture_id
from core.parquet_writer import BatchWriter
from utils.wordnet_mining import WordNetMiner


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
    expert_internal_records: List[ExpertInternalActivation]
    expert_output_records: List[ExpertOutputState]
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
        self.expert_internal_writer = BatchWriter(self.session_dir / "expert_internal_activations.parquet", batch_size)
        self.expert_output_writer = BatchWriter(self.session_dir / "expert_output_states.parquet", batch_size)
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
            
            for expert_internal_record in probe_data.expert_internal_records:
                self.expert_internal_writer.add_record(expert_internal_record)
            
            for expert_output_record in probe_data.expert_output_records:
                self.expert_output_writer.add_record(expert_output_record)

            for residual_record in probe_data.residual_stream_records:
                self.residual_stream_writer.add_record(residual_record)

        except Exception as e:
            print(f"❌ Failed to write probe {probe_data.probe_id}: {e}")
            raise
    
    def flush_all(self) -> None:
        """Flush all batch writers."""
        if not self.writers_active:
            return
            
        self.tokens_writer.flush()
        self.routing_writer.flush()
        self.expert_internal_writer.flush()
        self.expert_output_writer.flush()
        self.residual_stream_writer.flush()
    
    def close_all(self) -> None:
        """Close all batch writers and mark inactive."""
        if not self.writers_active:
            return
            
        self.flush_all()
        self.writers_active = False
        print(f"✅ Closed all batch writers for session {self.session_id}")


class IntegratedCaptureService:
    """
    Integrated MoE capture service with session management.
    Coordinates EnhancedRoutingCapture with schema conversion and batch writing.
    """
    
    def __init__(self, model, tokenizer, layers_to_capture: Optional[List[int]] = None,
                 data_lake_path: str = "data/lake", batch_size: int = 1000,
                 wordnet_miner: Optional[WordNetMiner] = None,
                 adapter=None):
        print("DEBUG: IntegratedCaptureService.__init__ starting")
        self.model = model
        print("DEBUG: Model assigned")
        self.tokenizer = tokenizer
        print("DEBUG: Tokenizer assigned")
        self.adapter = adapter
        self.data_lake_path = data_lake_path
        self.batch_size = batch_size
        print("DEBUG: Basic attributes set")

        # Use adapter for defaults, fall back to legacy hardcoded values
        if layers_to_capture is None:
            layers_to_capture = adapter.layers_range() if adapter else list(range(24))
        self.layers_to_capture = layers_to_capture
        print("DEBUG: Layers to capture set")
        
        # Session management
        print("DEBUG: Setting up session management")
        self.active_sessions: Dict[str, SessionStatus] = {}
        self.session_writers: Dict[str, SessionBatchWriters] = {}
        self.routing_capture: Optional[EnhancedRoutingCapture] = None
        print("DEBUG: Session management attributes set")
        
        # Session state persistence 
        print("DEBUG: Creating sessions directory")
        self.sessions_dir = Path(data_lake_path) / "_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        print("DEBUG: Sessions directory created")
        
        # Use provided WordNet miner or create new one (for backwards compatibility)
        print("DEBUG: Setting up WordNet miner")
        if wordnet_miner is not None:
            print("DEBUG: Using provided WordNet miner")
            self.wordnet_miner = wordnet_miner
        else:
            print("DEBUG: Creating new WordNet miner")
            # Fallback for tests or direct instantiation
            self.wordnet_miner = WordNetMiner(tokenizer)
        print("DEBUG: WordNet miner ready")
        
        print(f"🚀 IntegratedCaptureService initialized for layers {self.layers_to_capture}")
        print("DEBUG: IntegratedCaptureService.__init__ completed successfully")
    
    def create_session(self, session_name: str, contexts: List[str], targets: List[str], 
                      context_category_assignments: Optional[Dict[str, List[str]]] = None,
                      target_category_assignments: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Create new capture session with context-target word lists and optional category assignments.
        
        Args:
            session_name: Human-readable session name
            contexts: List of context words
            targets: List of target words
            context_category_assignments: Optional mapping of context words to category lists
            target_category_assignments: Optional mapping of target words to category lists
        
        Returns:
            Unique session ID
        """
        session_id = generate_capture_id("session")
        
        # Validate inputs
        if not contexts or not targets:
            raise ValueError("Both contexts and targets must be non-empty")
        
        # Calculate total pairs (Cartesian product)
        total_pairs = len(contexts) * len(targets)
        
        # Create session status
        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=total_pairs,
            completed_pairs=0,
            failed_pairs=0
        )
        
        # Initialize batch writers
        batch_writers = SessionBatchWriters(session_id, self.data_lake_path, self.batch_size)
        
        # Store session state
        self.active_sessions[session_id] = session_status
        self.session_writers[session_id] = batch_writers
        
        # Persist session metadata
        session_metadata = {
            "session_id": session_id,
            "session_name": session_name,
            "contexts": contexts,
            "targets": targets,
            "context_category_assignments": context_category_assignments,
            "target_category_assignments": target_category_assignments,
            "layers_captured": self.layers_to_capture,
            "total_pairs": total_pairs,
            "model_name": self.adapter.topology.model_name if self.adapter else "gpt-oss-20b",
            "created_at": datetime.now().isoformat(),
            "state": session_status.state.value
        }
        
        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_metadata, f, indent=2)
        
        print(f"✅ Created session {session_id} ({session_name}): {total_pairs} context-target pairs")
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
            print(f"🔗 Registered hooks for session {session_id}")
    
    def _cleanup_routing_capture(self) -> None:
        """Clean up routing capture hooks."""
        if self.routing_capture is not None:
            self.routing_capture.remove_hooks()
            self.routing_capture = None
            
            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("🧹 Cleaned up routing capture and GPU memory")
    
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
        sentence_index: int = None, regime_label: str = None,
        transition_step: int = None,
    ) -> Tuple[str, any]:
        """
        Capture a probe for any-length text input, tracking a target word
        and optionally a context word.

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
                regime_label=regime_label,
                transition_step=transition_step,
            )

            # Write to data lake
            writers = self.session_writers[session_id]
            writers.write_probe_data(probe_data)

            # Update session progress
            session_status.completed_pairs += 1
            session_status.current_probe = None

            ctx_info = f", context='{context_word}'" if context_word else ""
            print(f"✅ Captured probe {probe_id}: '{target_word}' in '{input_text[:40]}...'{ctx_info} (session {session_id})")
            return probe_id, new_past_key_values

        except Exception as e:
            session_status.failed_pairs += 1
            session_status.current_probe = None
            session_status.error_message = str(e)

            print(f"❌ Failed to capture '{target_word}' in '{input_text[:40]}...': {e}")
            raise

    def _convert_probe_to_schemas(
        self, probe_id: str, session_id: str,
        input_text: str, target_word: str,
        target_token_id: int, target_token_position: int,
        total_tokens: int,
        context_word: str = None, context_token_position: int = None,
        experiment_id: str = None, sequence_id: str = None,
        sentence_index: int = None, regime_label: str = None,
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
            regime_label=regime_label,
            transition_step=transition_step,
            created_at=datetime.now().isoformat(),
        )

        routing_records = []
        expert_internal_records = []
        expert_output_records = []
        residual_stream_records = []

        # Build list of (actual_position, semantic_position) pairs to extract
        positions_to_extract = [(target_token_position, 1)]  # target always at semantic position 1
        if context_token_position is not None:
            positions_to_extract.append((context_token_position, 0))  # context at semantic position 0

        for layer in self.layers_to_capture:
            layer_key = f"layer_{layer}"

            if layer_key not in self.routing_capture.routing_data:
                print(f"⚠️ No routing data for layer {layer}")
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

            # Expert internal activations (collective)
            collective_key = f"layer_{layer}_experts_collective"
            if collective_key in self.routing_capture.expert_internal_data:
                expert_data = self.routing_capture.expert_internal_data[collective_key]
                collective_output = expert_data["collective_output"]

                for actual_pos, semantic_pos in positions_to_extract:
                    token_output = collective_output[actual_pos, :]
                    expert_internal_records.append(create_expert_internal_activation(
                        probe_id=probe_id, layer=layer,
                        expert_id=-1,
                        token_position=semantic_pos,
                        ff_intermediate_state=token_output.numpy()
                    ))

            # Expert output states
            if layer_key in self.routing_capture.activation_data:
                activation_data = self.routing_capture.activation_data[layer_key]

                for actual_pos, semantic_pos in positions_to_extract:
                    expert_output_state = activation_data["expert_output_state"][0, actual_pos, :]
                    expert_output_records.append(create_expert_output_state(
                        probe_id=probe_id, layer=layer,
                        token_position=semantic_pos,
                        expert_output_state=expert_output_state.numpy()
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
            expert_internal_records=expert_internal_records,
            expert_output_records=expert_output_records,
            residual_stream_records=residual_stream_records
        )
    
    def capture_session_batch(self, session_id: str) -> List[str]:
        """
        Capture all context-target pairs for an active session.
        
        Args:
            session_id: Session to process
            
        Returns:
            List of successfully generated probe_ids
        """
        # Load session metadata
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            raise ValueError(f"Session metadata not found: {session_id}")
        
        with open(session_file, 'r') as f:
            metadata = json.load(f)
        
        contexts = metadata["contexts"]
        targets = metadata["targets"]
        successful_probes = []
        
        print(f"🚀 Starting batch capture for session {session_id}: {len(contexts)} × {len(targets)} = {len(contexts) * len(targets)} pairs")
        
        # Process all context-target combinations
        for context in contexts:
            for target in targets:
                try:
                    probe_id, _ = self.capture_probe(
                        session_id,
                        input_text=f"{context} {target}",
                        target_word=target,
                        context_word=context,
                    )
                    successful_probes.append(probe_id)
                except Exception as e:
                    print(f"⚠️ Skipping failed pair '{context}' → '{target}': {e}")
                    continue
        
        print(f"✅ Batch capture complete: {len(successful_probes)}/{len(contexts) * len(targets)} successful")
        
        # Finalize session to write Parquet files and update state
        self.finalize_session(session_id)
        print(f"✅ Session {session_id} finalized - Parquet files written")
        
        return successful_probes
    
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
            manifest = create_capture_manifest(
                capture_session_id=session_id,
                session_name=metadata["session_name"],
                contexts=metadata["contexts"],
                targets=metadata["targets"],
                layers_captured=self.layers_to_capture,
                probe_count=session_status.completed_pairs,
                model_name=self.adapter.topology.model_name if self.adapter else "gpt-oss-20b",
                context_category_assignments=metadata.get("context_category_assignments"),
                target_category_assignments=metadata.get("target_category_assignments")
            )
            
            # Write manifest to data lake (special handling for category JSON serialization)
            manifest_path = Path(self.data_lake_path) / session_id / "capture_manifest.parquet"
            manifest_dict = manifest.to_parquet_dict()
            
            # Write directly as a single-record table
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.Table.from_pylist([manifest_dict])
            pq.write_table(table, manifest_path)
            
            # Generate dimensionality-reduced features (PCA + UMAP for both sources)
            try:
                from services.features.reduction_service import ReductionService
                print(f"🔬 Generating reduced features for session {session_id}...")
                reducer = ReductionService(n_components=128)
                session_id_only = session_id.replace("session_", "") if session_id.startswith("session_") else session_id
                for source in ["expert_output", "residual_stream"]:
                    for method in ["pca", "umap"]:
                        try:
                            output_path = reducer.generate_features(session_id_only, self.data_lake_path, source, method)
                            print(f"✅ {source}/{method} features: {output_path}")
                        except Exception as e:
                            print(f"⚠️ {source}/{method} reduction failed (non-fatal): {e}")
            except Exception as reduction_error:
                import traceback
                print(f"⚠️ Feature reduction failed (non-fatal): {type(reduction_error).__name__}: {reduction_error}")
                print(f"🔍 Reduction error traceback: {traceback.format_exc()}")
            
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
            
            print(f"🎉 Session {session_id} finalized: {session_status.completed_pairs} successful probes")
            return manifest
            
        except Exception as e:
            session_status.state = SessionState.FAILED
            session_status.error_message = str(e)
            print(f"❌ Failed to finalize session {session_id}: {e}")
            raise
    
    def abort_session(self, session_id: str) -> None:
        """
        Abort active session and clean up resources.
        
        Args:
            session_id: Session to abort
        """
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
        
        print(f"🛑 Session {session_id} aborted")
    
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
        print(f"♻️ Restored session {session_id} from disk ({session_status.completed_pairs}/{session_status.total_pairs} completed)")

    def _mine_from_source(self, word_source: str, source_params: dict) -> Tuple[List[str], str]:
        """
        Mine words from different sources: custom, pos_pure, or synset_hyponyms.
        
        Args:
            word_source: "custom", "pos_pure", or "synset_hyponyms"
            source_params: Parameters specific to the source type
            
        Returns:
            Tuple of (word_list, category_label)
        """
        if word_source == "custom":
            # Custom word list provided by user
            words = source_params.get("words", [])
            label = source_params.get("label", "custom")
            return words, label
            
        elif word_source == "pos_pure":
            # POS-pure words (words that are only nouns, only verbs, etc.)
            pos = source_params.get("pos", "n")
            max_words = source_params.get("max_words", 30)
            words = self.wordnet_miner.mine_pos_pure_words(pos, max_words)
            label = f"pos_pure_{pos}"
            return words, label
            
        elif word_source == "synset_hyponyms":
            # WordNet hyponym mining (unambiguous or all words)
            synset_id = source_params.get("synset_id")
            max_depth = source_params.get("max_depth", 2)
            unambiguous_only = source_params.get("unambiguous_only", True)
            
            if not synset_id:
                raise ValueError("synset_id required for synset_hyponyms source")
            
            if unambiguous_only:
                words = self.wordnet_miner.mine_unambiguous_words(synset_id, max_depth)
            else:
                words = self.wordnet_miner.mine_all_words(synset_id, max_depth)
            
            label = synset_id
            return words, label
            
        else:
            raise ValueError(f"Unknown word source: {word_source}")
    
    def create_session_from_sources(self, session_name: str, 
                                   context_sources: List[Dict[str, any]], 
                                   target_sources: List[Dict[str, any]]) -> str:
        """
        Create session by mining words from multiple sources with category preservation.
        
        Args:
            session_name: Human-readable session name
            context_sources: List of word source configurations for contexts
            target_sources: List of word source configurations for targets
            
        Returns:
            Unique session ID
        """
        # Mine and aggregate contexts
        contexts, context_categories = self._aggregate_word_sources(context_sources)
        
        # Mine and aggregate targets  
        targets, target_categories = self._aggregate_word_sources(target_sources)
        
        # Create session with aggregated results
        return self.create_session(
            session_name=session_name,
            contexts=contexts,
            targets=targets,
            context_category_assignments=context_categories,
            target_category_assignments=target_categories
        )
    
    def _aggregate_word_sources(self, word_sources: List[Dict[str, any]]) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Mine words from multiple sources and preserve all category memberships.
        
        Args:
            word_sources: List of word source configurations
            
        Returns:
            Tuple of (unique_words, category_assignments)
        """
        all_words = []
        category_assignments = {}
        
        for source in word_sources:
            source_type = source.get("source_type")
            source_params = source.get("source_params", {})
            
            words, category_label = self._mine_from_source(source_type, source_params)
            all_words.extend(words)
            
            # Preserve all category memberships for each word
            for word in words:
                if word not in category_assignments:
                    category_assignments[word] = []
                if category_label not in category_assignments[word]:
                    category_assignments[word].append(category_label)
        
        unique_words = list(set(all_words))
        return unique_words, category_assignments
    
