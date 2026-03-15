#!/usr/bin/env python3
"""
Abstract base adapter for MoE model architectures.
Encapsulates all model-specific details (module paths, router computation,
expert structure, topology constants) behind a common interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Tuple

import torch
import torch.nn as nn
from transformers import PreTrainedModel, PreTrainedTokenizerBase


class RouterStyle(Enum):
    """How the router converts logits to expert assignments."""
    SOFTMAX_THEN_TOPK = auto()   # OLMoE, Mixtral: softmax first, then select top-k
    TOPK_THEN_SOFTMAX = auto()   # ossb20b: select top-k first, then softmax


class ExpertStyle(Enum):
    """How experts are organized in the module."""
    INDIVIDUAL = auto()     # nn.ModuleList of separate experts (OLMoE, Mixtral)
    COLLECTIVE = auto()     # Single fused module for all experts (ossb20b quantized)


@dataclass(frozen=True)
class ModelTopology:
    """Immutable structural constants for a model architecture."""
    num_layers: int
    num_experts: int
    top_k: int
    hidden_size: int
    model_name: str     # Display name (e.g., "OLMoE-1B-7B")
    model_id: str       # HuggingFace model ID (e.g., "allenai/OLMoE-1B-7B-0924")
    model_dir: str      # Local directory name under data/models/


@dataclass(frozen=True)
class ModelCapabilities:
    """Feature flags describing what a model supports."""
    has_individual_experts: bool
    has_shared_experts: bool
    has_router_bias: bool
    router_style: RouterStyle
    expert_style: ExpertStyle


class ModelAdapter(ABC):
    """
    Abstract adapter that encapsulates all model-specific access patterns.

    Subclasses implement the abstract methods for their specific architecture.
    The capture pipeline calls only adapter methods, never model internals directly.
    """

    @property
    @abstractmethod
    def topology(self) -> ModelTopology:
        """Return the model's structural constants."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """Return the model's feature flags."""
        ...

    @abstractmethod
    def load_model(self, model_path: str, device_map: str = "auto") -> Tuple[PreTrainedModel, PreTrainedTokenizerBase]:
        """Load model and tokenizer from local path."""
        ...

    @abstractmethod
    def get_layer(self, model: PreTrainedModel, layer_idx: int) -> nn.Module:
        """Return the transformer layer module at the given index."""
        ...

    @abstractmethod
    def get_moe_block(self, layer: nn.Module) -> nn.Module:
        """Return the MoE block (MLP) from a transformer layer."""
        ...

    @abstractmethod
    def get_router(self, moe_block: nn.Module) -> nn.Module:
        """Return the router module from an MoE block."""
        ...

    @abstractmethod
    def get_experts_module(self, moe_block: nn.Module) -> nn.Module:
        """Return the experts module from an MoE block."""
        ...

    @abstractmethod
    def compute_routing_weights(self, moe_block: nn.Module, hidden_states: torch.Tensor) -> torch.Tensor:
        """
        Compute routing probabilities from hidden states.

        Args:
            moe_block: The MoE block module (same as what hooks receive)
            hidden_states: Input tensor [batch, seq, hidden_dim]

        Returns:
            Routing probabilities [batch, seq, num_experts] (already softmaxed)
        """
        ...

    # Convenience methods (non-abstract)

    def layers_range(self) -> List[int]:
        """Return list of all layer indices."""
        return list(range(self.topology.num_layers))

    def validate_layer(self, layer_idx: int) -> bool:
        """Check if a layer index is valid for this model."""
        return 0 <= layer_idx < self.topology.num_layers

    def validate_expert(self, expert_id: int) -> bool:
        """Check if an expert ID is valid (-1 allowed for collective)."""
        return -1 <= expert_id < self.topology.num_experts
