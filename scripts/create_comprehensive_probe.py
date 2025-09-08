#!/usr/bin/env python3
"""
Create comprehensive multi-category probe for content vs function analysis.
"""

import json
import requests
from pathlib import Path

# Word collections with careful manual curation
SIMPLE_CONCRETE_POSITIVE_NOUNS = [
    "home", "gift", "flower", "friend", "baby", "party", "smile", "sun", "star", "rainbow",
    "garden", "beach", "music", "dance", "cake", "candy", "toy", "game", "pet", "puppy",
    "kitten", "bird", "butterfly", "diamond", "gold", "crown", "prize", "trophy", "medal", "ring",
    "mother", "father", "family", "hug", "kiss", "laugh", "warmth", "nest", "shelter", "rose",
    "tree", "forest", "ocean", "lake", "mountain", "valley", "meadow", "dolphin", "rabbit",
    "deer", "horse", "lamb", "dove", "chocolate", "ice", "cream", "fruit", "apple", "honey",
    "bread", "feast", "meal", "birthday", "wedding", "present", "champion", "hero", "talent",
    "art", "song", "performance", "jewel", "treasure", "gem", "pearl", "crystal", "necklace",
    "coin", "money", "wealth", "palace", "castle", "paradise", "heaven", "book", "story",
    "magic", "wonder", "miracle", "dream", "wish", "hope", "future", "promise", "adventure"
]

SIMPLE_CONCRETE_NEGATIVE_NOUNS = [
    "weapon", "prison", "disease", "enemy", "pain", "war", "bomb", "poison", "trap", "fire",
    "storm", "flood", "earthquake", "accident", "injury", "scar", "wound", "blood", "knife", "gun",
    "spider", "snake", "rat", "garbage", "dirt", "mud", "rust", "rot", "mold", "virus"
]

SIMPLE_CONCRETE_NEUTRAL_NOUNS = [
    "table", "chair", "door", "window", "paper", "rock", "wheel", "metal", "wood", "glass",
    "water", "stone", "sand", "ice", "snow", "rain", "wind", "cloud", "tree", "grass",
    "book", "pen", "car", "house", "road", "bridge", "wall", "floor", "roof", "box"
]

SIMPLE_ABSTRACT_POSITIVE_NOUNS = [
    "love", "joy", "hope", "peace", "freedom", "beauty", "truth", "wisdom", "success", "luck",
    "courage", "strength", "faith", "trust", "honor", "pride", "happiness", "delight", "bliss", "glory",
    "victory", "triumph", "achievement", "progress", "growth", "health", "wealth", "comfort", "safety", "security"
]

SIMPLE_ABSTRACT_NEGATIVE_NOUNS = [
    "hate", "fear", "anger", "sadness", "despair", "ugliness", "lie", "ignorance", "failure", "loss",
    "weakness", "shame", "guilt", "doubt", "worry", "stress", "anxiety", "depression", "loneliness", "emptiness",
    "defeat", "disaster", "crisis", "trouble", "problem", "mistake", "error", "fault", "danger", "threat"
]

SIMPLE_ABSTRACT_NEUTRAL_NOUNS = [
    "time", "space", "number", "size", "weight", "color", "shape", "sound", "smell", "taste",
    "idea", "thought", "memory", "dream", "fact", "rule", "law", "system", "method", "way",
    "reason", "cause", "effect", "result", "change", "difference", "similarity", "pattern", "order", "structure"
]

SIMPLE_ACTION_POSITIVE_VERBS = [
    "love", "help", "create", "build", "grow", "learn", "teach", "give", "share", "celebrate",
    "smile", "laugh", "dance", "sing", "play", "enjoy", "succeed", "win", "achieve", "accomplish",
    "heal", "cure", "save", "protect", "defend", "support", "encourage", "inspire", "motivate", "uplift"
]

SIMPLE_ACTION_NEGATIVE_VERBS = [
    "hate", "hurt", "destroy", "break", "kill", "attack", "fight", "steal", "lie", "cheat",
    "cry", "scream", "suffer", "fail", "lose", "fall", "crash", "burn", "cut", "stab",
    "poison", "infect", "damage", "ruin", "waste", "abandon", "betray", "deceive", "corrupt", "pollute"
]

SIMPLE_ACTION_NEUTRAL_VERBS = [
    "run", "walk", "jump", "sit", "stand", "look", "see", "hear", "touch", "move",
    "eat", "drink", "sleep", "wake", "work", "study", "read", "write", "draw", "paint",
    "drive", "ride", "travel", "visit", "meet", "talk", "speak", "listen", "think", "remember"
]

SIMPLE_STATE_POSITIVE_VERBS = [
    "be", "exist", "live", "thrive", "flourish", "bloom", "shine", "glow", "sparkle", "radiate",
    "feel", "seem", "appear", "become", "remain", "stay", "continue", "last", "endure", "survive",
    "rest", "relax", "calm", "peace", "comfort", "satisfy", "please", "delight", "amaze", "impress"
]

SIMPLE_STATE_NEGATIVE_VERBS = [
    "die", "decay", "rot", "fade", "wither", "shrink", "weaken", "suffer", "ache", "hurt",
    "worry", "fear", "doubt", "regret", "mourn", "grieve", "despair", "struggle", "fail", "collapse",
    "sick", "ill", "tired", "exhaust", "drain", "empty", "hollow", "bitter", "sour", "stale"
]

SIMPLE_STATE_NEUTRAL_VERBS = [
    "happen", "occur", "begin", "start", "end", "finish", "change", "turn", "shift", "move",
    "contain", "hold", "include", "involve", "relate", "connect", "link", "join", "separate", "divide",
    "measure", "weigh", "count", "calculate", "compare", "match", "equal", "differ", "vary", "range"
]

def create_comprehensive_probe():
    """Create comprehensive probe with multi-category tagging."""
    
    # Context sources
    context_sources = [
        {
            "source_type": "custom",
            "source_params": {"words": ["the"], "label": "determiner"}
        },
        {
            "source_type": "custom", 
            "source_params": {"words": ["I"], "label": "pronoun"}
        }
    ]
    
    # Collect all words
    all_nouns = (SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_CONCRETE_NEGATIVE_NOUNS + 
                SIMPLE_CONCRETE_NEUTRAL_NOUNS + SIMPLE_ABSTRACT_POSITIVE_NOUNS + 
                SIMPLE_ABSTRACT_NEGATIVE_NOUNS + SIMPLE_ABSTRACT_NEUTRAL_NOUNS)
    
    all_verbs = (SIMPLE_ACTION_POSITIVE_VERBS + SIMPLE_ACTION_NEGATIVE_VERBS + 
                SIMPLE_ACTION_NEUTRAL_VERBS + SIMPLE_STATE_POSITIVE_VERBS + 
                SIMPLE_STATE_NEGATIVE_VERBS + SIMPLE_STATE_NEUTRAL_VERBS)
    
    target_sources = []
    
    # Content/Function categories
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": all_nouns + all_verbs, "label": "content"}
    })
    
    # POS categories
    target_sources.append({
        "source_type": "custom", 
        "source_params": {"words": all_nouns, "label": "nouns"}
    })
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": all_verbs, "label": "verbs"}
    })
    
    # Complexity (all simple for now)
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": all_nouns + all_verbs, "label": "simple"}
    })
    
    # Concreteness for nouns
    concrete_nouns = SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_CONCRETE_NEGATIVE_NOUNS + SIMPLE_CONCRETE_NEUTRAL_NOUNS
    abstract_nouns = SIMPLE_ABSTRACT_POSITIVE_NOUNS + SIMPLE_ABSTRACT_NEGATIVE_NOUNS + SIMPLE_ABSTRACT_NEUTRAL_NOUNS
    
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": concrete_nouns, "label": "concrete"}
    })
    target_sources.append({
        "source_type": "custom", 
        "source_params": {"words": abstract_nouns, "label": "abstract"}
    })
    
    # Action/State for verbs
    action_verbs = SIMPLE_ACTION_POSITIVE_VERBS + SIMPLE_ACTION_NEGATIVE_VERBS + SIMPLE_ACTION_NEUTRAL_VERBS
    state_verbs = SIMPLE_STATE_POSITIVE_VERBS + SIMPLE_STATE_NEGATIVE_VERBS + SIMPLE_STATE_NEUTRAL_VERBS
    
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": action_verbs, "label": "action"}
    })
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": state_verbs, "label": "state"}
    })
    
    # Sentiment categories
    positive_words = (SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_ABSTRACT_POSITIVE_NOUNS + 
                     SIMPLE_ACTION_POSITIVE_VERBS + SIMPLE_STATE_POSITIVE_VERBS)
    negative_words = (SIMPLE_CONCRETE_NEGATIVE_NOUNS + SIMPLE_ABSTRACT_NEGATIVE_NOUNS + 
                     SIMPLE_ACTION_NEGATIVE_VERBS + SIMPLE_STATE_NEGATIVE_VERBS)
    neutral_words = (SIMPLE_CONCRETE_NEUTRAL_NOUNS + SIMPLE_ABSTRACT_NEUTRAL_NOUNS + 
                    SIMPLE_ACTION_NEUTRAL_VERBS + SIMPLE_STATE_NEUTRAL_VERBS)
    
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": positive_words, "label": "positive"}
    })
    target_sources.append({
        "source_type": "custom", 
        "source_params": {"words": negative_words, "label": "negative"}
    })
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": neutral_words, "label": "neutral"}
    })
    
    probe_request = {
        "session_name": "Comprehensive Multi-Category Analysis - Content vs Function",
        "context_sources": context_sources,
        "target_sources": target_sources
    }
    
    return probe_request

def main():
    """Create and execute comprehensive probe."""
    print("🔬 Creating comprehensive multi-category probe...")
    
    probe_request = create_comprehensive_probe()
    
    # Calculate totals
    total_targets = len(set(word for source in probe_request["target_sources"] 
                           for word in source["source_params"]["words"]))
    total_contexts = len(set(word for source in probe_request["context_sources"]
                            for word in source["source_params"]["words"]))
    estimated_pairs = total_contexts * total_targets
    
    print(f"📊 Probe Statistics:")
    print(f"   Contexts: {total_contexts}")
    print(f"   Unique Targets: {total_targets}")  
    print(f"   Total Pairs: {estimated_pairs}")
    print(f"   Category Sources: {len(probe_request['target_sources'])}")
    
    # Save to file
    output_file = Path("comprehensive_probe_request.json")
    with open(output_file, 'w') as f:
        json.dump(probe_request, f, indent=2)
    print(f"💾 Saved probe configuration to {output_file}")
    
    # Execute via API
    try:
        print("\n🚀 Creating session via API...")
        response = requests.post("http://localhost:8000/api/probes", 
                               json=probe_request, 
                               headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            session_id = result["session_id"]
            print(f"✅ Session created: {session_id}")
            print(f"   Total pairs: {result['total_pairs']}")
            
            # Execute session
            print(f"\n⚡ Executing session {session_id}...")
            exec_response = requests.post(f"http://localhost:8000/api/probes/{session_id}/execute")
            
            if exec_response.status_code == 200:
                exec_result = exec_response.json()
                print(f"✅ Execution started!")
                print(f"   Probe IDs generated: {len(exec_result['probe_ids'])}")
                print(f"   Estimated time: {exec_result['estimated_time']}")
            else:
                print(f"❌ Execution failed: {exec_response.status_code}")
                print(exec_response.text)
                
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print("You can manually use the saved JSON file")

if __name__ == "__main__":
    main()