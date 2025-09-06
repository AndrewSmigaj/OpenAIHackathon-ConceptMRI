#!/usr/bin/env python3
"""
Ultra-simple GPU memory utilities for demo stability.
Just cleanup and reporting - no fancy context managers.
"""

import torch
from typing import Dict, Union


def cleanup_gpu_memory():
    """Clean up GPU memory - call after capture operations."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_gpu_memory_info() -> Dict[str, Union[float, str]]:
    """Get current GPU memory usage for debugging."""
    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}
    
    allocated = torch.cuda.memory_allocated() / 1024**3  # GB
    reserved = torch.cuda.memory_reserved() / 1024**3    # GB
    max_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
    
    return {
        "allocated_gb": round(allocated, 2),
        "reserved_gb": round(reserved, 2), 
        "max_memory_gb": round(max_memory, 2),
        "utilization_percent": round((allocated / max_memory) * 100, 1)
    }