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
    token_position: int         # Token position in sequence (0=context, 1=target)
    
    # Top-K routing data (K depends on model: 4 for gpt-oss-20b, 8 for OLMoE)
    expert_top4_ids: Tuple[int, ...]                  # Top-K expert IDs
    expert_top4_weights: Tuple[float, ...]            # Routing weights for top-K experts
    
    # Top-1 extraction (for highway analysis)
    expert_top1_id: int         # Highest weighted expert ID
    expert_top1_weight: float   # Top-1 routing weight
    
    # Routing metrics
    gate_entropy: float         # Uncertainty measure: -sum(p * log(p))
    
    # Metadata
    captured_at: str            # ISO timestamp for debugging
    
    def __post_init__(self):
        """Validate routing data consistency."""
        context = f"Probe {self.probe_id} Layer {self.layer}"
        
        if len(self.expert_top4_ids) != len(self.expert_top4_weights):
            raise ValueError(f"{context}: Expert IDs count ({len(self.expert_top4_ids)}) != weights count ({len(self.expert_top4_weights)})")
        
        if self.layer < 0:
            raise ValueError(f"{context}: Layer {self.layer} must be >= 0")

        if not all(expert_id >= 0 for expert_id in self.expert_top4_ids):
            raise ValueError(f"{context}: Expert IDs must be >= 0, got {self.expert_top4_ids}")
        
        # Verify top-1 extraction is consistent
        max_weight_idx = np.argmax(self.expert_top4_weights)
        expected_top1_id = self.expert_top4_ids[max_weight_idx]
        expected_top1_weight = self.expert_top4_weights[max_weight_idx]
        
        if self.expert_top1_id != expected_top1_id:
            raise ValueError(f"{context}: Top-1 expert ID {self.expert_top1_id} doesn't match max weight index {expected_top1_id}")
        
        if not np.isclose(self.expert_top1_weight, expected_top1_weight, rtol=1e-6):
            raise ValueError(f"{context}: Top-1 weight {self.expert_top1_weight} doesn't match max weight {expected_top1_weight}")

    def routing_confidence(self, num_experts: int = 32) -> float:
        """Calculate routing confidence (1 - normalized entropy)."""
        max_entropy = np.log(num_experts)
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
            token_position=data['token_position'],
            expert_top4_ids=tuple(data['expert_top4_ids']),
            expert_top4_weights=tuple(data['expert_top4_weights']),
            expert_top1_id=data['expert_top1_id'],
            expert_top1_weight=data['expert_top1_weight'],
            gate_entropy=data['gate_entropy'],
            captured_at=data['captured_at']
        )


# Parquet schema definition
ROUTING_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "expert_top4_ids": "list<int32>",
    "expert_top4_weights": "list<float>",
    "expert_top1_id": "int32", 
    "expert_top1_weight": "float",
    "gate_entropy": "float",
    "captured_at": "string"
}


def create_routing_record(
    probe_id: str,
    layer: int,
    token_position: int,
    routing_weights: np.ndarray,  # Shape: [num_experts] for all experts
    top_k: int = 4,
    captured_at: Optional[str] = None
) -> RoutingRecord:
    """
    Create routing record from raw MoE router output.

    Args:
        probe_id: Unique probe identifier
        layer: Layer number
        token_position: Token position in sequence (0=context, 1=target)
        routing_weights: Full routing weights for all experts
        top_k: Number of top experts to record (default 4)
        captured_at: Capture timestamp (defaults to now)

    Returns:
        RoutingRecord with top-K data and top-1 extraction
    """
    if captured_at is None:
        captured_at = datetime.now().isoformat()

    # Get top-K experts and weights
    top4_indices = np.argsort(routing_weights)[-top_k:][::-1]  # Descending order
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
        token_position=token_position,
        expert_top4_ids=expert_top4_ids,
        expert_top4_weights=expert_top4_weights,
        expert_top1_id=expert_top1_id,
        expert_top1_weight=expert_top1_weight,
        gate_entropy=float(gate_entropy),
        captured_at=captured_at
    )


def highway_signature(routing_records: List[RoutingRecord], target_tokens_only: bool = True) -> str:
    """
    Generate highway signature from routing records.
    
    Args:
        routing_records: List of routing records for consecutive layers
        target_tokens_only: If True, only use target token (position=1) records for demo
    
    Returns:
        Highway signature like "L1E2→L2E15→L3E7" (for target token routing)
        
    Raises:
        ValueError: If layers are not consecutive or missing target token records
    """
    if not routing_records:
        return ""
    
    # Filter to target tokens only for demo (position=1)
    if target_tokens_only:
        target_records = [r for r in routing_records if r.token_position == 1]
        if not target_records:
            raise ValueError("No target token routing records found (token_position=1)")
        records_to_use = target_records
    else:
        records_to_use = routing_records
    
    sorted_records = sorted(records_to_use, key=lambda r: r.layer)
    
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