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
    contexts: List[str]         # Context words captured
    targets: List[str]          # Target words captured  
    layers_captured: List[int]  # Layers that were captured (e.g., [1,2,3])
    probe_count: int            # Total number of probes in session
    
    # Metadata
    created_at: str             # ISO timestamp
    model_name: str             # Model used for capture
    
    # Category assignments for multi-category analysis
    context_category_assignments: Optional[Dict[str, str]] = None  # {"the": "determiners", "a": "determiners"}
    target_category_assignments: Optional[Dict[str, str]] = None   # {"cat": "animals", "dog": "pets"}
    
    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'CaptureManifest':
        """Reconstruct from Parquet dictionary with JSON deserialization."""
        # Deserialize category assignment dicts from JSON strings
        context_assignments = None
        target_assignments = None
        
        if data.get('context_category_assignments'):
            context_assignments = json.loads(data['context_category_assignments'])
        if data.get('target_category_assignments'):
            target_assignments = json.loads(data['target_category_assignments'])
        
        return cls(
            capture_session_id=data['capture_session_id'],
            session_name=data['session_name'],
            contexts=data['contexts'],
            targets=data['targets'],
            layers_captured=data['layers_captured'],
            probe_count=data['probe_count'],
            created_at=data['created_at'],
            model_name=data['model_name'],
            context_category_assignments=context_assignments,
            target_category_assignments=target_assignments
        )

    def to_parquet_dict(self) -> dict:
        """Convert to dictionary with JSON serialization for Parquet storage."""
        context_assignments_json = None
        target_assignments_json = None
        
        if self.context_category_assignments:
            context_assignments_json = json.dumps(self.context_category_assignments)
        if self.target_category_assignments:
            target_assignments_json = json.dumps(self.target_category_assignments)
        
        return {
            'capture_session_id': self.capture_session_id,
            'session_name': self.session_name,
            'contexts': self.contexts,
            'targets': self.targets,
            'layers_captured': self.layers_captured,
            'probe_count': self.probe_count,
            'created_at': self.created_at,
            'model_name': self.model_name,
            'context_category_assignments': context_assignments_json,
            'target_category_assignments': target_assignments_json
        }


# Parquet schema definition
CAPTURE_MANIFEST_PARQUET_SCHEMA = {
    "capture_session_id": "string",
    "session_name": "string", 
    "contexts": "list<string>",
    "targets": "list<string>",
    "layers_captured": "list<int32>",
    "probe_count": "int32",
    "created_at": "string",
    "model_name": "string",
    "context_category_assignments": "string",  # JSON serialized dict
    "target_category_assignments": "string"
}


def create_capture_manifest(
    capture_session_id: str,
    session_name: str,
    contexts: List[str], 
    targets: List[str],
    layers_captured: List[int],
    probe_count: int,
    model_name: str = "gpt-oss-20b",
    context_category_assignments: Optional[Dict[str, str]] = None,
    target_category_assignments: Optional[Dict[str, str]] = None
) -> CaptureManifest:
    """Create capture manifest for session tracking with category assignments."""
    return CaptureManifest(
        capture_session_id=capture_session_id,
        session_name=session_name,
        contexts=contexts,
        targets=targets,
        layers_captured=layers_captured,
        probe_count=probe_count,
        created_at=datetime.now().isoformat(),
        model_name=model_name,
        context_category_assignments=context_category_assignments,
        target_category_assignments=target_category_assignments
    )