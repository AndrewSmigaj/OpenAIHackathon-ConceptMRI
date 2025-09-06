#!/usr/bin/env python3
"""
Test multi-category probe with mixed word sources for demo effectiveness.
This test validates the key demo scenarios for the hackathon.
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from transformers import AutoTokenizer
from services.probes.integrated_capture_service import IntegratedCaptureService


def test_multi_category_probe():
    """Test multi-category probe scenarios for hackathon demos."""
    print("🎯 Testing Multi-Category Probe Scenarios")
    print("=" * 50)
    
    # Load tokenizer
    print("📚 Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained("data/models/gpt-oss-20b")
    except:
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        print("  ⚠️ Using GPT2 tokenizer as fallback")
    
    # Create temporary data directory
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")
    
    try:
        # Initialize service
        service = IntegratedCaptureService(
            model=None,  # Mock for testing
            tokenizer=tokenizer,
            layers_to_capture=[0, 1, 2],  # Early window
            data_lake_path=temp_dir
        )
        
        # Demo Scenario 1: POS Contrast Analysis (noun vs verb after "the")
        print("\n🔬 Demo Scenario 1: POS Contrast Analysis")
        print("   Context: 'the' (determiner)")
        print("   Targets: Pure nouns vs Pure verbs")
        
        pos_context_sources = [
            {
                "source_type": "custom",
                "source_params": {"words": ["the"], "label": "determiner"}
            }
        ]
        
        pos_target_sources = [
            {
                "source_type": "pos_pure",
                "source_params": {"pos": "n", "max_words": 15}
            },
            {
                "source_type": "pos_pure", 
                "source_params": {"pos": "v", "max_words": 15}
            }
        ]
        
        pos_session_id = service.create_multi_category_session(
            session_name="POS_Contrast_Nouns_vs_Verbs",
            context_sources=pos_context_sources,
            target_sources=pos_target_sources
        )
        
        pos_status = service.get_session_status(pos_session_id)
        print(f"   ✅ POS session: {pos_status.total_pairs} pairs")
        
        # Demo Scenario 2: Semantic Category Analysis (animals vs artifacts)
        print("\n🔬 Demo Scenario 2: Semantic Category Analysis")
        print("   Context: 'the' (determiner)")
        print("   Targets: Animals vs Artifacts")
        
        semantic_target_sources = [
            {
                "source_type": "synset_hyponyms",
                "source_params": {
                    "synset_id": "animal.n.01",
                    "max_depth": 3,
                    "unambiguous_only": False  # Include ambiguous for more words
                }
            },
            {
                "source_type": "synset_hyponyms", 
                "source_params": {
                    "synset_id": "artifact.n.01",
                    "max_depth": 3,
                    "unambiguous_only": False
                }
            }
        ]
        
        semantic_session_id = service.create_multi_category_session(
            session_name="Semantic_Animals_vs_Artifacts",
            context_sources=pos_context_sources,  # Reuse "the"
            target_sources=semantic_target_sources
        )
        
        semantic_status = service.get_session_status(semantic_session_id)
        print(f"   ✅ Semantic session: {semantic_status.total_pairs} pairs")
        
        # Demo Scenario 3: Mixed Multi-Category (Custom + POS + Semantic)
        print("\n🔬 Demo Scenario 3: Mixed Multi-Category Analysis")
        print("   Multiple contexts: Custom selection")
        print("   Multiple targets: Custom + POS-pure + Semantic categories")
        
        mixed_context_sources = [
            {
                "source_type": "custom",
                "source_params": {"words": ["the", "a"], "label": "determiners"}
            }
        ]
        
        mixed_target_sources = [
            # Custom high-frequency words
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["cat", "dog", "car", "house", "book"],
                    "label": "common_nouns"
                }
            },
            # POS-pure verbs
            {
                "source_type": "pos_pure",
                "source_params": {"pos": "v", "max_words": 8}
            },
            # Semantic category: animals (unambiguous only)
            {
                "source_type": "synset_hyponyms",
                "source_params": {
                    "synset_id": "animal.n.01", 
                    "max_depth": 2,
                    "unambiguous_only": True
                }
            }
        ]
        
        mixed_session_id = service.create_multi_category_session(
            session_name="Mixed_MultiCategory_Demo",
            context_sources=mixed_context_sources,
            target_sources=mixed_target_sources
        )
        
        mixed_status = service.get_session_status(mixed_session_id)
        print(f"   ✅ Mixed session: {mixed_status.total_pairs} pairs")
        
        # Analyze category distributions
        print("\n📊 Category Distribution Analysis:")
        
        for session_name, session_id in [
            ("POS Contrast", pos_session_id),
            ("Semantic", semantic_session_id), 
            ("Mixed", mixed_session_id)
        ]:
            session_file = service.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                import json
                with open(session_file, 'r') as f:
                    metadata = json.load(f)
                
                context_assignments = metadata.get("context_category_assignments", {})
                target_assignments = metadata.get("target_category_assignments", {})
                
                # Count words per category
                context_counts = {}
                for word, category in context_assignments.items():
                    context_counts[category] = context_counts.get(category, 0) + 1
                
                target_counts = {}
                for word, category in target_assignments.items():
                    target_counts[category] = target_counts.get(category, 0) + 1
                
                print(f"\n   📋 {session_name} Session ({session_id}):")
                print(f"      Context categories: {dict(context_counts)}")
                print(f"      Target categories: {dict(target_counts)}")
                
                # Calculate total combinations per category pair
                total_category_pairs = 0
                for ctx_cat, ctx_count in context_counts.items():
                    for tgt_cat, tgt_count in target_counts.items():
                        pair_count = ctx_count * tgt_count
                        total_category_pairs += pair_count
                        print(f"      {ctx_cat} × {tgt_cat}: {pair_count} pairs")
        
        # Demo effectiveness assessment
        print(f"\n🎬 Demo Effectiveness Assessment:")
        print(f"   ✅ POS contrast available: {pos_status.total_pairs} pairs")
        print(f"   ✅ Semantic contrast available: {semantic_status.total_pairs} pairs")
        print(f"   ✅ Mixed categories available: {mixed_status.total_pairs} pairs")
        
        # Check for sufficient word counts for demos
        effective_demos = 0
        if pos_status.total_pairs >= 20:
            print("   🎯 POS demo: EFFECTIVE (≥20 pairs)")
            effective_demos += 1
        else:
            print(f"   ⚠️ POS demo: Limited ({pos_status.total_pairs} pairs)")
            
        if semantic_status.total_pairs >= 20:
            print("   🎯 Semantic demo: EFFECTIVE (≥20 pairs)")
            effective_demos += 1
        else:
            print(f"   ⚠️ Semantic demo: Limited ({semantic_status.total_pairs} pairs)")
            
        if mixed_status.total_pairs >= 30:
            print("   🎯 Mixed demo: EFFECTIVE (≥30 pairs)")
            effective_demos += 1
        else:
            print(f"   ⚠️ Mixed demo: Limited ({mixed_status.total_pairs} pairs)")
        
        print(f"\n🏆 Demo Readiness: {effective_demos}/3 scenarios are demo-ready")
        
        if effective_demos >= 2:
            print("   ✅ READY for hackathon demos!")
        else:
            print("   ⚠️ Need more word mining or depth adjustment")
        
    except Exception as e:
        print(f"❌ Multi-category test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary directory...")
        shutil.rmtree(temp_dir)
        print("✅ Cleanup complete")


if __name__ == "__main__":
    test_multi_category_probe()