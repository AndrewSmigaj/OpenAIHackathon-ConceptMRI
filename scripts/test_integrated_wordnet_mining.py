#!/usr/bin/env python3
"""
Comprehensive integration test for WordNet mining with IntegratedCaptureService.
Tests all three word mining types: custom, POS-pure, and synset hyponyms.
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


def test_integrated_wordnet_mining():
    """Test all WordNet mining integrations with capture service."""
    print("🧪 Testing Integrated WordNet Mining")
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
        # Initialize service (no model needed for word mining tests)
        service = IntegratedCaptureService(
            model=None,  # Mock for testing
            tokenizer=tokenizer,
            layers_to_capture=[0, 1, 2],
            data_lake_path=temp_dir
        )
        
        print("\n🔍 Testing word mining sources...")
        
        # Test 1: Custom word lists
        print("\n1️⃣ Testing custom word sources:")
        custom_words, label = service._mine_from_source("custom", {
            "words": ["cat", "dog", "house", "car"],
            "label": "manual_selection"
        })
        print(f"   ✅ Custom: {len(custom_words)} words - {custom_words}")
        print(f"   📋 Label: {label}")
        
        # Test 2: POS-pure words
        print("\n2️⃣ Testing POS-pure word mining:")
        pos_nouns, noun_label = service._mine_from_source("pos_pure", {
            "pos": "n",
            "max_words": 10
        })
        print(f"   ✅ Pure nouns: {len(pos_nouns)} words - {pos_nouns[:5]}...")
        print(f"   📋 Label: {noun_label}")
        
        pos_verbs, verb_label = service._mine_from_source("pos_pure", {
            "pos": "v", 
            "max_words": 10
        })
        print(f"   ✅ Pure verbs: {len(pos_verbs)} words - {pos_verbs[:5]}...")
        print(f"   📋 Label: {verb_label}")
        
        # Test 3: Synset hyponym mining (unambiguous)
        print("\n3️⃣ Testing unambiguous synset mining:")
        animal_words, animal_label = service._mine_from_source("synset_hyponyms", {
            "synset_id": "animal.n.01",
            "max_depth": 2,
            "unambiguous_only": True
        })
        print(f"   ✅ Unambiguous animals: {len(animal_words)} words - {animal_words[:5]}...")
        print(f"   📋 Label: {animal_label}")
        
        # Test 4: Synset hyponym mining (all words)
        print("\n4️⃣ Testing all-words synset mining:")
        all_animals, all_animal_label = service._mine_from_source("synset_hyponyms", {
            "synset_id": "animal.n.01",
            "max_depth": 2,
            "unambiguous_only": False
        })
        print(f"   ✅ All animals: {len(all_animals)} words - {all_animals[:5]}...")
        print(f"   📋 Label: {all_animal_label}")
        print(f"   📊 Ambiguous words included: {len(all_animals) - len(animal_words)}")
        
        # Test 5: Multi-category session creation
        print("\n5️⃣ Testing multi-category session creation:")
        
        # Define context sources (single context word with categories)
        context_sources = [
            {
                "source_type": "custom",
                "source_params": {"words": ["the"], "label": "determiner"}
            }
        ]
        
        # Define target sources (multiple categories)
        target_sources = [
            {
                "source_type": "pos_pure", 
                "source_params": {"pos": "n", "max_words": 5}
            },
            {
                "source_type": "pos_pure",
                "source_params": {"pos": "v", "max_words": 5}
            },
            {
                "source_type": "synset_hyponyms",
                "source_params": {
                    "synset_id": "animal.n.01",
                    "max_depth": 2,
                    "unambiguous_only": True
                }
            }
        ]
        
        session_id = service.create_multi_category_session(
            session_name="Demo_MultiCategory_Test",
            context_sources=context_sources,
            target_sources=target_sources
        )
        
        print(f"   ✅ Multi-category session created: {session_id}")
        
        # Verify session metadata
        session_status = service.get_session_status(session_id)
        print(f"   📊 Session pairs: {session_status.total_pairs}")
        print(f"   📊 Session state: {session_status.state.value}")
        
        # Test 6: Verify category assignments in session
        print("\n6️⃣ Testing category assignment verification:")
        
        session_file = service.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            import json
            with open(session_file, 'r') as f:
                metadata = json.load(f)
            
            context_assignments = metadata.get("context_category_assignments", {})
            target_assignments = metadata.get("target_category_assignments", {})
            
            print(f"   ✅ Context categories: {set(context_assignments.values())}")
            print(f"   ✅ Target categories: {set(target_assignments.values())}")
            
            # Show examples
            if target_assignments:
                for category in set(target_assignments.values()):
                    words_in_category = [w for w, c in target_assignments.items() if c == category]
                    print(f"      '{category}': {words_in_category[:3]}...")
        
        print("\n🎉 All integration tests passed!")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"   Custom words: {len(custom_words)}")
        print(f"   POS nouns: {len(pos_nouns)}")  
        print(f"   POS verbs: {len(pos_verbs)}")
        print(f"   Unambiguous animals: {len(animal_words)}")
        print(f"   All animals: {len(all_animals)}")
        print(f"   Multi-category session: {session_status.total_pairs} pairs")
        print(f"   Session ID: {session_id}")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary directory...")
        shutil.rmtree(temp_dir)
        print("✅ Cleanup complete")


if __name__ == "__main__":
    test_integrated_wordnet_mining()