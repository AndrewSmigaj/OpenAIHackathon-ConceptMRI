#!/usr/bin/env python3
"""
Comprehensive POS mining - get ALL pure words from ALL POS categories.
No limits, no filtering, maximum data.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend" / "src"))

from utils.wordnet_mining import WordNetMiner
from transformers import AutoTokenizer
import json
import nltk
from nltk.corpus import wordnet

def mine_all_pos_comprehensive():
    """Mine ALL pure words from ALL POS categories without limits."""
    print("🚀 Comprehensive POS mining - getting EVERYTHING...")
    
    # Load tokenizer
    model_path = Path(__file__).parent.parent / "data" / "models" / "gpt-oss-20b"
    if not model_path.exists():
        print("❌ Model not found - using default tokenizer")
        tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-j-6B")
    else:
        print(f"📚 Loading tokenizer from {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    
    # Initialize miner
    miner = WordNetMiner(tokenizer)
    
    # All possible POS categories in WordNet
    all_pos_categories = {
        'n': 'nouns',
        'v': 'verbs', 
        'a': 'adjectives',
        's': 'adjective_satellites',  # Adjective satellites (similar to adjectives)
        'r': 'adverbs'
    }
    
    results = {}
    total_words = 0
    
    for pos_code, pos_name in all_pos_categories.items():
        print(f"\n🔍 Mining ALL {pos_name} (POS: {pos_code})...")
        
        # Get ALL synsets for this POS (no limits)
        all_synsets = list(wordnet.all_synsets(pos=pos_code))
        print(f"   Found {len(all_synsets)} synsets to process...")
        
        words_found = []
        checked_words = set()
        processed = 0
        
        for synset in all_synsets:
            processed += 1
            if processed % 1000 == 0:
                print(f"   Processed {processed}/{len(all_synsets)} synsets, found {len(words_found)} words...")
            
            for lemma in synset.lemmas():
                word = lemma.name().lower()
                
                # Skip if already checked or has underscores/spaces
                if word in checked_words or '_' in word or ' ' in word:
                    continue
                
                checked_words.add(word)
                
                # Check: does this word ONLY appear as this POS?
                all_synsets_for_word = wordnet.synsets(word)
                all_pos_for_word = set(s.pos() for s in all_synsets_for_word)
                
                if len(all_pos_for_word) == 1 and pos_code in all_pos_for_word:  # Only this POS
                    # Check single token
                    try:
                        tokens = tokenizer.encode(word, add_special_tokens=False)
                        if len(tokens) == 1:
                            words_found.append(word)
                    except Exception:
                        continue
        
        result_words = sorted(set(words_found))
        results[pos_name] = result_words
        total_words += len(result_words)
        
        print(f"✅ Found {len(result_words)} pure {pos_name}")
        if len(result_words) > 0:
            print(f"   Sample: {result_words[:10]}")
    
    # Save comprehensive results
    output_file = Path("scripts/comprehensive_pos_words.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Comprehensive results saved to {output_file}")
    
    # Show complete summary
    print(f"\n📊 COMPREHENSIVE SUMMARY:")
    print(f"   Total pure words found: {total_words}")
    for pos_name, words in results.items():
        print(f"   {pos_name:20}: {len(words):4d} words")
    
    # Calculate total probe pairs
    total_targets = sum(len(words) for words in results.values())
    print(f"\n🎯 Probe session potential:")
    print(f"   Context: 1 word ('the')")
    print(f"   Targets: {total_targets} pure POS words")
    print(f"   Total probes: {total_targets}")
    
    return results

if __name__ == "__main__":
    mine_all_pos_comprehensive()