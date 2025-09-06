#!/usr/bin/env python3
"""
Debug the POS extraction logic to see what's going wrong.
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

from transformers import GPT2Tokenizer


def debug_pos_logic():
    """Debug why we're not finding pure POS words."""
    print("🐛 Debugging POS Logic")
    print("=" * 30)
    
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    
    # Test a few known words
    test_words = ["cat", "dog", "house", "red", "big", "run", "walk"]
    
    print("🧪 Testing known words:")
    for word in test_words:
        synsets = wordnet.synsets(word)
        all_pos = set(s.pos() for s in synsets)
        tokens = tokenizer.encode(word, add_special_tokens=False)
        
        print(f"   '{word}': {len(synsets)} synsets, POS: {all_pos}, {len(tokens)} tokens")
        for synset in synsets[:3]:  # First 3
            print(f"      - {synset.name()} ({synset.pos()})")
    
    # Let's manually try to find some pure nouns
    print(f"\n🔍 Manually checking some nouns from WordNet:")
    
    noun_count = 0
    checked = 0
    
    for synset in list(wordnet.all_synsets(pos='n'))[:100]:  # First 100 noun synsets
        for lemma in synset.lemmas():
            word = lemma.name().lower()
            checked += 1
            
            if '_' not in word and ' ' not in word:
                all_synsets = wordnet.synsets(word)
                all_pos = set(s.pos() for s in all_synsets)
                
                if len(all_pos) == 1 and 'n' in all_pos:
                    tokens = tokenizer.encode(word, add_special_tokens=False)
                    print(f"   PURE NOUN FOUND: '{word}' - {len(tokens)} tokens, POS: {all_pos}")
                    noun_count += 1
                    
                    if noun_count >= 5:  # Just get 5 examples
                        break
        
        if noun_count >= 5:
            break
    
    print(f"\n📊 Checked {checked} words, found {noun_count} pure nouns")
    
    # Check if the issue is with the logic
    print(f"\n🔧 Testing the problematic line:")
    
    # Check what happens with spaces
    test_word = "house"
    has_space = ' ' not in test_word  # This should be True (no space)
    has_underscore = '_' not in test_word  # This should be True (no underscore)
    
    print(f"   Word: '{test_word}'")
    print(f"   Has no space: {has_space}")
    print(f"   Has no underscore: {has_underscore}")
    print(f"   Should pass filter: {has_space and has_underscore}")


if __name__ == "__main__":
    debug_pos_logic()