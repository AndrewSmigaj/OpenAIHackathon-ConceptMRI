#!/usr/bin/env python3
"""
Check system requirements for ossb20b MoE model.
Verify GPU memory, CUDA setup, and dependencies.
"""

import torch
import sys
from typing import Dict, Any


def check_cuda_setup() -> Dict[str, Any]:
    """Check CUDA availability and version."""
    cuda_info = {
        "available": torch.cuda.is_available(),
        "version": None,
        "device_count": 0,
        "devices": []
    }
    
    if torch.cuda.is_available():
        cuda_info["version"] = torch.version.cuda
        cuda_info["device_count"] = torch.cuda.device_count()
        
        for i in range(torch.cuda.device_count()):
            device = torch.cuda.get_device_properties(i)
            cuda_info["devices"].append({
                "id": i,
                "name": device.name,
                "memory_total_gb": device.total_memory / (1024**3),
                "memory_reserved_gb": torch.cuda.memory_reserved(i) / (1024**3),
                "memory_allocated_gb": torch.cuda.memory_allocated(i) / (1024**3)
            })
    
    return cuda_info


def estimate_model_requirements() -> Dict[str, float]:
    """Estimate memory requirements for ossb20b with quantization."""
    # ossb20b is approximately 20B parameters
    params = 20e9
    
    # Memory estimates in GB
    estimates = {
        "fp32_gb": params * 4 / (1024**3),  # 4 bytes per parameter
        "fp16_gb": params * 2 / (1024**3),  # 2 bytes per parameter  
        "nf4_gb": params * 0.5 / (1024**3),  # NF4 quantization ~0.5 bytes per param
        "recommended_total_gb": params * 0.5 / (1024**3) * 1.5  # Add 50% overhead
    }
    
    return estimates


def check_dependencies():
    """Check if required packages are available."""
    deps = {}
    
    try:
        import transformers
        deps["transformers"] = transformers.__version__
    except ImportError:
        deps["transformers"] = "NOT INSTALLED"
    
    try:
        import bitsandbytes
        deps["bitsandbytes"] = bitsandbytes.__version__
    except ImportError:
        deps["bitsandbytes"] = "NOT INSTALLED"
        
    try:
        import accelerate  
        deps["accelerate"] = accelerate.__version__
    except ImportError:
        deps["accelerate"] = "NOT INSTALLED"
    
    return deps


def main():
    print("=== System Requirements Check for ossb20b ===\n")
    
    # Python version
    print(f"Python: {sys.version}")
    print(f"PyTorch: {torch.__version__}\n")
    
    # CUDA setup
    print("CUDA Setup:")
    cuda_info = check_cuda_setup()
    
    if cuda_info["available"]:
        print(f"✅ CUDA Available: {cuda_info['version']}")
        print(f"✅ GPU Count: {cuda_info['device_count']}")
        
        for device in cuda_info["devices"]:
            print(f"  GPU {device['id']}: {device['name']}")
            print(f"    Total Memory: {device['memory_total_gb']:.1f} GB")
            print(f"    Reserved: {device['memory_reserved_gb']:.1f} GB") 
            print(f"    Allocated: {device['memory_allocated_gb']:.1f} GB")
            print(f"    Free: {device['memory_total_gb'] - device['memory_reserved_gb']:.1f} GB")
    else:
        print("❌ CUDA not available")
        return
    
    # Memory estimates
    print("\nModel Memory Requirements:")
    estimates = estimate_model_requirements()
    
    print(f"  FP32: {estimates['fp32_gb']:.1f} GB")
    print(f"  FP16: {estimates['fp16_gb']:.1f} GB") 
    print(f"  NF4:  {estimates['nf4_gb']:.1f} GB")
    print(f"  Recommended Total: {estimates['recommended_total_gb']:.1f} GB")
    
    # Check if we have enough memory
    total_gpu_memory = sum(d["memory_total_gb"] for d in cuda_info["devices"])
    free_gpu_memory = sum(d["memory_total_gb"] - d["memory_reserved_gb"] for d in cuda_info["devices"])
    
    if free_gpu_memory >= estimates["recommended_total_gb"]:
        print(f"✅ Sufficient GPU memory available ({free_gpu_memory:.1f} GB)")
    else:
        print(f"⚠️  May need more GPU memory ({free_gpu_memory:.1f} GB available, {estimates['recommended_total_gb']:.1f} GB recommended)")
    
    # Dependencies
    print("\nDependencies:")
    deps = check_dependencies()
    
    for name, version in deps.items():
        if version == "NOT INSTALLED":
            print(f"❌ {name}: {version}")
        else:
            print(f"✅ {name}: {version}")
    
    # Final assessment
    print("\nAssessment:")
    if (cuda_info["available"] and 
        free_gpu_memory >= estimates["nf4_gb"] and
        all(v != "NOT INSTALLED" for v in deps.values())):
        print("✅ System appears ready for ossb20b with NF4 quantization")
    else:
        print("❌ System may need setup before running ossb20b")


if __name__ == "__main__":
    main()