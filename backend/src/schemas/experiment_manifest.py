#!/usr/bin/env python3
"""
Experiment manifest schema for tracking attractor experiment configurations.
Links experiment_id to its design parameters, sentence sets, and labels.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class ExperimentManifest:
    """Describes an attractor experiment's configuration and design."""

    # Core identifiers
    experiment_id: str              # Unique experiment identifier
    experiment_name: str            # Human-readable name

    # Target word being studied
    target_word: str                # The polysemous/ambiguous word under study

    # Regime definitions
    label_a: str                    # Label for group A (e.g., "military")
    label_b: str                    # Label for group B (e.g., "aquatic")

    # Sequence configurations (list of dicts describing each sequence)
    # Each dict: {"sequence_id": str, "group_order": [str, ...], "sentence_indices": [int, ...]}
    sequence_configs: List[Dict]

    # Summary counts
    total_sequences: int
    total_probes: int

    # Metadata
    model_name: str
    sentence_set_source: str        # Where sentences came from (e.g., "generated", "curated")
    created_at: str

    # Optional: links to capture sessions that hold the actual probe data
    individual_session_id: Optional[str] = None   # Session with individual sentence probes
    temporal_session_id: Optional[str] = None      # Session with expanding text probes

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ExperimentManifest':
        """Reconstruct from Parquet dictionary."""
        sequence_configs = json.loads(data['sequence_configs']) if isinstance(data['sequence_configs'], str) else data['sequence_configs']

        return cls(
            experiment_id=data['experiment_id'],
            experiment_name=data['experiment_name'],
            target_word=data['target_word'],
            label_a=data['label_a'],
            label_b=data['label_b'],
            sequence_configs=sequence_configs,
            total_sequences=data['total_sequences'],
            total_probes=data['total_probes'],
            model_name=data['model_name'],
            sentence_set_source=data['sentence_set_source'],
            created_at=data['created_at'],
            individual_session_id=data.get('individual_session_id'),
            temporal_session_id=data.get('temporal_session_id'),
        )

    def to_parquet_dict(self) -> dict:
        """Convert to dictionary for Parquet storage."""
        return {
            'experiment_id': self.experiment_id,
            'experiment_name': self.experiment_name,
            'target_word': self.target_word,
            'label_a': self.label_a,
            'label_b': self.label_b,
            'sequence_configs': json.dumps(self.sequence_configs),
            'total_sequences': self.total_sequences,
            'total_probes': self.total_probes,
            'model_name': self.model_name,
            'sentence_set_source': self.sentence_set_source,
            'created_at': self.created_at,
            'individual_session_id': self.individual_session_id,
            'temporal_session_id': self.temporal_session_id,
        }


# Parquet schema definition
EXPERIMENT_MANIFEST_PARQUET_SCHEMA = {
    "experiment_id": "string",
    "experiment_name": "string",
    "target_word": "string",
    "label_a": "string",
    "label_b": "string",
    "sequence_configs": "string",       # JSON serialized list of dicts
    "total_sequences": "int32",
    "total_probes": "int32",
    "model_name": "string",
    "sentence_set_source": "string",
    "created_at": "string",
    "individual_session_id": "string",
    "temporal_session_id": "string",
}


def create_experiment_manifest(
    experiment_id: str,
    experiment_name: str,
    target_word: str,
    label_a: str,
    label_b: str,
    sequence_configs: List[Dict],
    total_sequences: int,
    total_probes: int,
    model_name: str,
    sentence_set_source: str = "generated",
    individual_session_id: str = None,
    temporal_session_id: str = None,
) -> ExperimentManifest:
    """Create experiment manifest describing an attractor experiment."""
    return ExperimentManifest(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        target_word=target_word,
        label_a=label_a,
        label_b=label_b,
        sequence_configs=sequence_configs,
        total_sequences=total_sequences,
        total_probes=total_probes,
        model_name=model_name,
        sentence_set_source=sentence_set_source,
        created_at=datetime.now().isoformat(),
        individual_session_id=individual_session_id,
        temporal_session_id=temporal_session_id,
    )
