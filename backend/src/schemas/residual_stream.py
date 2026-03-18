#!/usr/bin/env python3
"""
Residual stream state schema for full decoder layer output capture.
Captures the complete hidden state after attention + MLP (residual_in + attn + mlp).
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
class ResidualStreamState:
    """Full decoder layer output for residual stream analysis."""

    probe_id: str                          # Links to tokens and routing data
    layer: int                             # Layer number
    token_position: int                    # Token position in sequence (0=context, 1=target)
    residual_stream: np.ndarray            # Full decoder layer output (hidden_size D)
    residual_dims: Tuple[int, ...]         # Shape metadata

    def __post_init__(self):
        """Ensure consistent data format and validate ranges."""
        self.residual_stream = ensure_numpy_array(self.residual_stream)

        if self.layer < 0:
            raise ValueError(f"Layer {self.layer} must be >= 0")

        if not (0 <= self.token_position <= 1):
            raise ValueError(f"Token position {self.token_position} out of range [0, 1]")

    def norm(self) -> float:
        return calculate_array_norm(self.residual_stream)

    def stats(self) -> dict:
        return calculate_array_stats(self.residual_stream)

    def similarity_to(self, other) -> float:
        return cosine_similarity(self.residual_stream, other.residual_stream)

    def prepare_for_clustering(self, normalization: str = "standard") -> np.ndarray:
        return normalize_for_clustering(self.residual_stream, normalization)

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ResidualStreamState':
        """Reconstruct from Parquet dictionary with numpy array deserialization."""
        residual_stream = deserialize_array_from_parquet(
            data['residual_stream'],
            tuple(data['residual_dims'])
        )

        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            residual_stream=residual_stream,
            residual_dims=tuple(data['residual_dims'])
        )


# Parquet schema definition
RESIDUAL_STREAM_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "residual_stream": "list<float>",
    "residual_dims": "list<int32>"
}


def create_residual_stream_state(probe_id: str, layer: int, token_position: int, residual_stream: np.ndarray) -> ResidualStreamState:
    """Create residual stream state record from decoder layer output."""
    residual_stream = ensure_numpy_array(residual_stream)
    residual_dims = tuple(residual_stream.shape)

    return ResidualStreamState(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        residual_stream=residual_stream,
        residual_dims=residual_dims
    )
