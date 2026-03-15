#!/usr/bin/env python3
"""
Model adapter for gpt-oss-20b (OpenAI's open-source MoE model).
24 layers, 32 experts, K=4, hidden_size=2880.
Uses fused collective experts module and router with bias.
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


class GptOssAdapter(ModelAdapter):
    """Adapter for gpt-oss-20b MoE architecture."""

    _topology = ModelTopology(
        num_layers=24,
        num_experts=32,
        top_k=4,
        hidden_size=2880,
        model_name="gpt-oss-20b",
        model_id="openai/gpt-oss-20b",
        model_dir="gpt-oss-20b",
    )

    _capabilities = ModelCapabilities(
        has_individual_experts=False,
        has_shared_experts=False,
        has_router_bias=True,
        router_style=RouterStyle.TOPK_THEN_SOFTMAX,
        expert_style=ExpertStyle.COLLECTIVE,
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
            dtype=torch.float16,
            device_map=device_map,
            trust_remote_code=True,
        )
        return model, tokenizer

    def get_layer(self, model: PreTrainedModel, layer_idx: int) -> nn.Module:
        return model.model.layers[layer_idx]

    def get_moe_block(self, layer: nn.Module) -> nn.Module:
        return layer.mlp

    def get_router(self, moe_block: nn.Module) -> nn.Module:
        return moe_block.router  # GptOssTopKRouter with weight + bias

    def get_experts_module(self, moe_block: nn.Module) -> nn.Module:
        return moe_block.experts  # Fused GptOssExperts module

    def compute_routing_weights(self, moe_block: nn.Module, hidden_states: torch.Tensor) -> torch.Tensor:
        batch, seq, dim = hidden_states.shape
        flat = hidden_states.reshape(-1, dim)
        router = moe_block.router
        logits = F.linear(flat, router.weight, router.bias)
        weights = F.softmax(logits, dim=-1)
        return weights.reshape(batch, seq, -1)
