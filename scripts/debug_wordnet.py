#!/usr/bin/env python3
"""
Debug WordNet synsets to understand what's available.
Check if our synset IDs are correct and what words they actually contain.
"""

import nltk
from nltk.corpus import wordnet
import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))


def debug_wordnet():
    """Debug WordNet synsets and word extraction."""
    print("🔍 Debugging WordNet")
    print("=" * 40)
    
    # Check if basic synsets exist
    test_synsets = [
        "animal.n.01",
        "mammal.n.01", 
        "determiner.n.01",
        "person.n.01"
    ]
    
    for synset_id in test_synsets:
        print(f"\n📋 Testing: {synset_id}")
        try:
            synset = wordnet.synset(synset_id)
            print(f"✅ Exists: {synset.definition()}")
            
            # Get direct hyponyms
            hyponyms = synset.hyponyms()
            print(f"📊 Direct hyponyms: {len(hyponyms)}")
            
            if hyponyms:
                for i, hyp in enumerate(hyponyms[:5]):
                    lemmas = [lemma.name() for lemma in hyp.lemmas()]
                    print(f"   {i+1}. {hyp.name()}: {lemmas}")
            
            # Check lemmas in this synset
            lemmas = [lemma.name() for lemma in synset.lemmas()]
            print(f"📝 Direct lemmas: {lemmas}")
            
            # Try to find better synset IDs
            if synset_id == "animal.n.01":
                print("🔍 Looking for better animal synsets:")
                for synset in wordnet.synsets("animal"):
                    print(f"   - {synset.name()}: {synset.definition()[:50]}...")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            
            # Try to find similar synsets
            word = synset_id.split('.')[0]
            print(f"🔍 Searching for '{word}' synsets:")
            for synset in wordnet.synsets(word):
                print(f"   - {synset.name()}: {synset.definition()[:50]}...")
    
    # Test some basic words we expect to work
    print(f"\n🧪 Testing basic words:")
    basic_words = ["cat", "dog", "the", "red", "big"]
    
    for word in basic_words:
        synsets = wordnet.synsets(word)
        print(f"{word}: {len(synsets)} synsets")
        for synset in synsets[:3]:
            print(f"   - {synset.name()}: {synset.definition()[:30]}...")


if __name__ == "__main__":
    debug_wordnet()