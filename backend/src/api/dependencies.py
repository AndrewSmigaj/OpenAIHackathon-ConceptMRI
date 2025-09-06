#!/usr/bin/env python3
"""
Simple dependency injection for shared services.
"""

import sys
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add backend to path  
backend_src = Path(__file__).parent.parent  # backend/src
project_root = backend_src.parent.parent     # project root
sys.path.insert(0, str(backend_src))

from services.probes.integrated_capture_service import IntegratedCaptureService


# Global service instance (simple approach)
_capture_service = None


def get_capture_service() -> IntegratedCaptureService:
    """Get or initialize the capture service."""
    global _capture_service
    
    if _capture_service is None:
        print("🚀 Initializing capture service...")
        
        try:
            # Use paths relative to project root (project_root is already backend/src/..)
            model_path = project_root / "data" / "models" / "gpt-oss-20b"
            data_lake_path = project_root / "data" / "lake"
            
            # Check if model exists
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found at: {model_path}")
            
            print(f"📚 Loading model from: {model_path}")
            tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            
            # Initialize service
            _capture_service = IntegratedCaptureService(
                model=model,
                tokenizer=tokenizer,
                layers_to_capture=[0, 1, 2],
                data_lake_path=str(data_lake_path)
            )
            
            print("✅ Capture service ready")
            
        except Exception as e:
            print(f"❌ Failed to initialize capture service: {e}")
            raise RuntimeError(f"Capture service initialization failed: {e}")
    
    return _capture_service