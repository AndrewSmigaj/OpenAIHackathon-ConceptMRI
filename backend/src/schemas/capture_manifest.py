#!/usr/bin/env python3
"""
Simple capture manifest schema for tracking capture sessions.
Provides UI with basic session information for experiment selection.
"""

from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class CaptureManifest:
    """Simple manifest tracking capture session for UI integration."""
    
    # Session identifiers
    capture_session_id: str      # Unique session identifier
    session_name: str           # User-friendly session name
    
    # Capture summary
    contexts: List[str]         # Context words captured
    targets: List[str]          # Target words captured  
    layers_captured: List[int]  # Layers that were captured (e.g., [1,2,3])
    probe_count: int            # Total number of probes in session
    
    # Metadata
    created_at: str             # ISO timestamp
    model_name: str             # Model used for capture
    
    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'CaptureManifest':
        """Reconstruct from Parquet dictionary."""
        return cls(**data)


# Parquet schema definition
CAPTURE_MANIFEST_PARQUET_SCHEMA = {
    "capture_session_id": "string",
    "session_name": "string", 
    "contexts": "list<string>",
    "targets": "list<string>",
    "layers_captured": "list<int32>",
    "probe_count": "int32",
    "created_at": "string",
    "model_name": "string"
}


def create_capture_manifest(
    capture_session_id: str,
    session_name: str,
    contexts: List[str], 
    targets: List[str],
    layers_captured: List[int],
    probe_count: int,
    model_name: str = "gpt-oss-20b"
) -> CaptureManifest:
    """Create simple capture manifest for session tracking."""
    return CaptureManifest(
        capture_session_id=capture_session_id,
        session_name=session_name,
        contexts=contexts,
        targets=targets,
        layers_captured=layers_captured,
        probe_count=probe_count,
        created_at=datetime.now().isoformat(),
        model_name=model_name
    )