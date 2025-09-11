#!/usr/bin/env python3
"""
Create probe session with carefully curated POS words - common and recognizable.
"""

import requests
import json
from pathlib import Path

def get_curated_pos_words():
    """Get manually curated, high-quality POS words."""
    
    # Load comprehensive results to verify availability
    pos_file = Path("scripts/comprehensive_pos_words.json")
    with open(pos_file) as f:
        available_words = json.load(f)
    
    # Manually curated high-quality words
    curated = {
        "pure_nouns": [
            # Common concrete nouns
            "car", "door", "food", "water", "fire", "sun", "moon", "tree", "bird", "fish",
            "house", "ball", "hand", "foot", "head", "eye", "ear", "nose", "face", "arm",
            # Medium complexity
            "person", "family", "city", "river", "mountain", "forest", "ocean", "garden", 
            "window", "picture", "flower", "music", "story", "letter", "animal", "kitchen",
            # Abstract/complex
            "knowledge", "freedom", "justice", "beauty", "truth", "wisdom", "courage",
            "education", "government", "technology", "philosophy", "democracy", "economy",
            "achievement", "communication", "implementation", "interaction", "application"
        ],
        
        "pure_verbs": [
            # Common simple verbs
            "sit", "eat", "drink", "hear", "feel", "smell", "taste", "touch", "hold", "give",
            "take", "put", "open", "close", "start", "stop", "help", "work", "play", "read", 
            "write", "speak", "walk", "jump", "stand", "sleep", "wake", "come", "leave",
            # Medium complexity
            "travel", "happen", "change", "create", "destroy", "build", "learn", "teach",
            "remember", "forget", "decide", "choose", "believe", "understand", "explain",
            # Complex verbs
            "communicate", "demonstrate", "appreciate", "recognize", "establish", "develop"
        ],
        
        "pure_adjectives": [
            # Use what's available from WordNet - most common adjectives are ambiguous
            "adaptive", "analytic", "angular", "avoidable", "aware", "basic", "digital",
            "existent", "functional", "genetic", "magnetic", "metric", "numeric", "organic",
            "semantic", "solar", "thermal", "toxic", "unique", "vertical", "visual",
            # Include some from adjective_satellites if needed
        ],
        
        "pure_adverbs": [
            # Common adverbs that are pure
            "again", "already", "always", "approximately", "around", "especially", "ever",
            "fortunately", "fully", "however", "mostly", "never", "often", "quite", 
            "really", "sometimes", "soon", "yet", "actually", "actively", "almost",
            "along", "also", "completely", "definitely", "exactly", "immediately",
            "necessarily", "particularly", "perfectly", "probably", "totally", "truly"
        ]
    }
    
    # Verify words are available and fill to 50 each
    final_selection = {}
    
    for category, word_list in curated.items():
        pos_type = category.replace("pure_", "")
        if pos_type == "adjectives":
            # Combine regular adjectives and adjective_satellites
            available = available_words.get("adjectives", []) + available_words.get("adjective_satellites", [])
        else:
            available = available_words.get(pos_type, [])
        
        # Filter to only available words
        verified = [word for word in word_list if word in available]
        
        # Fill remaining slots with high-quality available words
        if len(verified) < 50:
            remaining = 50 - len(verified)
            # Add more good words from available set
            for word in available:
                if (word not in verified and 
                    len(word) > 2 and  # Skip very short words
                    word.isalpha() and  # Only alphabetic
                    not word.startswith(('aaa', 'aa', 'aba')) and  # Skip weird ones
                    len(verified) < 50):
                    verified.append(word)
        
        final_selection[category] = verified[:50]
        print(f"✅ {category:15}: {len(final_selection[category]):2d} words")
        print(f"   Sample: {final_selection[category][:8]}")
        print(f"   Complex: {final_selection[category][-5:]}")
        print()
    
    return final_selection

def create_curated_probe_session():
    """Create probe session with curated POS words."""
    
    # Get curated words
    selected_words = get_curated_pos_words()
    
    # Create probe request
    probe_request = {
        "session_name": "POS Pure Words - Curated Balanced Set",
        "context_sources": [
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["the"],
                    "category": "determiner"
                }
            }
        ],
        "target_sources": []
    }
    
    # Add target sources for each POS category
    for category, words in selected_words.items():
        probe_request["target_sources"].append({
            "source_type": "custom",
            "source_params": {
                "words": words,
                "category": category
            }
        })
    
    total_targets = sum(len(words) for words in selected_words.values())
    
    print(f"🚀 Creating curated POS probe session...")
    print(f"   Context: 1 word (determiner)")
    print(f"   Targets: {total_targets} curated words across {len(selected_words)} POS categories")
    print(f"   Total probes: {total_targets}")
    
    # Save request for review
    with open("scripts/curated_pos_probe_request.json", "w") as f:
        json.dump(probe_request, f, indent=2)
    print(f"💾 Probe request saved to scripts/curated_pos_probe_request.json")
    
    return probe_request

if __name__ == "__main__":
    create_curated_probe_session()