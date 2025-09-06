#!/usr/bin/env python3
"""
Test WordNet mining utility with real tokenizer.
Validates unambiguous word filtering for demo categories.
"""

import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from transformers import AutoTokenizer
from utils.wordnet_mining import WordNetMiner, mine_category_words


def test_wordnet_mining():
    """Test WordNet mining with GPT-OSS-20B tokenizer."""
    print("🧪 Testing WordNet Mining Utility")
    print("=" * 40)
    
    # Load tokenizer
    print("📚 Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained("data/models/gpt-oss-20b")
        print("✅ Tokenizer loaded")
    except Exception as e:
        print(f"❌ Failed to load tokenizer: {e}")
        print("Using a fallback tokenizer for testing...")
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    
    # Test categories
    test_synsets = [
        "animal.n.01",        # Animals
        "person.n.01",        # People  
        "artifact.n.01",      # Objects
        "color.n.01",         # Colors
    ]
    
    miner = WordNetMiner(tokenizer)
    
    for synset_id in test_synsets:
        print(f"\n🔍 Testing synset: {synset_id}")
        
        try:
            words = miner.mine_unambiguous_words(synset_id)
            label = miner.get_synset_label(synset_id)
            
            print(f"📊 Found {len(words)} unambiguous words")
            print(f"🏷️ Label: {label}")
            
            if words:
                print(f"📝 Sample words: {words[:10]}...")  # First 10
                
                # Test tokenization
                print("🧪 Testing tokenization:")
                for word in words[:3]:  # Test first 3
                    tokens = tokenizer.encode(word, add_special_tokens=False)
                    print(f"   '{word}' → {tokens} (length: {len(tokens)})")
            else:
                print("⚠️ No words found!")
                
        except Exception as e:
            print(f"❌ Error testing {synset_id}: {e}")
    
    # Test convenience function
    print(f"\n🛠️ Testing convenience function...")
    try:
        words, label = mine_category_words("animal.n.01", tokenizer)
        print(f"✅ Convenience function works: {len(words)} words, label '{label}'")
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
    
    print(f"\n✅ WordNet mining test complete!")


if __name__ == "__main__":
    test_wordnet_mining()