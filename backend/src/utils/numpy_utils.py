#!/usr/bin/env python3
"""
Numpy utilities for consistent array handling across all schemas.
Prevents DRY violations in data processing and validation.
"""

from typing import Union, Tuple, List, Any
import numpy as np


def ensure_numpy_array(data: Union[np.ndarray, List, Any], dtype: np.dtype = np.float32) -> np.ndarray:
    """
    Ensure data is a numpy array with consistent dtype.
    
    Args:
        data: Input data (numpy array, list, or array-like)
        dtype: Target numpy dtype (default: float32)
    
    Returns:
        Numpy array with specified dtype
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data, dtype=dtype)
    elif data.dtype != dtype:
        data = data.astype(dtype)
    
    return data


def validate_finite_array(data: np.ndarray, context: str = "Array") -> None:
    """
    Validate that numpy array contains only finite values.
    
    Args:
        data: Numpy array to validate
        context: Context string for error messages
        
    Raises:
        ValueError: If array contains non-finite values (NaN, inf)
    """
    if not np.isfinite(data).all():
        raise ValueError(f"{context}: Array contains non-finite values (NaN/inf)")


def calculate_array_norm(data: np.ndarray) -> float:
    """Calculate L2 norm of array (flattened if multidimensional)."""
    return float(np.linalg.norm(data))


def calculate_array_stats(data: np.ndarray) -> dict:
    """
    Calculate comprehensive statistics for numpy array.
    
    Args:
        data: Input numpy array
        
    Returns:
        Dictionary with mean, std, min, max, median statistics
    """
    flat_data = data.flatten()
    return {
        "mean": float(np.mean(flat_data)),
        "std": float(np.std(flat_data)),
        "min": float(np.min(flat_data)),
        "max": float(np.max(flat_data)),
        "median": float(np.median(flat_data))
    }


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector (any shape, will be flattened)
        vec2: Second vector (any shape, will be flattened)
        
    Returns:
        Cosine similarity score (0-1)
        
    Raises:
        ValueError: If vectors have different total sizes
    """
    # Flatten both vectors
    flat1 = vec1.flatten()
    flat2 = vec2.flatten()
    
    if len(flat1) != len(flat2):
        raise ValueError(f"Vector size mismatch: {len(flat1)} vs {len(flat2)}")
    
    # Compute cosine similarity
    dot_product = np.dot(flat1, flat2)
    norm1 = np.linalg.norm(flat1)
    norm2 = np.linalg.norm(flat2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def normalize_for_clustering(data: np.ndarray, method: str = "standard") -> np.ndarray:
    """
    Normalize array data for clustering analysis.
    
    Args:
        data: Input numpy array (any shape, will be flattened)
        method: Normalization method ("standard", "minmax", "none")
        
    Returns:
        Normalized flat array ready for clustering
        
    Raises:
        ValueError: If normalization method is unknown
    """
    flat_data = data.flatten()
    
    if method == "standard":
        # Z-score normalization (zero mean, unit variance)
        return (flat_data - np.mean(flat_data)) / (np.std(flat_data) + 1e-8)
    elif method == "minmax":
        # Min-max scaling to [0, 1] range
        min_val, max_val = np.min(flat_data), np.max(flat_data)
        return (flat_data - min_val) / (max_val - min_val + 1e-8)
    elif method == "none":
        # No normalization
        return flat_data
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def calculate_sparsity(data: np.ndarray, threshold: float = 1e-6) -> float:
    """
    Calculate sparsity (fraction of near-zero values) in array.
    
    Args:
        data: Input numpy array
        threshold: Values below this are considered zero
        
    Returns:
        Sparsity fraction (0-1)
    """
    near_zero = np.abs(data) < threshold
    return float(np.mean(near_zero))