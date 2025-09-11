#!/usr/bin/env python3
"""
Create probe session with 4 POS categories, each having mix of simple and complex words.
"""

import requests
import json
from pathlib import Path

def create_simple_pos_probe():
    """Create probe with 4 POS categories, 50 words each, mixed complexity."""
    
    # Load available words
    pos_file = Path("scripts/comprehensive_pos_words.json")
    with open(pos_file) as f:
        available = json.load(f)
    
    # Select 50 from each category - mix simple and complex
    selected = {
        "nouns": [],
        "verbs": [], 
        "adjectives": [],
        "adverbs": []
    }
    
    # For each POS, take mix of short (simple) and long (complex) words
    for pos_name in selected.keys():
        available_words = available.get(pos_name, [])
        if pos_name == "adjectives":
            # Combine adjectives and adjective_satellites
            available_words.extend(available.get("adjective_satellites", []))
        
        # Filter to good words (alphabetic, reasonable length)
        good_words = [
            word for word in available_words 
            if (word.isalpha() and 
                3 <= len(word) <= 15 and
                not word.startswith(('aaa', 'aba', 'aar')))
        ]
        
        # Sort by length to get mix
        good_words.sort(key=len)
        
        # Take 25 shorter words (simple) and 25 longer words (complex)  
        simple_words = good_words[:len(good_words)//2][:25]
        complex_words = good_words[len(good_words)//2:][:25]
        
        selected[pos_name] = simple_words + complex_words
        
        print(f"✅ {pos_name:12}: {len(selected[pos_name]):2d} words")
        print(f"   Simple:  {simple_words[:5]} (avg: {sum(len(w) for w in simple_words)/len(simple_words):.1f} chars)")
        print(f"   Complex: {complex_words[-5:]} (avg: {sum(len(w) for w in complex_words)/len(complex_words):.1f} chars)")
        print()
    
    # Create probe request
    probe_request = {
        "session_name": "POS Analysis - 4 Categories Mixed Complexity",
        "context_sources": [
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["the"],
                    "category": "determiner"
                }
            }
        ],
        "target_sources": [
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected["nouns"],
                    "category": "nouns"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected["verbs"],
                    "category": "verbs"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected["adjectives"], 
                    "category": "adjectives"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected["adverbs"],
                    "category": "adverbs"
                }
            }
        ]
    }
    
    total_words = sum(len(words) for words in selected.values())
    print(f"🎯 Probe session: {total_words} words, 4 POS categories, mixed complexity")
    
    # Save for execution
    with open("scripts/simple_pos_probe_request.json", "w") as f:
        json.dump(probe_request, f, indent=2)
    
    return probe_request

if __name__ == "__main__":
    create_simple_pos_probe()