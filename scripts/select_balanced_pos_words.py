#!/usr/bin/env python3
"""
Select 50 balanced words from each POS category - mix of common/simple and complex words.
"""

import json
from pathlib import Path

def select_balanced_pos_words():
    """Select 50 words from each POS category with good balance."""
    
    # Load comprehensive results
    pos_file = Path("scripts/comprehensive_pos_words.json")
    if not pos_file.exists():
        print("❌ Run mine_all_pos_comprehensive.py first")
        return None
    
    with open(pos_file) as f:
        all_words = json.load(f)
    
    # Manual selection for balanced, recognizable words
    selected = {
        "nouns": [
            # Common simple nouns (1-2 syllables)
            "cat", "dog", "car", "book", "door", "tree", "bird", "fish", "house", "ball",
            "food", "water", "fire", "sun", "moon", "rock", "wind", "snow", "rain", "ice",
            "hand", "foot", "head", "eye", "ear", "nose", "face", "arm", "leg", "back",
            # Medium complexity nouns
            "animal", "person", "family", "city", "river", "mountain", "forest", "ocean",
            "garden", "kitchen", "window", "picture", "flower", "music", "story", "letter",
            # Complex/abstract nouns
            "knowledge", "freedom", "justice", "beauty", "truth", "wisdom", "courage",
            "education", "government", "technology", "philosophy", "democracy", "economy"
        ],
        
        "verbs": [
            # Common simple verbs (1-2 syllables) 
            "go", "come", "run", "walk", "jump", "sit", "stand", "lie", "eat", "drink",
            "see", "hear", "feel", "smell", "taste", "touch", "hold", "give", "take", "put",
            "open", "close", "start", "stop", "help", "work", "play", "read", "write", "speak",
            # Medium complexity verbs
            "travel", "happen", "change", "create", "destroy", "build", "learn", "teach",
            "remember", "forget", "decide", "choose", "believe", "understand", "explain",
            # Complex verbs
            "investigate", "communicate", "demonstrate", "appreciate", "recognize", "establish"
        ],
        
        "adjectives": [
            # Common simple adjectives
            "big", "small", "hot", "cold", "fast", "slow", "good", "bad", "new", "old",
            "red", "blue", "green", "black", "white", "long", "short", "high", "low", "wide",
            "happy", "sad", "angry", "calm", "kind", "mean", "smart", "dumb", "strong", "weak",
            # Medium complexity adjectives  
            "beautiful", "ugly", "comfortable", "difficult", "easy", "important", "interesting",
            "boring", "dangerous", "safe", "healthy", "sick", "popular", "famous", "quiet",
            # Complex adjectives
            "sophisticated", "controversial", "fundamental", "extraordinary", "magnificent"
        ],
        
        "adverbs": [
            # Common simple adverbs
            "here", "there", "now", "then", "soon", "late", "early", "fast", "slow", "well",
            "badly", "much", "little", "more", "less", "very", "quite", "really", "never", "always",
            "often", "sometimes", "maybe", "yes", "no", "up", "down", "in", "out", "on",
            # Medium complexity adverbs
            "quickly", "slowly", "carefully", "easily", "hardly", "nearly", "certainly", "probably",
            "definitely", "exactly", "completely", "perfectly", "totally", "especially", "particularly",
            # Complex adverbs  
            "immediately", "unfortunately", "fortunately", "absolutely", "approximately"
        ]
    }
    
    # Verify we have available words and substitute if needed
    final_selection = {}
    
    for pos_name, selected_words in selected.items():
        available = all_words.get(pos_name, [])
        
        # Check which selected words are actually available
        verified_words = []
        for word in selected_words:
            if word in available:
                verified_words.append(word)
        
        # If we don't have 50, fill in with additional available words
        if len(verified_words) < 50:
            remaining_needed = 50 - len(verified_words)
            additional_words = []
            for word in available:
                if word not in verified_words and len(additional_words) < remaining_needed:
                    additional_words.append(word)
            verified_words.extend(additional_words)
        
        # Take exactly 50
        final_selection[pos_name] = verified_words[:50]
        
        print(f"✅ {pos_name:20}: {len(final_selection[pos_name])} words selected")
        print(f"   Simple: {final_selection[pos_name][:10]}")
        print(f"   Complex: {final_selection[pos_name][-10:]}")
        print()
    
    # Save selection
    output_file = Path("scripts/balanced_pos_selection.json")
    with open(output_file, "w") as f:
        json.dump(final_selection, f, indent=2)
    
    print(f"💾 Balanced selection saved to {output_file}")
    
    # Summary
    total_words = sum(len(words) for words in final_selection.values())
    print(f"\n📊 BALANCED SELECTION SUMMARY:")
    print(f"   Total words: {total_words}")
    for pos_name, words in final_selection.items():
        print(f"   {pos_name:20}: {len(words):2d} words")
    
    print(f"\n🎯 Probe session specs:")
    print(f"   Context: 1 word ('the')")  
    print(f"   Targets: {total_words} balanced POS words")
    print(f"   Total probes: {total_words}")
    print(f"   Categories: {len(final_selection)} POS types")
    
    return final_selection

if __name__ == "__main__":
    select_balanced_pos_words()