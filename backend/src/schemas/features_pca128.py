#!/usr/bin/env python3
"""
Dimensionality reduction features schema.
Supports PCA and UMAP from expert output or residual stream sources.
Backward-compatible: PCAFeatureRecord and create_pca_features still work.
"""

from dataclasses import dataclass
import numpy as np

from utils.numpy_utils import ensure_numpy_array
from utils.parquet_utils import deserialize_array_from_parquet


@dataclass
class ReductionFeatureRecord:
    """Dimensionality-reduced features per probe and layer."""

    probe_id: str              # Links to tokens and activation data
    layer: int                 # Layer number
    token_position: int        # Token position (0=context, 1=target)
    features: np.ndarray       # N-dimensional reduced features
    method: str                # "pca" or "umap"
    source: str                # "expert_output" or "residual_stream"

    def __post_init__(self):
        self.features = ensure_numpy_array(self.features)

    def for_3d_viz(self) -> np.ndarray:
        """Get first 3 components for 3D visualization."""
        return self.features[:3]

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ReductionFeatureRecord':
        features = deserialize_array_from_parquet(data['features'], (len(data['features']),))
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            features=features,
            method=data.get('method', 'pca'),
            source=data.get('source', 'expert_output'),
        )


# New generic schema
REDUCTION_FEATURES_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "features": "list<float>",
    "method": "string",
    "source": "string",
}


def create_reduction_features(
    probe_id: str, layer: int, token_position: int,
    features: np.ndarray, method: str = "pca", source: str = "expert_output"
) -> ReductionFeatureRecord:
    return ReductionFeatureRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        features=ensure_numpy_array(features),
        method=method,
        source=source,
    )


# --- Backward compatibility ---

@dataclass
class PCAFeatureRecord:
    """128-dimensional PCA features per probe and layer (backward compat)."""

    probe_id: str
    layer: int
    token_position: int
    pca128: np.ndarray

    def __post_init__(self):
        self.pca128 = ensure_numpy_array(self.pca128)

    def for_3d_viz(self) -> np.ndarray:
        return self.pca128[:3]

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'PCAFeatureRecord':
        pca128 = deserialize_array_from_parquet(data['pca128'], (len(data['pca128']),))
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            pca128=pca128
        )


FEATURES_PCA128_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "pca128": "list<float>"
}


def create_pca_features(probe_id: str, layer: int, token_position: int, pca128: np.ndarray) -> PCAFeatureRecord:
    """Create PCA features record (backward compat)."""
    return PCAFeatureRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        pca128=ensure_numpy_array(pca128)
    )
