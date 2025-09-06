#!/usr/bin/env python3
"""
Test different synsets to find the best demo categories.
Check sizes at different depths and identify most promising categories.
"""

import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from transformers import AutoTokenizer
from utils.wordnet_mining import WordNetMiner


def test_demo_synsets():
    """Test promising synsets for demo effectiveness."""
    print("🎯 Testing Demo Category Synsets")
    print("=" * 50)
    
    # Load tokenizer
    print("📚 Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained("data/models/gpt-oss-20b")
    except:
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    
    miner = WordNetMiner(tokenizer)
    
    # Test categories for demos
    demo_synsets = [
        # Basic semantic categories
        ("body_part.n.01", "Body parts"),
        ("food.n.02", "Food"),
        ("mammal.n.01", "Mammals"),
        ("bird.n.01", "Birds"),
        
        # Functional categories  
        ("function_word.n.01", "Function words"),
        ("determiner.n.01", "Determiners"),
        ("pronoun.n.01", "Pronouns"),
        
        # Emotions and concepts
        ("emotion.n.01", "Emotions"),
        ("number.n.02", "Numbers"),
        ("family.n.01", "Family"),
        
        # Objects
        ("clothing.n.01", "Clothing"),
        ("tool.n.01", "Tools"),
        ("vehicle.n.01", "Vehicles"),
        
        # Colors and properties
        ("chromatic_color.n.01", "Colors"),
        ("size.n.01", "Size words")
    ]
    
    results = []
    
    for synset_id, description in demo_synsets:
        print(f"\n🔍 Testing: {description} ({synset_id})")
        
        for depth in [2, 3]:
            try:
                words = miner.mine_unambiguous_words(synset_id, max_depth=depth)
                count = len(words)
                print(f"   Depth {depth}: {count} words", end="")
                
                if count > 0:
                    sample = words[:5]
                    print(f" - Sample: {sample}")
                    results.append((description, synset_id, depth, count, sample))
                else:
                    print(" - No words found")
                    
            except Exception as e:
                print(f"   Depth {depth}: Error - {e}")
    
    # Show best categories for demos
    print(f"\n🏆 BEST DEMO CATEGORIES:")
    print("=" * 50)
    
    good_results = [r for r in results if r[3] >= 5]  # At least 5 words
    good_results.sort(key=lambda x: x[3], reverse=True)  # Sort by word count
    
    for description, synset_id, depth, count, sample in good_results[:10]:
        print(f"✅ {description:15} | {count:2d} words | depth {depth} | {sample}")
    
    if not good_results:
        print("⚠️ No categories found with 5+ unambiguous words")
        print("   Consider relaxing unambiguous requirement or trying different synsets")


if __name__ == "__main__":
    test_demo_synsets()