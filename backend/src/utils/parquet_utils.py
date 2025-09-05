#!/usr/bin/env python3
"""
Parquet serialization utilities for numpy arrays.
Handles consistent serialization/deserialization across all schemas.
"""

from typing import List, Tuple
import numpy as np


def serialize_array_for_parquet(data: np.ndarray) -> List[float]:
    """Serialize numpy array for Parquet storage as list<float>."""
    return data.flatten().tolist()


def deserialize_array_from_parquet(data: List[float], dims: Tuple[int, ...]) -> np.ndarray:
    """Deserialize array from Parquet list<float> storage."""
    return np.array(data, dtype=np.float32).reshape(dims)