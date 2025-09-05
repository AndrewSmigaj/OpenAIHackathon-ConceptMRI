#!/usr/bin/env python3
"""
Test loading the dequantized gpt-oss-20b with proper device mapping for RTX 5070 Ti.
Based on the working patterns from HuggingFace discussions.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from pathlib import Path
import time


class RTXModelLoader:
    """Optimized model loader for RTX 5070 Ti with manual device mapping."""
    
    def __init__(self, model_path: str, max_gpu_layers: int = 20):
        self.model_path = Path(model_path)
        self.max_gpu_layers = max_gpu_layers
        self.model = None
        self.tokenizer = None
        
    def create_device_map(self, num_layers: int = 24):
        """Create manual device mapping for RTX 5070 Ti (16GB)."""
        print(f"Creating device map: {self.max_gpu_layers}/{num_layers} layers on GPU")
        
        device_map = {
            "model.embed_tokens": 0,
            "model.norm": "cpu",  # Keep final norm on CPU
            "lm_head": "cpu"      # Keep output head on CPU
        }
        
        # Put first N layers on GPU, rest on CPU
        for i in range(num_layers):
            if i < self.max_gpu_layers:
                device_map[f"model.layers.{i}"] = 0
            else:
                device_map[f"model.layers.{i}"] = "cpu"
        
        return device_map
    
    def load_model(self, use_quantization: bool = True):
        """Load model with optimized settings for RTX 5070 Ti."""
        print("=== Loading Dequantized GPT-OSS-20B ===\n")
        
        if not self.model_path.exists():
            print(f"❌ Model not found at: {self.model_path}")
            print("Run dequantize_model.py first!")
            return False
        
        print("Step 1: Loading tokenizer...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            print(f"✅ Tokenizer loaded: {len(self.tokenizer)} tokens")
        except Exception as e:
            print(f"❌ Tokenizer loading failed: {e}")
            return False
        
        print(f"\nStep 2: Loading model...")
        print(f"  Path: {self.model_path}")
        print(f"  GPU layers: {self.max_gpu_layers}/24")
        print(f"  Quantization: {'4-bit' if use_quantization else 'BF16'}")
        
        try:
            # Create device mapping
            device_map = self.create_device_map()
            
            # Configure quantization if requested
            quantization_config = None
            if use_quantization:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    llm_int8_enable_fp32_cpu_offload=True
                )
            
            start_time = time.time()
            
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                quantization_config=quantization_config,
                device_map=device_map,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded in {load_time:.1f} seconds")
            
            # Print model info
            total_params = sum(p.numel() for p in self.model.parameters())
            print(f"   Total parameters: {total_params:,} ({total_params/1e9:.2f}B)")
            
            # Check GPU memory usage
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated(0) / (1024**3)
                print(f"   GPU memory used: {gpu_memory:.2f} GB")
            
            return True
            
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False
    
    def test_inference(self, test_prompt: str = "The cat sat on"):
        """Test basic inference."""
        if self.model is None or self.tokenizer is None:
            print("❌ Model not loaded")
            return False
        
        print(f"\n=== Testing Inference ===")
        print(f"Prompt: '{test_prompt}'")
        
        try:
            self.model.eval()
            
            # Tokenize input
            inputs = self.tokenizer(test_prompt, return_tensors="pt")
            
            # Move to appropriate device
            if torch.cuda.is_available():
                # Only move inputs to GPU if embed_tokens is on GPU
                inputs = {k: v.to(0) for k, v in inputs.items()}
            
            start_time = time.time()
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=10,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            inference_time = time.time() - start_time
            
            # Decode output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            continuation = generated_text[len(test_prompt):].strip()
            
            print(f"✅ Output: '{continuation}'")
            print(f"✅ Time: {inference_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            print(f"❌ Inference failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_different_configurations():
    """Test different loading configurations."""
    model_path = "data/models/gpt-oss-20b-dequantized"
    
    configurations = [
        {"max_gpu_layers": 15, "use_quantization": True, "name": "Conservative (15 GPU layers, 4-bit)"},
        {"max_gpu_layers": 20, "use_quantization": True, "name": "Aggressive (20 GPU layers, 4-bit)"},
        {"max_gpu_layers": 10, "use_quantization": False, "name": "BF16 (10 GPU layers, no quantization)"}
    ]
    
    for i, config in enumerate(configurations):
        print(f"\n{'='*60}")
        print(f"Configuration {i+1}: {config['name']}")
        print(f"{'='*60}")
        
        loader = RTXModelLoader(model_path, config["max_gpu_layers"])
        
        if loader.load_model(config["use_quantization"]):
            # Test inference
            success = loader.test_inference("The cat sat on")
            
            if success:
                print(f"✅ Configuration {i+1} works!")
                return loader  # Return the working configuration
            else:
                print(f"❌ Configuration {i+1} failed inference")
        else:
            print(f"❌ Configuration {i+1} failed loading")
        
        # Clean up
        if loader.model:
            del loader.model
        if loader.tokenizer:
            del loader.tokenizer
        
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    return None


def main():
    print("=== GPT-OSS-20B Fixed Loading Test ===\n")
    
    # Check if dequantized model exists
    model_path = Path("data/models/gpt-oss-20b-dequantized")
    if not model_path.exists():
        print("❌ Dequantized model not found!")
        print("Run: python3 scripts/dequantize_model.py")
        return
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        print("❌ No GPU available")
        return
    
    # Test different configurations
    print("\nTesting different loading configurations...\n")
    working_loader = test_different_configurations()
    
    if working_loader:
        print("\n" + "="*60)
        print("SUCCESS: Found working configuration!")
        print("="*60)
        print("\nNext steps:")
        print("1. Implement MoE routing capture hooks")
        print("2. Test with context/target word pairs") 
        print("3. Build probe capture service")
    else:
        print("\n" + "="*60)
        print("FAILED: No working configuration found")
        print("="*60)
        print("\nTroubleshooting:")
        print("1. Check GPU memory usage")
        print("2. Try reducing max_gpu_layers further")
        print("3. Verify model dequantization completed successfully")


if __name__ == "__main__":
    main()