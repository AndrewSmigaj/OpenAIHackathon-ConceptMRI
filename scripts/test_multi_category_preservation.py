#!/usr/bin/env python3
"""
Quick test to verify multi-category membership preservation.
"""

import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.src.schemas.capture_manifest import CaptureManifest, create_capture_manifest
import json

def test_multi_category_serialization():
    """Test that multi-category assignments serialize/deserialize correctly."""
    
    print("🧪 Testing multi-category serialization...")
    
    # Create test data with multi-category assignments
    context_categories = {
        "patient": ["medical", "pos_pure_n"],
        "doctor": ["medical"],
        "the": ["determiners", "pos_pure_det"]
    }
    
    target_categories = {
        "treatment": ["medical", "pos_pure_n"],
        "care": ["medical", "emotion"]
    }
    
    # Create manifest
    manifest = create_capture_manifest(
        capture_session_id="test_session_123",
        session_name="Multi-category Test",
        contexts=["patient", "doctor", "the"],
        targets=["treatment", "care"],
        layers_captured=[0, 1, 2],
        probe_count=6,
        context_category_assignments=context_categories,
        target_category_assignments=target_categories
    )
    
    print(f"✅ Created manifest with multi-category assignments")
    print(f"   Context categories: {manifest.context_category_assignments}")
    print(f"   Target categories: {manifest.target_category_assignments}")
    
    # Test Parquet serialization
    parquet_dict = manifest.to_parquet_dict()
    print(f"✅ Serialized to Parquet dict")
    
    # Verify JSON strings are created
    context_json = parquet_dict['context_category_assignments']
    target_json = parquet_dict['target_category_assignments']
    
    print(f"   Context JSON: {context_json}")
    print(f"   Target JSON: {target_json}")
    
    # Test deserialization
    reconstructed = CaptureManifest.from_parquet_dict(parquet_dict)
    print(f"✅ Deserialized from Parquet dict")
    
    # Verify multi-category preservation
    assert reconstructed.context_category_assignments == context_categories
    assert reconstructed.target_category_assignments == target_categories
    
    print(f"✅ Multi-category assignments preserved correctly!")
    print(f"   Reconstructed context: {reconstructed.context_category_assignments}")
    print(f"   Reconstructed target: {reconstructed.target_category_assignments}")
    
    # Verify specific multi-category words
    assert "medical" in reconstructed.context_category_assignments["patient"]
    assert "pos_pure_n" in reconstructed.context_category_assignments["patient"]
    assert len(reconstructed.context_category_assignments["patient"]) == 2
    
    print(f"✅ Multi-category word 'patient' has both categories: {reconstructed.context_category_assignments['patient']}")

if __name__ == "__main__":
    test_multi_category_serialization()
    print(f"\n🎉 All multi-category tests passed!")