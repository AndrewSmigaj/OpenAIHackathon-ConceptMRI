#!/usr/bin/env python3
"""
Routing schema for MoE routing capture with full routing weights vector.
Captures routing decisions from MoE router for all experts per layer.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from datetime import datetime


@dataclass
class RoutingRecord:
    """Full routing capture with top-1 extraction for expert highway analysis."""

    # Core identifiers
    probe_id: str               # Links to tokens and features
    layer: int                  # Layer number
    token_position: int         # Token position in sequence (0=context, 1=target)

    # Full routing weights vector (all experts)
    routing_weights: np.ndarray  # Shape: [num_experts], softmaxed probabilities
    num_experts: int             # Number of experts in this layer

    # Top-1 extraction (for highway analysis)
    expert_top1_id: int         # Highest weighted expert ID
    expert_top1_weight: float   # Top-1 routing weight

    # Routing metrics
    gate_entropy: float         # Uncertainty measure: -sum(p * log(p))

    # Metadata
    captured_at: str            # ISO timestamp for debugging

    # Agent session fields (null for batch captures)
    turn_id: Optional[int] = None
    scenario_id: Optional[str] = None
    capture_type: Optional[str] = None  # "batch", "reasoning", "knowledge_query"

    def __post_init__(self):
        """Validate routing data consistency."""
        context = f"Probe {self.probe_id} Layer {self.layer}"

        if not isinstance(self.routing_weights, np.ndarray):
            self.routing_weights = np.array(self.routing_weights)

        if self.routing_weights.ndim != 1:
            raise ValueError(f"{context}: routing_weights must be 1D, got shape {self.routing_weights.shape}")

        if len(self.routing_weights) != self.num_experts:
            raise ValueError(f"{context}: routing_weights length ({len(self.routing_weights)}) != num_experts ({self.num_experts})")

        if self.layer < 0:
            raise ValueError(f"{context}: Layer {self.layer} must be >= 0")

        # Verify top-1 extraction is consistent with routing_weights
        expected_top1_id = int(np.argmax(self.routing_weights))
        expected_top1_weight = float(self.routing_weights[expected_top1_id])

        if self.expert_top1_id != expected_top1_id:
            raise ValueError(f"{context}: Top-1 expert ID {self.expert_top1_id} doesn't match argmax {expected_top1_id}")

        if not np.isclose(self.expert_top1_weight, expected_top1_weight, rtol=1e-6):
            raise ValueError(f"{context}: Top-1 weight {self.expert_top1_weight} doesn't match max weight {expected_top1_weight}")

    def routing_confidence(self) -> float:
        """Calculate routing confidence (1 - normalized entropy)."""
        max_entropy = np.log(self.num_experts)
        return 1.0 - (self.gate_entropy / max_entropy)

    def routing_margin(self) -> float:
        """Calculate margin between top-1 and top-2 expert weights."""
        sorted_weights = np.sort(self.routing_weights)[::-1]  # Descending
        if len(sorted_weights) < 2:
            return 0.0
        return float(sorted_weights[0] - sorted_weights[1])

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'RoutingRecord':
        """Reconstruct from Parquet dictionary."""
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            routing_weights=np.array(data['routing_weights']),
            num_experts=data['num_experts'],
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
    "routing_weights": "list<float>",
    "num_experts": "int32",
    "expert_top1_id": "int32",
    "expert_top1_weight": "float",
    "gate_entropy": "float",
    "captured_at": "string",
    "turn_id": "int32",
    "scenario_id": "string",
    "capture_type": "string",
}


def create_routing_record(
    probe_id: str,
    layer: int,
    token_position: int,
    routing_weights: np.ndarray,  # Shape: [num_experts] for all experts
    captured_at: Optional[str] = None,
    turn_id: Optional[int] = None,
    scenario_id: Optional[str] = None,
    capture_type: Optional[str] = None,
) -> RoutingRecord:
    """
    Create routing record from raw MoE router output.

    Args:
        probe_id: Unique probe identifier
        layer: Layer number
        token_position: Token position in sequence (0=context, 1=target)
        routing_weights: Full routing weights for all experts (softmaxed)
        captured_at: Capture timestamp (defaults to now)

    Returns:
        RoutingRecord with full weights and top-1 extraction
    """
    if captured_at is None:
        captured_at = datetime.now().isoformat()

    if not isinstance(routing_weights, np.ndarray):
        routing_weights = np.array(routing_weights)

    num_experts = routing_weights.shape[0]

    # Extract top-1
    expert_top1_id = int(np.argmax(routing_weights))
    expert_top1_weight = float(routing_weights[expert_top1_id])

    # Calculate gate entropy
    eps = 1e-8
    log_weights = np.log(routing_weights + eps)
    gate_entropy = -np.sum(routing_weights * log_weights)

    return RoutingRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        routing_weights=routing_weights,
        num_experts=num_experts,
        expert_top1_id=expert_top1_id,
        expert_top1_weight=expert_top1_weight,
        gate_entropy=float(gate_entropy),
        captured_at=captured_at,
        turn_id=turn_id,
        scenario_id=scenario_id,
        capture_type=capture_type,
    )


def highway_signature(
    routing_records: List[RoutingRecord],
    target_tokens_only: bool = True,
    expert_rank: int = 1,
) -> str:
    """
    Generate highway signature from routing records.

    Args:
        routing_records: List of routing records for consecutive layers
        target_tokens_only: If True, only use target token (position=1) records for demo
        expert_rank: Which rank of expert to visualize per (probe, layer).
            1 = top-1 (argmax, identical to expert_top1_id).
            2 = second-highest weighted expert, etc.

    Returns:
        Highway signature like "L1E2→L2E15→L3E7" (for target token routing)

    Raises:
        ValueError: If layers are not consecutive, missing target token records,
            or expert_rank is out of range for any record's num_experts.
    """
    if not routing_records:
        return ""

    if expert_rank < 1:
        raise ValueError(f"expert_rank must be >= 1, got {expert_rank}")

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
        if expert_rank == 1:
            expert_id = record.expert_top1_id
        else:
            if expert_rank > record.num_experts:
                raise ValueError(
                    f"expert_rank {expert_rank} exceeds num_experts {record.num_experts} "
                    f"at layer {record.layer}"
                )
            # argsort ascending; -expert_rank picks the Nth-highest weight
            expert_id = int(np.argsort(record.routing_weights)[-expert_rank])
        signature_parts.append(f"L{record.layer}E{expert_id}")

    return "→".join(signature_parts)
