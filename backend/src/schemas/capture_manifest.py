#!/usr/bin/env python3
"""
Simple capture manifest schema for tracking capture sessions.
Provides UI with basic session information for experiment selection.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import json


@dataclass
class CaptureManifest:
    """Simple manifest tracking capture session for UI integration."""

    # Session identifiers
    capture_session_id: str      # Unique session identifier
    session_name: str           # User-friendly session name

    # Capture summary
    target_word: str            # The word being tracked across probes
    labels: List[str]           # Distinct labels in this session (e.g., ["aquatic", "military"])
    layers_captured: List[int]  # Layers that were captured (e.g., [1,2,3])
    probe_count: int            # Total number of probes in session

    # Metadata
    created_at: str             # ISO timestamp
    model_name: str             # Model used for capture

    # Model topology (from adapter)
    num_experts: int = 0            # Number of experts per MoE layer
    num_layers: int = 0             # Total number of model layers
    hidden_size: int = 0            # Hidden dimension size

    # Agent session fields (null for batch captures)
    target_words: Optional[List[str]] = None  # Multi-word tracking for agent sessions
    experiment_type: Optional[str] = None     # "sentence" or "agent"

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'CaptureManifest':
        """Reconstruct from Parquet dictionary with JSON deserialization."""
        return cls(
            capture_session_id=data['capture_session_id'],
            session_name=data['session_name'],
            target_word=data.get('target_word', ''),
            labels=data.get('labels', []),
            layers_captured=data['layers_captured'],
            probe_count=data['probe_count'],
            created_at=data['created_at'],
            model_name=data['model_name'],
            num_experts=data.get('num_experts', 0),
            num_layers=data.get('num_layers', 0),
            hidden_size=data.get('hidden_size', 0),
            target_words=data.get('target_words'),
            experiment_type=data.get('experiment_type'),
        )

    def to_parquet_dict(self) -> dict:
        """Convert to dictionary with JSON serialization for Parquet storage."""
        return {
            'capture_session_id': self.capture_session_id,
            'session_name': self.session_name,
            'target_word': self.target_word,
            'labels': self.labels,
            'layers_captured': self.layers_captured,
            'probe_count': self.probe_count,
            'created_at': self.created_at,
            'model_name': self.model_name,
            'num_experts': self.num_experts,
            'num_layers': self.num_layers,
            'hidden_size': self.hidden_size,
            'target_words': self.target_words,
            'experiment_type': self.experiment_type,
        }


# Parquet schema definition
CAPTURE_MANIFEST_PARQUET_SCHEMA = {
    "capture_session_id": "string",
    "session_name": "string",
    "target_word": "string",
    "labels": "list<string>",
    "layers_captured": "list<int32>",
    "probe_count": "int32",
    "created_at": "string",
    "model_name": "string",
    "num_experts": "int32",
    "num_layers": "int32",
    "hidden_size": "int32",
    "target_words": "list<string>",
    "experiment_type": "string",
}


def create_capture_manifest(
    capture_session_id: str,
    session_name: str,
    target_word: str,
    labels: List[str],
    layers_captured: List[int],
    probe_count: int,
    model_name: str = "gpt-oss-20b",
    num_experts: int = 0,
    num_layers: int = 0,
    hidden_size: int = 0,
    target_words: Optional[List[str]] = None,
    experiment_type: Optional[str] = None,
) -> CaptureManifest:
    """Create capture manifest for session tracking."""
    return CaptureManifest(
        capture_session_id=capture_session_id,
        session_name=session_name,
        target_word=target_word,
        labels=labels,
        layers_captured=layers_captured,
        probe_count=probe_count,
        created_at=datetime.now().isoformat(),
        model_name=model_name,
        num_experts=num_experts,
        num_layers=num_layers,
        hidden_size=hidden_size,
        target_words=target_words,
        experiment_type=experiment_type,
    )
