"""
Model adapter package for MoE architecture abstraction.

Usage:
    from adapters import get_adapter, list_available_models

    adapter = get_adapter("olmoe-1b-7b")
    model, tokenizer = adapter.load_model("data/models/OLMoE-1B-7B-0924")
"""

from adapters.base_adapter import (
    ModelAdapter,
    ModelTopology,
    ModelCapabilities,
    RouterStyle,
    ExpertStyle,
)
from adapters.registry import get_adapter, list_available_models
