#!/usr/bin/env python3
"""
Test loading the original GPT-OSS-20B with MXFP4 quantization directly.
Skip dequantization for now and work with the quantized model.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.utils.quantization_config import Mxfp4Config
import time

def test_quantized_model():
    """Test loading the original quantized GPT-OSS-20B model."""
    print("=== GPT-OSS-20B Quantized Model Test ===\n")
    
    model_id = "openai/gpt-oss-20b"
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        print("❌ No CUDA GPU available")
        return False
    
    print(f"Testing model: {model_id}")
    
    # Step 1: Load tokenizer
    print("\nStep 1: Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        print(f"✅ Tokenizer loaded: {len(tokenizer)} tokens")
    except Exception as e:
        print(f"❌ Tokenizer failed: {e}")
        return False
    
    # Step 2: Load model with quantization (no dequantization)
    print("\nStep 2: Loading model with MXFP4 quantization...")
    try:
        quantization_config = Mxfp4Config()  # Keep quantized
        
        print("Loading quantized model (conservative memory settings)...")
        start_time = time.time()
        
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16,
            device_map="auto",  # Let transformers handle GPU/CPU split
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            max_memory={0: "14GB", "cpu": "16GB"},  # Conservative GPU limit
        )
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.1f} seconds")
        
        # Model info
        total_params = sum(p.numel() for p in model.parameters())
        print(f"   Parameters: {total_params:,} ({total_params/1e9:.2f}B)")
        print(f"   Device map: {model.hf_device_map}")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False
    
    # Step 3: Simple inference test
    print("\nStep 3: Testing inference...")
    try:
        test_prompt = "The concept of artificial intelligence"
        inputs = tokenizer(test_prompt, return_tensors="pt")
        
        # Move inputs to same device as model
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        print(f"Input prompt: '{test_prompt}'")
        print("Generating...")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=20,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"✅ Generated: {response}")
        
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        return False
    
    print(f"\n✅ GPT-OSS-20B quantized model is working!")
    print("Ready for MoE routing capture implementation.")
    
    return True

if __name__ == "__main__":
    success = test_quantized_model()
    if not success:
        print("\n❌ Test failed. Check error messages above.")
        exit(1)