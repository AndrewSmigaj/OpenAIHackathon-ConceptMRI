#!/usr/bin/env python3
"""
Simple dependency injection for shared services.
"""

import sys
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add backend to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.probes.integrated_capture_service import IntegratedCaptureService


# Global service instance (simple approach)
_capture_service = None


def get_capture_service() -> IntegratedCaptureService:
    """Get or initialize the capture service."""
    global _capture_service
    
    if _capture_service is None:
        print("🚀 Initializing capture service...")
        
        # Load model
        model_path = "data/models/gpt-oss-20b"
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Initialize service
        _capture_service = IntegratedCaptureService(
            model=model,
            tokenizer=tokenizer,
            layers_to_capture=[0, 1, 2],
            data_lake_path="data/lake"
        )
        
        print("✅ Capture service ready")
    
    return _capture_service