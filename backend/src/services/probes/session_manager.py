#!/usr/bin/env python3
"""
Session lifecycle management for probe captures.

Owns session creation, tracking, restoration, finalization, and abort.
No knowledge of model inference, hooks, or writers.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from schemas.capture_manifest import CaptureManifest, create_capture_manifest
from services.probes.probe_ids import generate_capture_id

logger = logging.getLogger(__name__)


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
    current_turn_id: int = 0  # Agent sessions: auto-incremented per generate call

    @property
    def progress_percent(self) -> float:
        if self.total_pairs == 0:
            return 0.0
        return (self.completed_pairs / self.total_pairs) * 100.0


class SessionManager:
    """Manages session lifecycle — create, track, restore, finalize, abort."""

    def __init__(
        self,
        data_lake_path: str,
        batch_size: int,
        layers_to_capture: List[int],
        model_name: str = "gpt-oss-20b",
        num_experts: int = 0,
        num_layers: int = 0,
        hidden_size: int = 0,
    ):
        self.data_lake_path = data_lake_path
        self.batch_size = batch_size
        self.layers_to_capture = layers_to_capture
        self.model_name = model_name
        self.num_experts = num_experts
        self.num_layers = num_layers
        self.hidden_size = hidden_size

        self.active_sessions: Dict[str, SessionStatus] = {}
        self.sessions_dir = Path(data_lake_path) / "_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        session_name: str,
        total_probes: int,
        target_word: str,
        labels: List[str],
        experiment_id: str = None,
        sentence_set_name: str = None,
    ) -> str:
        """Create a new capture session. Returns session_id."""
        session_id = generate_capture_id("session")

        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=total_probes,
            completed_pairs=0,
            failed_pairs=0,
        )
        self.active_sessions[session_id] = session_status

        session_metadata = {
            "session_id": session_id,
            "session_name": session_name,
            "sentence_set_name": sentence_set_name,
            "target_word": target_word,
            "labels": labels,
            "layers_captured": self.layers_to_capture,
            "total_pairs": total_probes,
            "model_name": self.model_name,
            "created_at": datetime.now().isoformat(),
            "state": session_status.state.value,
            "experiment_type": "sentence",
            "experiment_id": experiment_id,
        }

        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session_metadata, f, indent=2)

        logger.info(f"Created sentence session {session_id} ({session_name}): {total_probes} probes")
        return session_id

    def create_agent_session(
        self,
        session_name: str,
        scenario_id: str,
        target_words: List[str],
        bootstrap_session_id: str,
        agent_name: str,
        capture_type_config: List[str] = None,
    ) -> str:
        """Create a new agent capture session. Returns session_id."""
        if capture_type_config is None:
            capture_type_config = ["reasoning"]

        session_id = generate_capture_id("session")

        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=0,  # open-ended
            completed_pairs=0,
            failed_pairs=0,
            current_turn_id=0,
        )
        self.active_sessions[session_id] = session_status

        session_metadata = {
            "session_id": session_id,
            "session_name": session_name,
            "target_word": target_words[0] if target_words else "",
            "target_words": target_words,
            "labels": [],
            "layers_captured": self.layers_to_capture,
            "total_pairs": 0,
            "model_name": self.model_name,
            "created_at": datetime.now().isoformat(),
            "state": session_status.state.value,
            "experiment_type": "agent",
            "scenario_id": scenario_id,
            "bootstrap_session_id": bootstrap_session_id,
            "agent_name": agent_name,
            "capture_type_config": capture_type_config,
        }

        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session_metadata, f, indent=2)

        logger.info(f"Created agent session {session_id} ({session_name}): scenario={scenario_id}, targets={target_words}")
        return session_id

    def get_session_status(self, session_id: str) -> SessionStatus:
        """Get current session status, loading from disk if needed."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, "r") as f:
                metadata = json.load(f)
            return SessionStatus(
                session_id=session_id,
                state=SessionState(metadata["state"]),
                total_pairs=metadata["total_pairs"],
                completed_pairs=metadata.get("completed_pairs", 0),
                failed_pairs=metadata.get("failed_pairs", 0),
            )

        raise ValueError(f"Session {session_id} not found")

    def validate_active_session(self, session_id: str) -> SessionStatus:
        """Ensure session exists and is active, restoring from disk if needed."""
        if session_id not in self.active_sessions:
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, "r") as f:
                    metadata = json.load(f)
                if metadata["state"] == "active":
                    self._restore_session(session_id, metadata)
                else:
                    raise ValueError(f"Session {session_id} is not active (state: {metadata['state']})")
            else:
                raise ValueError(f"Session {session_id} not found")

        status = self.active_sessions[session_id]
        if status.state != SessionState.ACTIVE:
            raise ValueError(f"Session {session_id} is not in ACTIVE state: {status.state}")
        return status

    def record_probe_success(self, session_id: str) -> None:
        status = self.active_sessions[session_id]
        status.completed_pairs += 1
        status.current_probe = None

    def record_probe_failure(self, session_id: str, error_msg: str) -> None:
        status = self.active_sessions[session_id]
        status.failed_pairs += 1
        status.current_probe = None
        status.error_message = error_msg

    def finalize_session(self, session_id: str) -> CaptureManifest:
        """Finalize session state, create and write manifest. Returns manifest."""
        session_status = self.active_sessions[session_id]

        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "r") as f:
            metadata = json.load(f)

        manifest = create_capture_manifest(
            capture_session_id=session_id,
            session_name=metadata["session_name"],
            target_word=metadata.get("target_word", ""),
            labels=metadata.get("labels", []),
            layers_captured=self.layers_to_capture,
            probe_count=session_status.completed_pairs,
            model_name=self.model_name,
            num_experts=self.num_experts,
            num_layers=self.num_layers,
            hidden_size=self.hidden_size,
        )

        manifest_path = Path(self.data_lake_path) / session_id / "capture_manifest.parquet"
        manifest_dict = manifest.to_parquet_dict()
        table = pa.Table.from_pylist([manifest_dict])
        pq.write_table(table, manifest_path)

        session_status.state = SessionState.COMPLETED
        metadata["state"] = SessionState.COMPLETED.value
        metadata["completed_pairs"] = session_status.completed_pairs
        metadata["failed_pairs"] = session_status.failed_pairs

        with open(session_file, "w") as f:
            json.dump(metadata, f, indent=2)

        del self.active_sessions[session_id]

        logger.info(f"Session {session_id} finalized: {session_status.completed_pairs} successful probes")
        return manifest

    def abort_session(self, session_id: str) -> None:
        """Mark session as failed and remove from active tracking."""
        if session_id in self.active_sessions:
            status = self.active_sessions[session_id]
            status.state = SessionState.FAILED
            status.error_message = "Aborted by user"
            del self.active_sessions[session_id]
        logger.info(f"Session {session_id} aborted")

    def _restore_session(self, session_id: str, metadata: dict) -> None:
        """Restore an active session from persisted metadata."""
        # For agent sessions, recover turn_id from tick_log line count
        turn_id = 0
        if metadata.get("experiment_type") == "agent":
            tick_log = Path(self.data_lake_path) / session_id / "tick_log.jsonl"
            if tick_log.exists():
                turn_id = sum(1 for _ in tick_log.open())
                logger.info(f"Recovered turn_id={turn_id} from tick_log for {session_id}")

        session_status = SessionStatus(
            session_id=session_id,
            state=SessionState.ACTIVE,
            total_pairs=metadata["total_pairs"],
            completed_pairs=metadata.get("completed_pairs", 0),
            failed_pairs=metadata.get("failed_pairs", 0),
            current_turn_id=turn_id,
        )
        self.active_sessions[session_id] = session_status
        logger.info(
            f"Restored session {session_id} from disk "
            f"({session_status.completed_pairs}/{session_status.total_pairs} completed)"
        )
