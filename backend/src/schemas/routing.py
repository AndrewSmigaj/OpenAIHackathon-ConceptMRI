#!/usr/bin/env python3
"""
Routing schema for K=4 MoE routing capture with top-1 expert extraction.
Captures routing decisions from GptOssTopKRouter for all 32 experts per layer.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from datetime import datetime


@dataclass
class RoutingRecord:
    """K=4 routing capture with top-1 extraction for expert highway analysis."""
    
    # Core identifiers
    probe_id: str               # Links to tokens and features
    layer: int                  # Layer number (0-23 for GPT-OSS-20B)
    
    # K=4 routing data (full capture for future expansion)
    expert_top4_ids: Tuple[int, int, int, int]        # Top-4 expert IDs [0-31]
    expert_top4_weights: Tuple[float, float, float, float] # Routing weights for top-4 experts
    
    # Top-1 extraction (for highway analysis)
    expert_top1_id: int         # Highest weighted expert ID
    expert_top1_weight: float   # Top-1 routing weight
    
    # Routing metrics
    gate_entropy: float         # Uncertainty measure: -sum(p * log(p))
    routing_aux_loss: float     # Auxiliary routing loss
    
    # Metadata
    captured_at: str            # ISO timestamp for debugging
    
    def __post_init__(self):
        """Validate routing data consistency."""
        context = f"Probe {self.probe_id} Layer {self.layer}"
        
        if len(self.expert_top4_ids) != 4:
            raise ValueError(f"{context}: Expected 4 expert IDs, got {len(self.expert_top4_ids)}")
        
        if len(self.expert_top4_weights) != 4:
            raise ValueError(f"{context}: Expected 4 routing weights, got {len(self.expert_top4_weights)}")
        
        if not (0 <= self.layer <= 23):
            raise ValueError(f"{context}: Layer {self.layer} out of range [0, 23]")
        
        if not all(0 <= expert_id <= 31 for expert_id in self.expert_top4_ids):
            raise ValueError(f"{context}: Expert IDs must be in range [0, 31], got {self.expert_top4_ids}")
        
        # Verify top-1 extraction is consistent
        max_weight_idx = np.argmax(self.expert_top4_weights)
        expected_top1_id = self.expert_top4_ids[max_weight_idx]
        expected_top1_weight = self.expert_top4_weights[max_weight_idx]
        
        if self.expert_top1_id != expected_top1_id:
            raise ValueError(f"{context}: Top-1 expert ID {self.expert_top1_id} doesn't match max weight index {expected_top1_id}")
        
        if not np.isclose(self.expert_top1_weight, expected_top1_weight, rtol=1e-6):
            raise ValueError(f"{context}: Top-1 weight {self.expert_top1_weight} doesn't match max weight {expected_top1_weight}")

    def routing_confidence(self) -> float:
        """Calculate routing confidence (1 - normalized entropy)."""
        max_entropy = np.log(32)  # Max entropy for 32 experts
        return 1.0 - (self.gate_entropy / max_entropy)
    
    def routing_margin(self) -> float:
        """Calculate margin between top-1 and top-2 expert weights."""
        if len(self.expert_top4_weights) < 2:
            return 0.0
        return self.expert_top4_weights[0] - self.expert_top4_weights[1]

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'RoutingRecord':
        """Reconstruct from Parquet dictionary with tuple conversion."""
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            expert_top4_ids=tuple(data['expert_top4_ids']),
            expert_top4_weights=tuple(data['expert_top4_weights']),
            expert_top1_id=data['expert_top1_id'],
            expert_top1_weight=data['expert_top1_weight'],
            gate_entropy=data['gate_entropy'],
            routing_aux_loss=data['routing_aux_loss'],
            captured_at=data['captured_at']
        )


# Parquet schema definition
ROUTING_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "expert_top4_ids": "list<int32>",
    "expert_top4_weights": "list<float>",
    "expert_top1_id": "int32", 
    "expert_top1_weight": "float",
    "gate_entropy": "float",
    "routing_aux_loss": "float",
    "captured_at": "string"
}


def create_routing_record(
    probe_id: str,
    layer: int,
    routing_weights: np.ndarray,  # Shape: [32] for all experts
    routing_aux_loss: float,
    captured_at: Optional[str] = None
) -> RoutingRecord:
    """
    Create routing record from raw MoE router output.
    
    Args:
        probe_id: Unique probe identifier
        layer: Layer number (0-23)
        routing_weights: Full routing weights for all 32 experts
        routing_aux_loss: Auxiliary routing loss
        captured_at: Capture timestamp (defaults to now)
    
    Returns:
        RoutingRecord with K=4 data and top-1 extraction
    """
    if captured_at is None:
        captured_at = datetime.now().isoformat()
    
    if routing_weights.shape[0] != 32:
        raise ValueError(f"Expected 32 expert weights, got {routing_weights.shape[0]}")
    
    # Get top-4 experts and weights
    top4_indices = np.argsort(routing_weights)[-4:][::-1]  # Descending order
    expert_top4_ids = tuple(top4_indices.tolist())
    expert_top4_weights = tuple(routing_weights[top4_indices].tolist())
    
    # Extract top-1 (first in descending order)
    expert_top1_id = expert_top4_ids[0]
    expert_top1_weight = expert_top4_weights[0]
    
    # Calculate gate entropy
    eps = 1e-8
    log_weights = np.log(routing_weights + eps)
    gate_entropy = -np.sum(routing_weights * log_weights)
    
    return RoutingRecord(
        probe_id=probe_id,
        layer=layer,
        expert_top4_ids=expert_top4_ids,
        expert_top4_weights=expert_top4_weights,
        expert_top1_id=expert_top1_id,
        expert_top1_weight=expert_top1_weight,
        gate_entropy=float(gate_entropy),
        routing_aux_loss=float(routing_aux_loss),
        captured_at=captured_at
    )


def highway_signature(routing_records: List[RoutingRecord]) -> str:
    """
    Generate highway signature from routing records.
    
    Args:
        routing_records: Ordered list of routing records for consecutive layers
    
    Returns:
        Highway signature like "L6E2→L7E15→L8E7"
        
    Raises:
        ValueError: If layers are not consecutive
    """
    if not routing_records:
        return ""
    
    sorted_records = sorted(routing_records, key=lambda r: r.layer)
    
    # Check for consecutive layers
    for i in range(1, len(sorted_records)):
        if sorted_records[i].layer != sorted_records[i-1].layer + 1:
            layers = [r.layer for r in sorted_records]
            raise ValueError(f"Non-consecutive layers in highway: {layers}")
    
    signature_parts = []
    for record in sorted_records:
        part = f"L{record.layer}E{record.expert_top1_id}"
        signature_parts.append(part)
    
    return "→".join(signature_parts)