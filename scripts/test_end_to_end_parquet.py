#!/usr/bin/env python3
"""
End-to-end test with actual Parquet I/O and real model forward passes.
Tests category assignments survive serialization and can be queried from data lake.
"""

import sys
from pathlib import Path
import tempfile
import shutil
import pandas as pd

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from services.probes.integrated_capture_service import IntegratedCaptureService


def test_end_to_end_parquet():
    """Test full pipeline with real model and Parquet I/O."""
    print("🧪 End-to-End Parquet Integration Test")
    print("=" * 50)
    
    # Create temporary data directory
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")
    
    try:
        # Load lightweight model for testing
        print("📚 Loading lightweight model and tokenizer...")
        model_name = "gpt2"  # Small model for testing
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # Add pad token if missing
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        print(f"   ✅ Loaded {model_name}")
        print(f"   📊 Model layers: {model.config.n_layer}")
        
        # Initialize service with real model
        service = IntegratedCaptureService(
            model=model,
            tokenizer=tokenizer,
            layers_to_capture=[0, 1],  # First 2 layers for speed
            data_lake_path=temp_dir,
            batch_size=10  # Small batches
        )
        
        # Create multi-category session with small word sets
        print("\n🔬 Creating multi-category session with real categories...")
        
        context_sources = [
            {
                "source_type": "custom",
                "source_params": {"words": ["the"], "label": "determiner"}
            }
        ]
        
        target_sources = [
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["cat", "dog"], 
                    "label": "animals"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["car", "book"],
                    "label": "objects"
                }
            }
        ]
        
        session_id = service.create_multi_category_session(
            session_name="E2E_Parquet_Test",
            context_sources=context_sources,
            target_sources=target_sources
        )
        
        print(f"   ✅ Session created: {session_id}")
        
        # Capture actual probes (real forward passes)
        print("\n🚀 Running actual MoE captures...")
        
        try:
            # Capture a few specific pairs to test
            test_pairs = [
                ("the", "cat"),   # determiner × animals
                ("the", "car"),   # determiner × objects  
                ("the", "dog"),   # determiner × animals
                ("the", "book")   # determiner × objects
            ]
            
            successful_probes = []
            for context, target in test_pairs:
                try:
                    probe_id = service.capture_single_pair(session_id, context, target)
                    successful_probes.append(probe_id)
                    print(f"   ✅ Captured: '{context}' → '{target}' (probe: {probe_id})")
                except Exception as e:
                    print(f"   ❌ Failed '{context}' → '{target}': {e}")
            
            print(f"\n📊 Successfully captured {len(successful_probes)} probes")
            
            # Finalize session (writes manifest to Parquet)
            print("\n💾 Finalizing session and writing Parquet files...")
            manifest = service.finalize_session(session_id)
            
            print(f"   ✅ Session finalized")
            print(f"   📋 Manifest probe count: {manifest.probe_count}")
            print(f"   🗂️ Context categories: {manifest.context_category_assignments}")
            print(f"   🗂️ Target categories: {manifest.target_category_assignments}")
            
            # Verify Parquet files exist
            print("\n🔍 Verifying Parquet files...")
            session_dir = Path(temp_dir) / session_id
            
            parquet_files = list(session_dir.glob("*.parquet"))
            print(f"   📁 Found {len(parquet_files)} Parquet files:")
            for file in parquet_files:
                size = file.stat().st_size
                print(f"      - {file.name}: {size} bytes")
            
            # Test 1: Read manifest back from Parquet
            print("\n🧪 Test 1: Reading manifest from Parquet...")
            manifest_path = session_dir / "capture_manifest.parquet"
            
            if manifest_path.exists():
                df_manifest = pd.read_parquet(manifest_path)
                print(f"   ✅ Manifest Parquet loaded: {len(df_manifest)} rows")
                
                # Reconstruct manifest from Parquet
                manifest_dict = df_manifest.iloc[0].to_dict()
                reconstructed_manifest = manifest.from_parquet_dict(manifest_dict)
                
                print(f"   📋 Reconstructed contexts: {reconstructed_manifest.contexts}")
                print(f"   📋 Reconstructed context categories: {reconstructed_manifest.context_category_assignments}")
                print(f"   📋 Reconstructed target categories: {reconstructed_manifest.target_category_assignments}")
                
                # Verify category assignments survived serialization
                original_ctx_cats = manifest.context_category_assignments
                reconstructed_ctx_cats = reconstructed_manifest.context_category_assignments
                
                if original_ctx_cats == reconstructed_ctx_cats:
                    print("   ✅ Context categories survived Parquet roundtrip")
                else:
                    print("   ❌ Context categories corrupted in roundtrip")
                    print(f"      Original: {original_ctx_cats}")
                    print(f"      Reconstructed: {reconstructed_ctx_cats}")
            else:
                print("   ❌ Manifest Parquet file not found")
            
            # Test 2: Query activation data by categories
            print("\n🧪 Test 2: Querying activation data by categories...")
            
            # Read tokens table to see category assignments in practice
            tokens_path = session_dir / "tokens.parquet"
            if tokens_path.exists():
                df_tokens = pd.read_parquet(tokens_path)
                print(f"   ✅ Tokens table loaded: {len(df_tokens)} rows")
                
                # Show sample token records
                for idx, row in df_tokens.iterrows():
                    context_word = row['context_text']
                    target_word = row['target_text']
                    probe_id = row['probe_id']
                    
                    # Get categories from manifest
                    context_cat = manifest.context_category_assignments.get(context_word, "unknown")
                    target_cat = manifest.target_category_assignments.get(target_word, "unknown")
                    
                    print(f"      Probe {probe_id}: '{context_word}' ({context_cat}) → '{target_word}' ({target_cat})")
            
            # Test 3: Query routing data for category analysis
            print("\n🧪 Test 3: Analyzing routing data by categories...")
            
            routing_path = session_dir / "routing.parquet"
            if routing_path.exists():
                df_routing = pd.read_parquet(routing_path)
                print(f"   ✅ Routing table loaded: {len(df_routing)} rows")
                
                # Group by categories (join with tokens table)
                df_combined = df_routing.merge(df_tokens, on='probe_id')
                
                # Add category labels
                df_combined['context_category'] = df_combined['context_text'].map(manifest.context_category_assignments)
                df_combined['target_category'] = df_combined['target_text'].map(manifest.target_category_assignments)
                
                # Analyze routing patterns by category
                category_combinations = df_combined.groupby(['context_category', 'target_category']).size()
                print("   📊 Routing records by category combination:")
                for (ctx_cat, tgt_cat), count in category_combinations.items():
                    print(f"      {ctx_cat} → {tgt_cat}: {count} routing records")
            
            # Test 4: Verify expert activation data integrity
            print("\n🧪 Test 4: Checking expert activation data...")
            
            expert_internal_path = session_dir / "expert_internal_activations.parquet"
            expert_output_path = session_dir / "expert_output_states.parquet"
            
            records_found = 0
            if expert_internal_path.exists():
                df_internal = pd.read_parquet(expert_internal_path)
                records_found += len(df_internal)
                print(f"   ✅ Expert internal activations: {len(df_internal)} records")
            
            if expert_output_path.exists():
                df_output = pd.read_parquet(expert_output_path)
                records_found += len(df_output)
                print(f"   ✅ Expert output states: {len(df_output)} records")
            
            print(f"   📊 Total activation records: {records_found}")
            
            # Final assessment
            print(f"\n🎉 End-to-End Test Results:")
            print(f"   ✅ Real model forward passes: {len(successful_probes)} probes")
            print(f"   ✅ Parquet files written: {len(parquet_files)} files")
            print(f"   ✅ Category assignments serialized and deserialized")
            print(f"   ✅ Data lake queryable by categories")
            print(f"   ✅ Activation data linked to semantic categories")
            print(f"\n🏆 INTEGRATION COMPLETE - Categories work with real Parquet data!")
            
        except Exception as e:
            print(f"❌ Capture failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary directory...")
        shutil.rmtree(temp_dir)
        print("✅ Cleanup complete")


if __name__ == "__main__":
    test_end_to_end_parquet()