#!/usr/bin/env python3
"""
Adapter registry for looking up model adapters by key.
"""

from typing import Dict, List, Type

from adapters.base_adapter import ModelAdapter
from adapters.gptoss_adapter import GptOssAdapter
from adapters.olmoe_adapter import OLMoEAdapter


_REGISTRY: Dict[str, Type[ModelAdapter]] = {}


def register_adapter(key: str, cls: Type[ModelAdapter]) -> None:
    """Register an adapter class under a lookup key."""
    _REGISTRY[key] = cls


def get_adapter(key: str) -> ModelAdapter:
    """Instantiate and return an adapter by key."""
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(f"Unknown model adapter '{key}'. Available: {available}")
    return _REGISTRY[key]()


def list_available_models() -> List[str]:
    """Return list of registered adapter keys."""
    return sorted(_REGISTRY.keys())


# Auto-register built-in adapters
register_adapter("gpt-oss-20b", GptOssAdapter)
register_adapter("olmoe-1b-7b", OLMoEAdapter)

# Aliases for convenience (HuggingFace model IDs)
register_adapter("allenai/OLMoE-1B-7B-0924", OLMoEAdapter)
register_adapter("openai/gpt-oss-20b", GptOssAdapter)
