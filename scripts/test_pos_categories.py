#!/usr/bin/env python3
"""
Test general POS categories to find better demo words.
Look for broad noun/verb categories that should have more unambiguous words.
"""

import sys
from pathlib import Path
import nltk
from nltk.corpus import wordnet

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from transformers import AutoTokenizer
from utils.wordnet_mining import WordNetMiner


def test_pos_categories():
    """Test general POS-based categories."""
    print("📝 Testing General POS Categories")
    print("=" * 40)
    
    # Load tokenizer
    print("📚 Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained("data/models/gpt-oss-20b")
    except:
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    
    miner = WordNetMiner(tokenizer)
    
    # Test broad POS-based synsets
    pos_synsets = [
        # Broad noun categories
        ("entity.n.01", "All nouns (entities)"),
        ("physical_entity.n.01", "Physical things"),
        ("abstraction.n.06", "Abstract concepts"),
        ("object.n.01", "Objects"),
        ("substance.n.01", "Substances"),
        
        # Broad verb categories  
        ("verb.n.01", "All verbs"),
        ("change.v.01", "Change verbs"),
        ("move.v.01", "Movement verbs"),
        ("act.v.01", "Action verbs"),
        ("think.v.01", "Mental verbs"),
        
        # Try some we know exist
        ("person.n.01", "People (confirmed good)"),
        ("artifact.n.01", "Artifacts (confirmed good)")
    ]
    
    print(f"\n🎯 Testing with depth 3 for more words...")
    
    for synset_id, description in pos_synsets:
        print(f"\n🔍 {description} ({synset_id})")
        
        try:
            # Test with depth 3 to get more words
            words = miner.mine_unambiguous_words(synset_id, max_depth=3)
            count = len(words)
            
            if count > 0:
                print(f"   ✅ {count} words: {words[:10]}...")
                
                # Check tokenization of a few
                for word in words[:3]:
                    tokens = tokenizer.encode(word, add_special_tokens=False)
                    synsets = wordnet.synsets(word)
                    print(f"      '{word}' → {len(tokens)} token, {len(synsets)} synset(s)")
            else:
                print(f"   ❌ No unambiguous words found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Also test: do we have ANY simple words that are unambiguous?
    print(f"\n🧪 Testing common words for unambiguity:")
    common_words = [
        "cat", "dog", "house", "car", "tree", "book", "water", "fire",
        "run", "walk", "eat", "sleep", "think", "see", "go", "come",
        "red", "blue", "big", "small", "good", "bad", "new", "old"
    ]
    
    unambiguous_found = []
    for word in common_words:
        synsets = wordnet.synsets(word)
        tokens = tokenizer.encode(word, add_special_tokens=False)
        
        if len(synsets) == 1 and len(tokens) == 1:
            unambiguous_found.append((word, synsets[0].name(), synsets[0].pos()))
    
    print(f"\n🎉 Found {len(unambiguous_found)} unambiguous common words:")
    for word, synset, pos in unambiguous_found:
        print(f"   {word} ({synset}) - {pos}")
    
    if not unambiguous_found:
        print("   😞 No common words are globally unambiguous")
        print("   → Consider relaxing to POS-specific ambiguity or manual curation")


if __name__ == "__main__":
    test_pos_categories()