#!/usr/bin/env python3
"""
Mine POS-pure words from WordNet for creating a more diverse probe session.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend" / "src"))

from utils.wordnet_mining import WordNetMiner
from transformers import AutoTokenizer
import json

def mine_pos_categories():
    """Mine words that are pure nouns, verbs, and adjectives."""
    print("🚀 Mining POS-pure words from WordNet...")
    
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
    
    # Mine different POS categories
    pos_categories = {
        'n': 'nouns',      # nouns only
        'v': 'verbs',      # verbs only  
        'a': 'adjectives', # adjectives only
        'r': 'adverbs'     # adverbs only
    }
    
    results = {}
    
    for pos_code, pos_name in pos_categories.items():
        print(f"\n🔍 Mining {pos_name} (POS: {pos_code})...")
        words = miner.mine_pos_pure_words(pos_code, max_words=25)
        
        print(f"✅ Found {len(words)} pure {pos_name}:")
        print(f"   Sample: {words[:10]}")
        
        results[pos_name] = words
    
    # Save results
    output_file = Path("scripts/pos_mined_words.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to {output_file}")
    
    # Show summary
    print(f"\n📊 Summary:")
    for pos_name, words in results.items():
        print(f"   {pos_name:12}: {len(words):2d} words")
    
    # Suggest probe session configuration
    print(f"\n🎯 Suggested probe session configuration:")
    print(f"Context sources:")
    print(f"  - Custom: ['the']")
    print(f"Target sources:")
    for pos_name, words in results.items():
        if words:  # Only show categories with words
            sample_words = words[:5]
            print(f"  - Custom: {sample_words} ({pos_name})")
    
    return results

if __name__ == "__main__":
    mine_pos_categories()