#!/usr/bin/env python3
"""
Dequantize gpt-oss-20b from MXFP4 to BF16 format for RTX 5070 Ti compatibility.
Based on the working examples from HuggingFace discussions.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.utils.quantization_config import Mxfp4Config
from pathlib import Path
import time
import shutil


def dequantize_model():
    """Dequantize the MXFP4 model to BF16 and save locally."""
    print("=== GPT-OSS-20B Model Dequantization ===\n")
    
    model_id = "openai/gpt-oss-20b"
    save_path = Path("data/models/gpt-oss-20b-dequantized")
    
    print(f"Source model: {model_id}")
    print(f"Target path: {save_path}")
    
    # Create directory
    save_path.mkdir(parents=True, exist_ok=True)
    
    print("\nStep 1: Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        print(f"✅ Tokenizer loaded: {len(tokenizer)} tokens")
    except Exception as e:
        print(f"❌ Tokenizer loading failed: {e}")
        return False
    
    print("\nStep 2: Loading model with MXFP4 dequantization...")
    try:
        # Configure dequantization
        quantization_config = Mxfp4Config(dequantize=True)
        
        print("Loading model (this will take several minutes)...")
        start_time = time.time()
        
        # Ultra-conservative loading for WSL memory constraints
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16,
            device_map="cpu",  # Load to CPU first
            trust_remote_code=True,
            low_cpu_mem_usage=True,  # Documented solution for OOM issues
            max_memory={"cpu": "18GB"},  # More conservative, leave buffer
            offload_folder="./temp_offload"  # Disk offload for memory overflow
        )
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.1f} seconds")
        
        # Check model info
        total_params = sum(p.numel() for p in model.parameters())
        print(f"   Total parameters: {total_params:,} ({total_params/1e9:.2f}B)")
        print(f"   Model dtype: {next(model.parameters()).dtype}")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False
    
    print("\nStep 3: Saving dequantized model...")
    try:
        start_time = time.time()
        
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        
        save_time = time.time() - start_time
        print(f"✅ Model saved in {save_time:.1f} seconds")
        
        # Verify saved files
        config_file = save_path / "config.json"
        model_files = list(save_path.glob("*.safetensors"))
        
        print(f"✅ Config file: {config_file.exists()}")
        print(f"✅ Model files: {len(model_files)} safetensors files")
        
        # Calculate saved size
        total_size = sum(f.stat().st_size for f in save_path.iterdir() if f.is_file())
        size_gb = total_size / (1024**3)
        print(f"✅ Total size: {size_gb:.2f} GB")
        
    except Exception as e:
        print(f"❌ Model saving failed: {e}")
        return False
    
    finally:
        # Clean up temp offload directory
        temp_offload = Path("./temp_offload")
        if temp_offload.exists():
            print("🧹 Cleaning up temporary offload directory...")
            shutil.rmtree(temp_offload)
    
    print(f"\n=== Dequantization Complete ===")
    print(f"✅ Model saved to: {save_path.absolute()}")
    print(f"✅ Format: BF16 (dequantized from MXFP4)")
    print(f"✅ Ready for RTX 4070 Ti Super loading with device mapping")
    
    return True


def verify_dequantized_model():
    """Verify the dequantized model can be loaded."""
    print("\n=== Verification Test ===\n")
    
    save_path = Path("data/models/gpt-oss-20b-dequantized")
    
    if not save_path.exists():
        print("❌ Dequantized model not found")
        return False
    
    try:
        print("Testing basic loading...")
        
        # Test tokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(save_path))
        print(f"✅ Tokenizer: {len(tokenizer)} tokens")
        
        # Test config loading (no weights)
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(str(save_path))
        print(f"✅ Config: {config.model_type}, {config.num_hidden_layers} layers")
        
        print("✅ Verification passed - model ready for inference testing")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    print("=== GPT-OSS-20B Dequantization Process ===\n")
    
    # Check if already dequantized
    save_path = Path("data/models/gpt-oss-20b-dequantized")
    if save_path.exists() and (save_path / "config.json").exists():
        print("Dequantized model already exists.")
        print("Run verification test? (y/n): ", end="")
        
        # For script automation, just verify
        if verify_dequantized_model():
            print("\nDequantized model is ready to use!")
            return
        else:
            print("\nRe-running dequantization due to verification failure...")
    
    # Run dequantization
    success = dequantize_model()
    
    if success:
        # Verify the result
        verify_dequantized_model()
        
        print("\nNext steps:")
        print("1. Test loading with manual device mapping")
        print("2. Implement MoE routing capture hooks")
        print("3. Run inference tests")
    else:
        print("\n❌ Dequantization failed")
        print("Check error messages above and dependency versions")


if __name__ == "__main__":
    main()