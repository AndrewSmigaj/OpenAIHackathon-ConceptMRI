#!/usr/bin/env python3
"""
Download and setup OpenAI gpt-oss-20b MoE model.
Uses MXFP4 quantization to fit in 16GB GPU memory.
"""

import os
from pathlib import Path
from huggingface_hub import snapshot_download
import torch


def setup_model_directory():
    """Create model directory structure."""
    model_dir = Path("data/models/gpt-oss-20b")
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def download_model(model_dir: Path):
    """Download gpt-oss-20b from Hugging Face."""
    print("Downloading gpt-oss-20b from Hugging Face...")
    print("This will take several minutes as the model is ~20GB...")
    
    model_name = "openai/gpt-oss-20b"
    
    try:
        # Download to our model directory
        snapshot_download(
            repo_id=model_name,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,  # Copy files instead of symlinks
            resume_download=True,  # Resume if interrupted
        )
        print(f"✅ Model downloaded to {model_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def verify_model_files(model_dir: Path):
    """Check that essential model files exist."""
    required_files = [
        "config.json",
        "tokenizer.json", 
        "tokenizer_config.json"
    ]
    
    print("\nVerifying model files...")
    missing_files = []
    
    for filename in required_files:
        filepath = model_dir / filename
        if filepath.exists():
            print(f"✅ Found {filename}")
        else:
            print(f"❌ Missing {filename}")
            missing_files.append(filename)
    
    # Check for model weight files (various formats)
    weight_patterns = ["*.bin", "*.safetensors", "*.pth"]
    weight_files = []
    for pattern in weight_patterns:
        weight_files.extend(model_dir.glob(pattern))
    
    if weight_files:
        print(f"✅ Found {len(weight_files)} weight files")
        for wf in weight_files[:3]:  # Show first 3
            print(f"  - {wf.name}")
        if len(weight_files) > 3:
            print(f"  ... and {len(weight_files) - 3} more")
    else:
        print("❌ No weight files found")
        missing_files.append("model weights")
    
    return len(missing_files) == 0


def test_model_loading(model_dir: Path):
    """Test basic model loading with transformers."""
    print("\nTesting model loading...")
    
    try:
        from transformers import AutoConfig, AutoTokenizer
        
        # Load config
        config = AutoConfig.from_pretrained(str(model_dir))
        print(f"✅ Config loaded: {config.model_type}")
        print(f"   Architecture: {config.architectures[0] if config.architectures else 'Unknown'}")
        print(f"   Vocab size: {config.vocab_size}")
        print(f"   Layers: {getattr(config, 'num_hidden_layers', 'Unknown')}")
        
        # Check for MoE specific config
        if hasattr(config, 'num_experts'):
            print(f"   MoE experts: {config.num_experts}")
        if hasattr(config, 'num_experts_per_token'): 
            print(f"   Experts per token: {config.num_experts_per_token}")
        if hasattr(config, 'expert_capacity'):
            print(f"   Expert capacity: {config.expert_capacity}")
            
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        print(f"✅ Tokenizer loaded: {len(tokenizer)} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False


def main():
    print("=== OpenAI gpt-oss-20b Setup ===\n")
    
    # Check GPU memory
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU Memory: {gpu_memory:.1f} GB")
        if gpu_memory < 15:
            print("⚠️  Model may not fit in available GPU memory")
    else:
        print("❌ No GPU available - model will be very slow")
        return
    
    # Setup directory
    model_dir = setup_model_directory()
    print(f"Model directory: {model_dir}")
    
    # Check if already downloaded
    if (model_dir / "config.json").exists():
        print("Model appears to already exist. Skipping download...")
    else:
        # Download model
        success = download_model(model_dir)
        if not success:
            return
    
    # Verify files
    if not verify_model_files(model_dir):
        print("\n❌ Model files incomplete")
        return
    
    # Test loading
    if not test_model_loading(model_dir):
        print("\n❌ Model loading failed")
        return
    
    print("\n✅ gpt-oss-20b setup complete!")
    print(f"Model path: {model_dir.absolute()}")
    
    # Next steps
    print("\nNext steps:")
    print("1. Run test_inference.py to verify model works")
    print("2. Run inspect_moe_structure.py to understand MoE layers")


if __name__ == "__main__":
    main()