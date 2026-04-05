#!/usr/bin/env python3
"""
Probe record schema - links probe_id to input text and tracked words.
Used by experiments to query probes and their activation data.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import json


@dataclass
class ProbeRecord:
    """Links probe_id to input text, target word, and optional context word."""

    # Core fields
    probe_id: str                    # Links to all activation data for this probe
    session_id: str                  # Capture session identifier
    input_text: str                  # Full text fed to model
    target_word: str                 # Word being tracked within input_text
    target_token_id: int             # Tokenized target word
    target_token_position: int       # Position of target in tokenized input
    total_tokens: int                # Total tokens in input

    # Optional context word for disambiguation analysis
    context_word: Optional[str] = None
    context_token_position: Optional[int] = None

    # Temporal metadata (attractor experiments)
    experiment_id: Optional[str] = None
    sequence_id: Optional[str] = None
    sentence_index: Optional[int] = None
    label: Optional[str] = None
    label2: Optional[str] = None
    categories_json: Optional[str] = None
    transition_step: Optional[int] = None
    created_at: Optional[str] = None

    # Generated output and categorization
    generated_text: Optional[str] = None
    output_category: Optional[str] = None
    output_category_json: Optional[str] = None

    # Agent session fields (null for batch captures)
    turn_id: Optional[int] = None
    scenario_id: Optional[str] = None
    capture_type: Optional[str] = None  # "batch", "reasoning", "knowledge_query"

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ProbeRecord':
        """Reconstruct from Parquet dictionary."""
        return cls(**data)


# Parquet schema definition
PROBE_RECORD_PARQUET_SCHEMA = {
    "probe_id": "string",
    "session_id": "string",
    "input_text": "string",
    "target_word": "string",
    "target_token_id": "int32",
    "target_token_position": "int32",
    "total_tokens": "int32",
    "context_word": "string",
    "context_token_position": "int32",
    "experiment_id": "string",
    "sequence_id": "string",
    "sentence_index": "int32",
    "label": "string",
    "label2": "string",
    "categories_json": "string",
    "transition_step": "int32",
    "created_at": "string",
    "generated_text": "string",
    "output_category": "string",
    "output_category_json": "string",
    "turn_id": "int32",
    "scenario_id": "string",
    "capture_type": "string",
}


def create_probe_record(
    probe_id: str,
    session_id: str,
    input_text: str,
    target_word: str,
    target_token_id: int,
    target_token_position: int,
    total_tokens: int,
    context_word: str = None,
    context_token_position: int = None,
    experiment_id: str = None,
    sequence_id: str = None,
    sentence_index: int = None,
    label: str = None,
    label2: str = None,
    categories: Optional[Dict[str, str]] = None,
    transition_step: int = None,
    created_at: str = None,
    turn_id: int = None,
    scenario_id: str = None,
    capture_type: str = None,
) -> ProbeRecord:
    """Create probe record linking probe_id to input text and tracked words."""
    categories_json = json.dumps(categories) if categories else None
    return ProbeRecord(
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
        label2=label2,
        categories_json=categories_json,
        transition_step=transition_step,
        created_at=created_at,
        turn_id=turn_id,
        scenario_id=scenario_id,
        capture_type=capture_type,
    )
