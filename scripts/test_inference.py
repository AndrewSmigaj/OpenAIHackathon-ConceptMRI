#!/usr/bin/env python3
"""
Test basic inference with gpt-oss-20b MoE model.
Verifies proper loading with MXFP4 quantization and device mapping.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path
import time


def test_model_loading():
    """Test loading the downloaded gpt-oss-20b model."""
    model_dir = Path("data/models/gpt-oss-20b")
    
    if not model_dir.exists():
        print(f"❌ Model directory not found: {model_dir}")
        return False
        
    print("Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        print(f"✅ Tokenizer loaded: {len(tokenizer)} tokens")
    except Exception as e:
        print(f"❌ Tokenizer loading failed: {e}")
        return False
    
    print("\nLoading model with MoE-optimized settings...")
    try:
        # Use documented MoE loading pattern
        model = AutoModelForCausalLM.from_pretrained(
            str(model_dir),
            torch_dtype="auto",  # Let model decide (likely bfloat16)
            device_map="auto",   # Automatic GPU placement
            trust_remote_code=True
        )
        print(f"✅ Model loaded successfully")
        print(f"   Model type: {type(model).__name__}")
        print(f"   Device: {next(model.parameters()).device}")
        print(f"   Dtype: {next(model.parameters()).dtype}")
        
        return model, tokenizer
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False


def test_basic_inference(model, tokenizer):
    """Test basic text generation."""
    print("\nTesting basic inference...")
    
    # Simple test prompts
    test_prompts = [
        "The cat sat on",
        "Machine learning is",
        "In the future"
    ]
    
    try:
        model.eval()
        
        for prompt in test_prompts:
            print(f"\nPrompt: '{prompt}'")
            
            # Tokenize input
            inputs = tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
            
            # Generate with simple settings
            with torch.no_grad():
                start_time = time.time()
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=10,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id
                )
                gen_time = time.time() - start_time
            
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            continuation = generated_text[len(prompt):].strip()
            
            print(f"Output: '{continuation}'")
            print(f"Time: {gen_time:.2f}s")
            
        print("\n✅ Basic inference working")
        return True
        
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        return False


def inspect_moe_structure(model):
    """Inspect the MoE architecture to understand expert layers."""
    print("\nInspecting MoE structure...")
    
    try:
        # Look at model architecture
        print(f"Model config: {model.config}")
        
        # Check for MoE-specific attributes
        moe_attrs = ['num_experts', 'num_experts_per_token', 'expert_capacity', 'moe_layers']
        for attr in moe_attrs:
            if hasattr(model.config, attr):
                print(f"  {attr}: {getattr(model.config, attr)}")
        
        # Examine model structure
        print(f"\nModel structure:")
        for name, module in model.named_modules():
            if 'expert' in name.lower() or 'moe' in name.lower():
                print(f"  MoE layer: {name} -> {type(module).__name__}")
            elif 'layer' in name.lower() and len(name.split('.')) == 3:  # Top-level layers
                print(f"  Layer: {name} -> {type(module).__name__}")
                
        return True
        
    except Exception as e:
        print(f"❌ MoE inspection failed: {e}")
        return False


def main():
    print("=== gpt-oss-20b Inference Test ===\n")
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU: {torch.cuda.get_device_name(0)} ({gpu_memory:.1f} GB)")
    else:
        print("❌ No GPU available")
        return
    
    # Test loading
    result = test_model_loading()
    if not result:
        return
        
    model, tokenizer = result
    
    # Test inference
    if not test_basic_inference(model, tokenizer):
        return
        
    # Inspect MoE structure
    if not inspect_moe_structure(model):
        return
    
    print("\n✅ All tests passed!")
    print("\nNext steps:")
    print("1. Identify specific MoE layers for activation capture")
    print("2. Create PyTorch hooks for expert routing data")
    print("3. Test K=1 expert routing capture")


if __name__ == "__main__":
    main()