#!/usr/bin/env python3
"""
Model adapter for OLMoE-1B-7B (Allen AI's open MoE model).
16 layers, 64 experts, K=8, hidden_size=2048.
Uses OlmoeExperts fused module and OlmoeTopKRouter (nn.Parameter weight, no bias).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from adapters.base_adapter import (
    ModelAdapter, ModelTopology, ModelCapabilities,
    RouterStyle, ExpertStyle,
)


class OLMoEAdapter(ModelAdapter):
    """Adapter for OLMoE-1B-7B MoE architecture."""

    _topology = ModelTopology(
        num_layers=16,
        num_experts=64,
        top_k=8,
        hidden_size=2048,
        model_name="OLMoE-1B-7B",
        model_id="allenai/OLMoE-1B-7B-0924",
        model_dir="OLMoE-1B-7B-0924",
    )

    _capabilities = ModelCapabilities(
        has_individual_experts=False,   # OlmoeExperts is a fused module, not nn.ModuleList
        has_shared_experts=False,
        has_router_bias=False,          # OlmoeTopKRouter uses nn.Parameter weight, no bias
        router_style=RouterStyle.SOFTMAX_THEN_TOPK,
        expert_style=ExpertStyle.COLLECTIVE,  # OlmoeExperts stores weights as 3D tensors
    )

    @property
    def topology(self) -> ModelTopology:
        return self._topology

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._capabilities

    def load_model(self, model_path: str, device_map: str = "auto") -> Tuple[PreTrainedModel, PreTrainedTokenizerBase]:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map=device_map,
        )
        return model, tokenizer

    def get_layer(self, model: PreTrainedModel, layer_idx: int) -> nn.Module:
        return model.model.layers[layer_idx]

    def get_moe_block(self, layer: nn.Module) -> nn.Module:
        return layer.mlp

    def get_router(self, moe_block: nn.Module) -> nn.Module:
        return moe_block.gate  # OlmoeTopKRouter with nn.Parameter weight

    def get_experts_module(self, moe_block: nn.Module) -> nn.Module:
        return moe_block.experts  # OlmoeExperts fused module

    def compute_routing_weights(self, moe_block: nn.Module, hidden_states: torch.Tensor) -> torch.Tensor:
        batch, seq, dim = hidden_states.shape
        flat = hidden_states.reshape(-1, dim)
        # Manual linear using gate's weight parameter (no bias).
        # Cannot call gate(flat) directly — that triggers full top-k routing.
        logits = F.linear(flat, moe_block.gate.weight)
        weights = F.softmax(logits, dim=-1)
        return weights.reshape(batch, seq, -1)
