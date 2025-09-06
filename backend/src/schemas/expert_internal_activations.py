#!/usr/bin/env python3
"""
Expert internal activations schema for individual expert clustering analysis.
Captures FF intermediate states from individual experts for specialization analysis.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np
from datetime import datetime

from utils.numpy_utils import ensure_numpy_array
from utils.parquet_utils import deserialize_array_from_parquet


@dataclass
class ExpertInternalActivation:
    """Expert FF intermediate states for expert specialization analysis."""
    
    # Core identifiers
    probe_id: str               # Links to routing and tokens data
    layer: int                  # Layer number (0-23 for GPT-OSS-20B)
    expert_id: int              # Specific expert (0-31, or -1 for collective in quantized models)
    token_position: int         # Token position in sequence (0=context, 1=target)
    
    # Activation data
    ff_intermediate_state: np.ndarray  # FF activation before output projection
    activation_dims: Tuple[int, ...]   # Shape metadata for validation
    
    # Metadata
    captured_at: str            # ISO timestamp for debugging
    
    def __post_init__(self):
        """Validate activation data consistency."""
        context = f"Probe {self.probe_id} Layer {self.layer} Expert {self.expert_id} Token {self.token_position}"
        
        if not (0 <= self.layer <= 23):
            raise ValueError(f"{context}: Layer {self.layer} out of range [0, 23]")
        
        # Allow expert_id = -1 for collective experts in quantized models
        if not ((-1 <= self.expert_id <= 31)):
            raise ValueError(f"{context}: Expert ID {self.expert_id} out of range [-1, 31]")
        
        if not (0 <= self.token_position <= 1):
            raise ValueError(f"{context}: Token position {self.token_position} out of range [0, 1]")
        
        if self.ff_intermediate_state is None:
            raise ValueError(f"{context}: FF intermediate state cannot be None")
        
        # Ensure consistent dtype
        if self.ff_intermediate_state.dtype != np.float32:
            self.ff_intermediate_state = self.ff_intermediate_state.astype(np.float32)
        
        # Validate activation dimensions match metadata
        actual_dims = tuple(self.ff_intermediate_state.shape)
        if actual_dims != self.activation_dims:
            raise ValueError(
                f"{context}: Activation dims {actual_dims} don't match metadata {self.activation_dims}"
            )
        
        # Basic sanity checks on activation data
        if not np.isfinite(self.ff_intermediate_state).all():
            raise ValueError(f"{context}: FF intermediate state contains non-finite values")

    def activation_norm(self) -> float:
        """Calculate L2 norm of the activation vector."""
        return float(np.linalg.norm(self.ff_intermediate_state))
    
    def activation_sparsity(self) -> float:
        """Calculate sparsity (fraction of near-zero activations)."""
        threshold = 1e-6
        near_zero = np.abs(self.ff_intermediate_state) < threshold
        return float(np.mean(near_zero))
    
    def top_k_activations(self, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Return top-k activation values and their indices."""
        flat_activations = self.ff_intermediate_state.flatten()
        top_k_indices = np.argsort(flat_activations)[-k:][::-1]
        return flat_activations[top_k_indices], top_k_indices

    def activation_percentiles(self, percentiles: List[float] = [25, 50, 75, 90, 95]) -> np.ndarray:
        """Calculate activation percentiles for distribution analysis."""
        return np.percentile(self.ff_intermediate_state.flatten(), percentiles)

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ExpertInternalActivation':
        """Reconstruct from Parquet dictionary with numpy array deserialization."""
        # Deserialize numpy array
        ff_intermediate_state = deserialize_array_from_parquet(
            data['ff_intermediate_state'], 
            tuple(data['activation_dims'])
        )
        
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            expert_id=data['expert_id'],
            token_position=data['token_position'],
            ff_intermediate_state=ff_intermediate_state,
            activation_dims=tuple(data['activation_dims']),
            captured_at=data['captured_at']
        )


# Parquet schema definition
EXPERT_INTERNAL_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "expert_id": "int32",
    "token_position": "int32",
    "ff_intermediate_state": "list<float>",  # Better compression than binary
    "activation_dims": "list<int32>",
    "captured_at": "string"
}


def create_expert_internal_activation(
    probe_id: str,
    layer: int,
    expert_id: int,
    token_position: int,
    ff_intermediate_state: np.ndarray,
    captured_at: Optional[str] = None
) -> ExpertInternalActivation:
    """
    Create expert internal activation record from raw FF intermediate state.
    
    Args:
        probe_id: Unique probe identifier
        layer: Layer number (0-23)
        expert_id: Expert ID (0-31, or -1 for collective in quantized models)
        token_position: Token position in sequence (0=context, 1=target)
        ff_intermediate_state: FF activation before output projection
        captured_at: Capture timestamp (defaults to now)
    
    Returns:
        ExpertInternalActivation record
    """
    if captured_at is None:
        captured_at = datetime.now().isoformat()
    
    # Ensure we have a numpy array
    if not isinstance(ff_intermediate_state, np.ndarray):
        ff_intermediate_state = np.array(ff_intermediate_state, dtype=np.float32)
    
    activation_dims = tuple(ff_intermediate_state.shape)
    
    return ExpertInternalActivation(
        probe_id=probe_id,
        layer=layer,
        expert_id=expert_id,
        token_position=token_position,
        ff_intermediate_state=ff_intermediate_state,
        activation_dims=activation_dims,
        captured_at=captured_at
    )


def serialize_activation_for_parquet(activation: np.ndarray) -> List[float]:
    """Serialize numpy activation for Parquet storage as list<float>."""
    return activation.flatten().tolist()


def deserialize_activation_from_parquet(data: List[float], dims: Tuple[int, ...]) -> np.ndarray:
    """Deserialize activation from Parquet list<float> storage."""
    return np.array(data, dtype=np.float32).reshape(dims)