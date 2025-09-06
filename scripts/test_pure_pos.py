#!/usr/bin/env python3
"""
Test getting words that are pure POS (only noun, only adjective, etc.)
This should give us plenty of demo words for POS-based routing analysis.
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


def get_words_by_pos(tokenizer, pos: str, max_words: int = 50) -> list:
    """Get words that are ONLY this POS (noun, verb, adj, etc.)"""
    print(f"🔍 Finding words that are ONLY {pos}...")
    
    words_found = []
    checked_words = set()
    
    # Go through WordNet synsets for this POS
    for synset in list(wordnet.all_synsets(pos=pos))[:1000]:  # Limit for speed
        for lemma in synset.lemmas():
            word = lemma.name().lower()
            
            # Skip if already checked or has underscores/spaces
            if word in checked_words or '_' in word or ' ' in word:
                continue
            
            checked_words.add(word)
            
            # Check: does this word ONLY appear as this POS?
            all_synsets = wordnet.synsets(word)
            all_pos = set(s.pos() for s in all_synsets)
            
            if len(all_pos) == 1 and pos in all_pos:  # Only this POS
                # Check single token
                try:
                    tokens = tokenizer.encode(word, add_special_tokens=False)
                    if len(tokens) == 1:
                        words_found.append(word)
                        
                        if len(words_found) >= max_words:
                            break
                except Exception:
                    continue
        
        if len(words_found) >= max_words:
            break
    
    return sorted(set(words_found))


def test_pure_pos():
    """Test pure POS word extraction."""
    print("🧪 Testing Pure POS Word Extraction")
    print("=" * 50)
    
    # Load tokenizer
    print("📚 Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained("data/models/gpt-oss-20b")
    except:
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    
    # Test different POS categories
    pos_categories = [
        ('n', 'Nouns'),
        ('v', 'Verbs'), 
        ('a', 'Adjectives'),
        ('r', 'Adverbs'),
        ('s', 'Adjective satellites')
    ]
    
    results = {}
    
    for pos, description in pos_categories:
        print(f"\n📝 Testing {description} (pos='{pos}'):")
        
        try:
            words = get_words_by_pos(tokenizer, pos, max_words=30)
            count = len(words)
            results[description] = words
            
            print(f"   ✅ Found {count} pure {description.lower()}")
            if words:
                print(f"   📋 First 10: {words[:10]}")
                print(f"   📋 Sample: {words[10:15] if len(words) > 10 else words[-5:]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[description] = []
    
    # Summary
    print(f"\n🎯 SUMMARY - Pure POS Words Found:")
    print("=" * 50)
    for category, words in results.items():
        if words:
            print(f"{category:15}: {len(words):2d} words - {words[:5]}...")
        else:
            print(f"{category:15}:  0 words - None found")
    
    # Test a few for validation
    print(f"\n🧪 Validation - Checking POS purity:")
    
    if results.get("Nouns"):
        test_word = results["Nouns"][0]
        synsets = wordnet.synsets(test_word)
        pos_set = set(s.pos() for s in synsets)
        print(f"   '{test_word}' (noun): {len(synsets)} synsets, POS: {pos_set}")
    
    if results.get("Adjectives"):
        test_word = results["Adjectives"][0] 
        synsets = wordnet.synsets(test_word)
        pos_set = set(s.pos() for s in synsets)
        print(f"   '{test_word}' (adj): {len(synsets)} synsets, POS: {pos_set}")
    
    # Demo potential
    noun_count = len(results.get("Nouns", []))
    adj_count = len(results.get("Adjectives", []))
    verb_count = len(results.get("Verbs", []))
    
    print(f"\n🚀 Demo Potential:")
    if noun_count >= 10 and adj_count >= 10:
        print(f"   ✅ 'the' + noun vs 'the' + adjective ({noun_count} vs {adj_count} words)")
    if noun_count >= 10 and verb_count >= 10:
        print(f"   ✅ 'the' + noun vs 'the' + verb ({noun_count} vs {verb_count} words)")
    if adj_count >= 10 and verb_count >= 10:
        print(f"   ✅ Pure adjective vs pure verb routing comparison")
    
    print(f"\n✅ Pure POS test complete!")


if __name__ == "__main__":
    test_pure_pos()