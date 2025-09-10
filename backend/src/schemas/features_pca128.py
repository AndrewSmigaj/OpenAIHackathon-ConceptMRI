#!/usr/bin/env python3
"""
PCA128 features schema for dimensionality reduction results.
Reduces 2880-dimensional expert outputs to 128 dimensions for clustering.
First 3 components used for 3D visualization.
"""

from dataclasses import dataclass
import numpy as np

from utils.numpy_utils import ensure_numpy_array
from utils.parquet_utils import deserialize_array_from_parquet


@dataclass
class PCAFeatureRecord:
    """128-dimensional PCA features per probe and layer."""
    
    probe_id: str              # Links to tokens and activation data
    layer: int                 # Layer number (0-23)
    token_position: int        # Token position (0=context, 1=target)
    pca128: np.ndarray         # 128-dimensional PCA features
    
    def __post_init__(self):
        """Ensure consistent data format."""
        self.pca128 = ensure_numpy_array(self.pca128)

    def for_3d_viz(self) -> np.ndarray:
        """Get first 3 components for 3D visualization."""
        return self.pca128[:3]

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'PCAFeatureRecord':
        """Reconstruct from Parquet dictionary with numpy array deserialization."""
        # PCA128 is a 1D array, so dims are just the length
        pca128 = deserialize_array_from_parquet(data['pca128'], (len(data['pca128']),))
        
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            pca128=pca128
        )


# Parquet schema definition  
FEATURES_PCA128_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "pca128": "list<float>"        # 128-dimensional features
}


def create_pca_features(probe_id: str, layer: int, token_position: int, pca128: np.ndarray) -> PCAFeatureRecord:
    """Create PCA features record."""
    return PCAFeatureRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        pca128=ensure_numpy_array(pca128)
    )