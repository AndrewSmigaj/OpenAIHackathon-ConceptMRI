#!/usr/bin/env python3
"""
Embedding schema for collective latent space analysis.
Captures the output of the MoE MLP after expert routing, weighting, and combination.
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
class EmbeddingRecord:
    """Post-expert layer outputs for collective latent space clustering analysis."""

    probe_id: str                          # Links to tokens and routing data
    layer: int                             # Layer number
    token_position: int                    # Token position in sequence (0=context, 1=target)
    embedding: np.ndarray                  # Final MoE MLP output
    embedding_dims: Tuple[int, ...]        # Shape metadata

    def __post_init__(self):
        """Ensure consistent data format and validate ranges."""
        self.embedding = ensure_numpy_array(self.embedding)

        if self.layer < 0:
            raise ValueError(f"Layer {self.layer} must be >= 0")

        if not (0 <= self.token_position <= 1):
            raise ValueError(f"Token position {self.token_position} out of range [0, 1]")

    def norm(self) -> float:
        """Calculate L2 norm of the embedding."""
        return calculate_array_norm(self.embedding)

    def stats(self) -> dict:
        """Calculate statistics for the embedding."""
        return calculate_array_stats(self.embedding)

    def similarity_to(self, other) -> float:
        """Calculate cosine similarity with another embedding record."""
        return cosine_similarity(self.embedding, other.embedding)

    def prepare_for_clustering(self, normalization: str = "standard") -> np.ndarray:
        """Prepare embedding for clustering analysis."""
        return normalize_for_clustering(self.embedding, normalization)

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'EmbeddingRecord':
        """Reconstruct from Parquet dictionary with numpy array deserialization."""
        embedding = deserialize_array_from_parquet(
            data['embedding'],
            tuple(data['embedding_dims'])
        )

        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            embedding=embedding,
            embedding_dims=tuple(data['embedding_dims'])
        )


# Parquet schema definition
EMBEDDING_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "embedding": "list<float>",
    "embedding_dims": "list<int32>"
}


def create_embedding_record(probe_id: str, layer: int, token_position: int, embedding: np.ndarray) -> EmbeddingRecord:
    """Create embedding record from MoE MLP output."""
    embedding = ensure_numpy_array(embedding)
    embedding_dims = tuple(embedding.shape)

    return EmbeddingRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        embedding=embedding,
        embedding_dims=embedding_dims
    )
