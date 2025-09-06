#!/usr/bin/env python3
"""
Expert output states schema for collective latent space analysis.
Captures the output of GptOssMLP after K=4 expert routing, weighting, and combination.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np

from utils.numpy_utils import (
    ensure_numpy_array,
    calculate_array_norm,
    calculate_array_stats,
    cosine_similarity,
    normalize_for_clustering
)
from utils.parquet_utils import deserialize_array_from_parquet


@dataclass
class ExpertOutputState:
    """Post-expert layer outputs for collective latent space clustering analysis."""
    
    probe_id: str                          # Links to tokens and routing data
    layer: int                             # Layer number (0-23)
    token_position: int                    # Token position in sequence (0=context, 1=target)
    expert_output_state: np.ndarray        # Final GptOssMLP output
    post_expert_dims: Tuple[int, ...]      # Shape metadata
    
    def __post_init__(self):
        """Ensure consistent data format and validate ranges."""
        self.expert_output_state = ensure_numpy_array(self.expert_output_state)
        
        # Validate ranges
        if not (0 <= self.layer <= 23):
            raise ValueError(f"Layer {self.layer} out of range [0, 23]")
        
        if not (0 <= self.token_position <= 1):
            raise ValueError(f"Token position {self.token_position} out of range [0, 1]")

    def norm(self) -> float:
        """Calculate L2 norm of the output state."""
        return calculate_array_norm(self.expert_output_state)
    
    def stats(self) -> dict:
        """Calculate statistics for the output state."""
        return calculate_array_stats(self.expert_output_state)
    
    def similarity_to(self, other) -> float:
        """Calculate cosine similarity with another expert output state."""
        return cosine_similarity(self.expert_output_state, other.expert_output_state)

    def prepare_for_clustering(self, normalization: str = "standard") -> np.ndarray:
        """Prepare output state for clustering analysis."""
        return normalize_for_clustering(self.expert_output_state, normalization)

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ExpertOutputState':
        """Reconstruct from Parquet dictionary with numpy array deserialization."""
        # Deserialize numpy array
        expert_output_state = deserialize_array_from_parquet(
            data['expert_output_state'], 
            tuple(data['post_expert_dims'])
        )
        
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            expert_output_state=expert_output_state,
            post_expert_dims=tuple(data['post_expert_dims'])
        )


# Parquet schema definition
EXPERT_OUTPUT_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "expert_output_state": "list<float>",
    "post_expert_dims": "list<int32>"
}


def create_expert_output_state(probe_id: str, layer: int, token_position: int, expert_output_state: np.ndarray) -> ExpertOutputState:
    """Create expert output state record from GptOssMLP output."""
    expert_output_state = ensure_numpy_array(expert_output_state)
    post_expert_dims = tuple(expert_output_state.shape)
    
    return ExpertOutputState(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        expert_output_state=expert_output_state,
        post_expert_dims=post_expert_dims
    )