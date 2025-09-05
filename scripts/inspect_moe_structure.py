#!/usr/bin/env python3
"""
Inspect the MoE structure of gpt-oss-20b to understand expert routing.
Focus on identifying which layers have experts and how routing works.
"""

import torch
from transformers import AutoModelForCausalLM, AutoConfig
from pathlib import Path


def load_model_safely():
    """Load model using the working quantized approach."""
    from transformers.utils.quantization_config import Mxfp4Config
    
    model_id = "openai/gpt-oss-20b"  # Use HuggingFace directly
    
    print("Loading model config...")
    config = AutoConfig.from_pretrained(model_id)
    
    print("Loading model with MXFP4 quantization (working configuration)...")
    try:
        quantization_config = Mxfp4Config()
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            max_memory={0: "14GB", "cpu": "16GB"},
        )
        return model, config
    except Exception as e:
        print(f"Full loading failed: {e}")
        # Try loading just config and architecture info
        return None, config


def inspect_config(config):
    """Inspect model configuration for MoE details."""
    print("\n=== Model Configuration ===")
    print(f"Model type: {config.model_type}")
    print(f"Architecture: {config.architectures}")
    print(f"Vocab size: {config.vocab_size}")
    print(f"Hidden size: {config.hidden_size}")
    print(f"Num layers: {config.num_hidden_layers}")
    print(f"Num attention heads: {config.num_attention_heads}")
    
    # Look for MoE specific config
    moe_attrs = [
        'num_experts', 'num_experts_per_token', 'expert_capacity',
        'moe_layers', 'router_aux_loss_coef', 'router_z_loss_coef',
        'intermediate_size', 'moe_freq', 'first_k_dense_replace'
    ]
    
    print("\n=== MoE Configuration ===")
    for attr in moe_attrs:
        if hasattr(config, attr):
            value = getattr(config, attr)
            print(f"  {attr}: {value}")


def inspect_model_structure(model):
    """Inspect the actual model structure to find expert layers."""
    if model is None:
        print("Model not loaded, skipping structure inspection")
        return
        
    print("\n=== Model Structure Analysis ===")
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,} ({total_params/1e9:.2f}B)")
    
    # Find MoE layers
    expert_layers = []
    router_layers = []
    
    for name, module in model.named_modules():
        if 'expert' in name.lower():
            expert_layers.append((name, type(module).__name__))
        elif 'router' in name.lower() or 'gate' in name.lower():
            router_layers.append((name, type(module).__name__))
    
    print(f"\nFound {len(expert_layers)} expert components:")
    for name, mod_type in expert_layers[:10]:  # Show first 10
        print(f"  {name} -> {mod_type}")
    if len(expert_layers) > 10:
        print(f"  ... and {len(expert_layers) - 10} more")
    
    print(f"\nFound {len(router_layers)} routing components:")
    for name, mod_type in router_layers:
        print(f"  {name} -> {mod_type}")
    
    # Examine layer structure
    print(f"\n=== Layer-by-Layer Analysis ===")
    if hasattr(model, 'transformer') and hasattr(model.transformer, 'h'):
        layers = model.transformer.h
    elif hasattr(model, 'model') and hasattr(model.model, 'layers'):
        layers = model.model.layers
    else:
        print("Could not find transformer layers")
        return
    
    print(f"Found {len(layers)} transformer layers")
    
    # Inspect first few layers in detail
    for i, layer in enumerate(layers[:3]):
        print(f"\nLayer {i}:")
        for name, module in layer.named_modules():
            if name:  # Skip the layer itself
                print(f"  {name} -> {type(module).__name__}")
                # Check for MoE specific attributes
                if hasattr(module, 'num_experts'):
                    print(f"    num_experts: {module.num_experts}")
                if hasattr(module, 'top_k'):
                    print(f"    top_k: {module.top_k}")
    
    return layers


def find_routing_layer(model):
    """Find a specific layer we can hook for routing analysis."""
    if model is None:
        return None
        
    # Look for the routing/gating mechanism
    routing_targets = []
    
    for name, module in model.named_modules():
        # Look for router/gate modules
        if any(keyword in name.lower() for keyword in ['router', 'gate']) and hasattr(module, 'forward'):
            routing_targets.append((name, module))
    
    print(f"\n=== Potential Routing Hook Targets ===")
    for name, module in routing_targets:
        print(f"  {name} -> {type(module).__name__}")
        # Check what the forward method expects
        try:
            if hasattr(module, 'weight'):
                print(f"    Weight shape: {module.weight.shape}")
        except:
            pass
    
    return routing_targets


def main():
    print("=== MoE Structure Inspection ===\n")
    
    # Load model and config
    model, config = load_model_safely()
    
    # Inspect configuration
    inspect_config(config)
    
    # Inspect model structure if loaded
    layers = inspect_model_structure(model)
    
    # Find routing hook points
    routing_targets = find_routing_layer(model)
    
    print("\n=== Summary ===")
    if config:
        num_layers = getattr(config, 'num_hidden_layers', 'unknown')
        print(f"✅ Model has {num_layers} layers")
        
        if hasattr(config, 'num_experts'):
            print(f"✅ MoE with {config.num_experts} experts per layer")
        else:
            print("❓ MoE configuration unclear from config")
    
    if model:
        print("✅ Model structure analyzed")
        if routing_targets:
            print(f"✅ Found {len(routing_targets)} potential routing hook points")
        else:
            print("❌ No clear routing hook points found")
    else:
        print("❌ Model not fully loaded")
    
    print("\nNext steps:")
    print("1. Fix model loading issues")
    print("2. Create hooks for routing capture")
    print("3. Test with simple inputs")


if __name__ == "__main__":
    main()