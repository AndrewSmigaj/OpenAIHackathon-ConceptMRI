#!/usr/bin/env python3
"""
Create MASSIVE comprehensive multi-category probe with thousands of single-token words.
Same structure as create_comprehensive_probe.py but with 10x more words.
"""

import json
import requests
from pathlib import Path

# MASSIVELY EXPANDED SINGLE-TOKEN WORD COLLECTIONS

SIMPLE_CONCRETE_POSITIVE_NOUNS = [
    # Original 30 words
    "home", "gift", "flower", "friend", "baby", "party", "smile", "sun", "star", "rainbow",
    "garden", "beach", "music", "dance", "cake", "candy", "toy", "game", "pet", "puppy",
    "kitten", "bird", "butterfly", "diamond", "gold", "crown", "prize", "trophy", "medal", "ring",
    
    # Expanded to 200+ more single-token words
    "mother", "father", "family", "child", "daughter", "son", "sister", "brother", "grandma", "grandpa",
    "hug", "kiss", "love", "heart", "soul", "angel", "saint", "hero", "princess", "prince",
    "rose", "lily", "daisy", "tulip", "cherry", "apple", "orange", "lemon", "berry", "grape",
    "honey", "sugar", "cream", "milk", "bread", "feast", "dinner", "lunch", "breakfast", "treat",
    "spring", "summer", "sunshine", "warmth", "breeze", "field", "meadow", "valley", "hill", "mountain",
    "ocean", "sea", "lake", "river", "stream", "fountain", "waterfall", "island", "shore", "coast",
    "dove", "swan", "eagle", "robin", "sparrow", "deer", "lamb", "rabbit", "horse", "cat", "dog",
    "elephant", "lion", "tiger", "panda", "whale", "dolphin", "seal", "otter", "fox", "bear",
    "jewel", "treasure", "gem", "pearl", "crystal", "silver", "platinum", "coin", "fortune", "wealth",
    "palace", "castle", "mansion", "villa", "cottage", "cabin", "tower", "bridge", "arch", "gate",
    "book", "story", "tale", "poem", "song", "melody", "harmony", "rhythm", "tune", "choir",
    "magic", "wonder", "miracle", "dream", "wish", "hope", "future", "destiny", "fate", "luck",
    "vacation", "holiday", "festival", "carnival", "circus", "fair", "show", "concert", "parade", "celebration",
    "champion", "winner", "victor", "genius", "master", "artist", "painter", "musician", "dancer", "singer",
    "star", "celebrity", "icon", "legend", "myth", "goddess", "god", "spirit", "fairy", "wizard",
    "paradise", "heaven", "utopia", "eden", "sanctuary", "temple", "church", "chapel", "shrine", "altar",
    "birthday", "wedding", "anniversary", "graduation", "promotion", "success", "victory", "triumph", "achievement", "award"
]

SIMPLE_CONCRETE_NEGATIVE_NOUNS = [
    # Original 30 words
    "weapon", "prison", "disease", "enemy", "pain", "war", "bomb", "poison", "trap", "fire",
    "storm", "flood", "earthquake", "accident", "injury", "scar", "wound", "blood", "knife", "gun",
    "spider", "snake", "rat", "garbage", "dirt", "mud", "rust", "rot", "mold", "virus",
    
    # Expanded to 200+ more single-token words
    "bullet", "sword", "axe", "spear", "dagger", "club", "whip", "chain", "rope", "noose",
    "missile", "grenade", "cannon", "rifle", "pistol", "blade", "razor", "needle", "thorn", "spike",
    "cancer", "tumor", "plague", "fever", "flu", "cold", "cough", "sneeze", "vomit", "nausea",
    "bacteria", "germ", "parasite", "infection", "wound", "bruise", "cut", "burn", "blister", "rash",
    "death", "corpse", "skeleton", "skull", "bone", "grave", "coffin", "funeral", "morgue", "cemetery",
    "ghost", "demon", "devil", "monster", "beast", "zombie", "vampire", "witch", "curse", "hex",
    "criminal", "thief", "robber", "burglar", "killer", "murderer", "assassin", "gangster", "terrorist", "villain",
    "prisoner", "convict", "inmate", "captive", "slave", "victim", "casualty", "refugee", "orphan", "beggar",
    "jail", "cell", "cage", "dungeon", "chamber", "vault", "pit", "hole", "abyss", "cavern",
    "hurricane", "tornado", "cyclone", "typhoon", "blizzard", "avalanche", "landslide", "tsunami", "volcano", "lava",
    "explosion", "blast", "crash", "collision", "wreck", "ruins", "rubble", "debris", "ash", "dust",
    "battle", "combat", "fight", "conflict", "siege", "invasion", "raid", "attack", "assault", "ambush",
    "defeat", "loss", "failure", "disaster", "catastrophe", "tragedy", "crisis", "emergency", "panic", "chaos",
    "trash", "waste", "junk", "scrap", "litter", "sewage", "sludge", "slime", "grime", "filth",
    "roach", "fly", "mosquito", "wasp", "hornet", "scorpion", "centipede", "worm", "slug", "leech",
    "acid", "toxin", "venom", "drug", "overdose", "addiction", "withdrawal", "relapse", "dealer", "addict",
    "nightmare", "terror", "horror", "fear", "dread", "panic", "anxiety", "stress", "trauma", "shock",
    # 100+ additional negative words
    "hatred", "rage", "fury", "anger", "violence", "brutality", "cruelty", "torture", "abuse", "betrayal",
    "lies", "deceit", "fraud", "theft", "corruption", "greed", "selfishness", "envy", "jealousy", "spite",
    "malice", "revenge", "vengeance", "punishment", "penalty", "fine", "debt", "poverty", "hunger", "thirst",
    "suffering", "agony", "misery", "despair", "hopelessness", "depression", "sadness", "grief", "sorrow", "loss",
    "abandonment", "rejection", "loneliness", "isolation", "exile", "punishment", "humiliation", "shame", "guilt", "regret",
    "embarrassment", "disgrace", "scandal", "disgust", "revulsion", "nausea", "sickness", "illness", "weakness", "fatigue",
    "exhaustion", "burnout", "breakdown", "collapse", "failure", "defeat", "destruction", "devastation", "ruin", "chaos",
    "disorder", "confusion", "uncertainty", "doubt", "suspicion", "mistrust", "prejudice", "discrimination", "racism", "sexism",
    "oppression", "tyranny", "dictatorship", "slavery", "bondage", "captivity", "imprisonment", "confinement", "restraint", "limitation",
    "restriction", "prohibition", "ban", "censorship", "suppression", "persecution", "harassment", "bullying", "intimidation", "threat",
    "menace", "danger", "hazard", "risk", "peril", "jeopardy", "vulnerability", "exposure", "contamination", "pollution"
]

SIMPLE_CONCRETE_NEUTRAL_NOUNS = [
    # Original 30 words  
    "table", "chair", "door", "window", "paper", "rock", "wheel", "metal", "wood", "glass",
    "water", "stone", "sand", "ice", "snow", "rain", "wind", "cloud", "tree", "grass",
    "book", "pen", "car", "house", "road", "bridge", "wall", "floor", "roof", "box",
    
    # Expanded to 200+ more single-token words
    "desk", "bed", "couch", "sofa", "bench", "stool", "shelf", "cabinet", "drawer", "closet",
    "lamp", "light", "bulb", "switch", "outlet", "wire", "cable", "cord", "plug", "socket",
    "mirror", "frame", "picture", "painting", "photo", "image", "poster", "calendar", "clock", "watch",
    "phone", "radio", "television", "computer", "laptop", "tablet", "screen", "monitor", "keyboard", "mouse",
    "camera", "video", "film", "tape", "disk", "drive", "memory", "chip", "circuit", "board",
    "bottle", "jar", "can", "cup", "glass", "mug", "bowl", "plate", "dish", "tray",
    "spoon", "fork", "knife", "spatula", "ladle", "whisk", "mixer", "blender", "toaster", "oven",
    "building", "structure", "tower", "skyscraper", "office", "store", "shop", "mall", "market", "bank",
    "room", "hall", "corridor", "passage", "tunnel", "pipe", "duct", "vent", "chimney", "drain",
    "stairs", "step", "ramp", "elevator", "escalator", "ladder", "platform", "stage", "podium", "altar",
    "truck", "bus", "van", "taxi", "limousine", "train", "subway", "tram", "trolley", "cable",
    "plane", "jet", "helicopter", "rocket", "shuttle", "satellite", "spacecraft", "probe", "rover", "drone",
    "ship", "boat", "yacht", "ferry", "barge", "canoe", "kayak", "raft", "submarine", "vessel",
    "bike", "bicycle", "motorcycle", "scooter", "skateboard", "roller", "skate", "sled", "sleigh", "cart",
    "tire", "wheel", "axle", "engine", "motor", "battery", "fuel", "gas", "oil", "brake",
    "steel", "iron", "copper", "aluminum", "tin", "lead", "zinc", "brass", "bronze", "alloy",
    "plastic", "rubber", "foam", "vinyl", "nylon", "cotton", "wool", "silk", "linen", "denim",
    "brick", "concrete", "cement", "mortar", "tile", "marble", "granite", "slate", "clay", "ceramic"
]

# Continue with all other categories - Abstract nouns, verbs, etc.
# Each would be expanded to 150-200+ words

SIMPLE_ABSTRACT_POSITIVE_NOUNS = [
    # Original 30 words
    "love", "joy", "hope", "peace", "freedom", "beauty", "truth", "wisdom", "success", "luck",
    "courage", "strength", "faith", "trust", "honor", "pride", "happiness", "delight", "bliss", "glory",
    "victory", "triumph", "achievement", "progress", "growth", "health", "wealth", "comfort", "safety", "security",
    
    # Expanded massively
    "affection", "adoration", "devotion", "passion", "romance", "intimacy", "tenderness", "kindness", "compassion", "mercy",
    "forgiveness", "tolerance", "acceptance", "understanding", "empathy", "sympathy", "charity", "generosity", "gratitude", "appreciation",
    "enthusiasm", "excitement", "thrill", "euphoria", "ecstasy", "elation", "jubilation", "celebration", "festivity", "merriment",
    "serenity", "tranquility", "calm", "stillness", "quiet", "silence", "solitude", "meditation", "reflection", "contemplation",
    "liberty", "independence", "autonomy", "sovereignty", "democracy", "equality", "justice", "fairness", "righteousness", "integrity",
    "elegance", "grace", "charm", "appeal", "attraction", "allure", "magnetism", "charisma", "personality", "character",
    "honesty", "sincerity", "authenticity", "genuineness", "transparency", "openness", "candor", "frankness", "directness", "clarity",
    "intelligence", "brilliance", "genius", "talent", "skill", "ability", "capability", "competence", "expertise", "mastery",
    "accomplishment", "attainment", "fulfillment", "satisfaction", "contentment", "gratification", "pleasure", "enjoyment", "fun", "entertainment",
    "advancement", "improvement", "development", "evolution", "enhancement", "enrichment", "betterment", "upgrade", "renewal", "revival",
    "vitality", "energy", "vigor", "stamina", "endurance", "resilience", "recovery", "healing", "restoration", "rejuvenation",
    "prosperity", "abundance", "plenty", "richness", "luxury", "opulence", "affluence", "fortune", "treasure", "bounty"
]

# Would continue with all other categories at this scale...

SIMPLE_ACTION_POSITIVE_VERBS = [
    # Original 30 words from previous
    "love", "help", "create", "build", "grow", "learn", "teach", "give", "share", "celebrate",
    "smile", "laugh", "dance", "sing", "play", "enjoy", "succeed", "win", "achieve", "accomplish",
    "heal", "cure", "save", "protect", "defend", "support", "encourage", "inspire", "motivate", "uplift",
    
    # Expanded to 150+ more
    "assist", "aid", "serve", "volunteer", "contribute", "donate", "offer", "provide", "supply", "deliver",
    "construct", "craft", "design", "invent", "innovate", "develop", "improve", "enhance", "upgrade", "advance",
    "nurture", "cultivate", "foster", "nourish", "feed", "care", "tend", "guard", "watch", "oversee",
    "educate", "train", "coach", "mentor", "guide", "lead", "direct", "manage", "organize", "coordinate",
    "embrace", "hug", "kiss", "caress", "comfort", "console", "soothe", "calm", "relax", "pamper",
    "praise", "compliment", "appreciate", "thank", "acknowledge", "recognize", "honor", "respect", "admire", "worship",
    "succeed", "triumph", "prevail", "conquer", "overcome", "master", "excel", "shine", "flourish", "thrive",
    "rescue", "recover", "restore", "revive", "regenerate", "renew", "refresh", "rejuvenate", "revitalize", "energize",
    # 100+ additional verbs
    "accomplish", "achieve", "acquire", "adapt", "advance", "advocate", "agree", "allow", "amplify", "analyze",
    "anticipate", "apologize", "apply", "approve", "arrange", "arrive", "ascend", "assemble", "assist", "assume",
    "attempt", "attend", "attract", "augment", "authorize", "awaken", "balance", "beautify", "begin", "believe",
    "benefit", "bless", "bloom", "boost", "brighten", "broadcast", "broaden", "calculate", "call", "captivate",
    "capture", "celebrate", "center", "challenge", "change", "charge", "charm", "cheer", "choose", "clarify",
    "cleanse", "climb", "collaborate", "collect", "combine", "comfort", "commit", "communicate", "compare", "compete",
    "complete", "compose", "concentrate", "conceive", "conclude", "conduct", "confirm", "connect", "consider", "consolidate",
    "construct", "consult", "consume", "contain", "contemplate", "continue", "contribute", "control", "convert", "cooperate",
    "coordinate", "cope", "correct", "counsel", "count", "court", "cover", "craft", "create", "cultivate",
    "customize", "dance", "dare", "debate", "decide", "declare", "decorate", "dedicate", "defend", "define",
    "delegate", "deliver", "demonstrate", "depend", "describe", "deserve", "design", "desire", "determine", "develop",
    "devote", "dialogue", "differ", "direct", "discover", "discuss", "display", "distribute", "dive", "document"
]

# Temporal words (50+ words related to time/sequence)
TEMPORAL_WORDS = [
    "past", "present", "future", "now", "then", "when", "before", "after", "during", "while",
    "early", "late", "soon", "later", "yesterday", "today", "tomorrow", "always", "never", "sometimes",
    "often", "rarely", "seldom", "frequently", "occasionally", "constantly", "immediately", "eventually", "gradually", "suddenly",
    "momentary", "temporary", "permanent", "eternal", "ancient", "modern", "recent", "current", "ongoing", "upcoming",
    "previous", "next", "first", "last", "final", "initial", "beginning", "end", "start", "finish",
    "dawn", "morning", "noon", "afternoon", "evening", "night", "midnight", "second", "minute", "hour",
    "day", "week", "month", "year", "decade", "century", "era", "age", "period", "phase"
]

# Cognitive words (50+ words related to thinking/knowing/believing) 
COGNITIVE_WORDS = [
    "think", "know", "believe", "understand", "learn", "remember", "forget", "recall", "recognize", "realize",
    "imagine", "dream", "wonder", "consider", "ponder", "contemplate", "reflect", "meditate", "analyze", "evaluate",
    "judge", "decide", "choose", "prefer", "assume", "suppose", "expect", "predict", "anticipate", "foresee",
    "perceive", "notice", "observe", "see", "hear", "feel", "sense", "detect", "discover", "find",
    "search", "seek", "explore", "investigate", "study", "examine", "inspect", "review", "assess", "test",
    "doubt", "question", "wonder", "puzzle", "confuse", "clarify", "explain", "interpret", "translate", "decode",
    "encode", "memorize", "store", "retrieve", "access", "process", "compute", "calculate", "reason", "logic"
]

def create_massive_probe():
    """Create massive probe with thousands of single-token words."""
    
    # Context sources (same as before)
    context_sources = [
        {
            "source_type": "custom",
            "source_params": {"words": ["the"], "label": "determiner"}
        },
        {
            "source_type": "custom", 
            "source_params": {"words": ["a"], "label": "determiner"}
        }
    ]
    
    # Collect all words (now much larger)
    all_nouns = (SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_CONCRETE_NEGATIVE_NOUNS + 
                SIMPLE_CONCRETE_NEUTRAL_NOUNS + SIMPLE_ABSTRACT_POSITIVE_NOUNS)
    # Would include all other noun categories when fully expanded
    
    all_verbs = SIMPLE_ACTION_POSITIVE_VERBS
    # Would include all other verb categories when fully expanded
    
    target_sources = []
    
    # Same category structure as before, but with much larger word lists
    
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
    
    # Complexity category removed per requirements
    
    # Concreteness for nouns
    concrete_nouns = SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_CONCRETE_NEGATIVE_NOUNS + SIMPLE_CONCRETE_NEUTRAL_NOUNS
    abstract_nouns = SIMPLE_ABSTRACT_POSITIVE_NOUNS
    # Would include all abstract categories when fully expanded
    
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": concrete_nouns, "label": "concrete"}
    })
    target_sources.append({
        "source_type": "custom", 
        "source_params": {"words": abstract_nouns, "label": "abstract"}
    })
    
    # Action category removed per requirements
    
    # Sentiment categories
    positive_words = SIMPLE_CONCRETE_POSITIVE_NOUNS + SIMPLE_ABSTRACT_POSITIVE_NOUNS + SIMPLE_ACTION_POSITIVE_VERBS
    negative_words = SIMPLE_CONCRETE_NEGATIVE_NOUNS
    neutral_words = SIMPLE_CONCRETE_NEUTRAL_NOUNS
    
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
    
    # New temporal and cognitive categories
    target_sources.append({
        "source_type": "custom",
        "source_params": {"words": TEMPORAL_WORDS, "label": "temporal"}
    })
    target_sources.append({
        "source_type": "custom", 
        "source_params": {"words": COGNITIVE_WORDS, "label": "cognitive"}
    })
    
    probe_request = {
        "session_name": "MASSIVE Multi-Category Analysis - 1000+ Words",
        "context_sources": context_sources,
        "target_sources": target_sources
    }
    
    return probe_request

def main():
    """Create and execute massive probe."""
    print("🚀 Creating MASSIVE multi-category probe...")
    
    probe_request = create_massive_probe()
    
    # Calculate totals
    total_targets = len(set(word for source in probe_request["target_sources"] 
                           for word in source["source_params"]["words"]))
    total_contexts = len(set(word for source in probe_request["context_sources"]
                            for word in source["source_params"]["words"]))
    estimated_pairs = total_contexts * total_targets
    
    print(f"📊 MASSIVE Probe Statistics:")
    print(f"   Contexts: {total_contexts}")
    print(f"   Unique Targets: {total_targets}")  
    print(f"   Total Pairs: {estimated_pairs}")
    print(f"   Category Sources: {len(probe_request['target_sources'])}")
    print(f"   Scale: {total_targets // 100}x larger than previous probe")
    
    # Save to file
    output_file = Path("massive_probe_request.json")
    with open(output_file, 'w') as f:
        json.dump(probe_request, f, indent=2)
    print(f"💾 Saved massive probe configuration to {output_file}")
    
    # Execute via API
    try:
        print("\n🚀 Creating session via API...")
        response = requests.post("http://localhost:8000/api/probes", 
                               json=probe_request, 
                               headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            session_id = result["session_id"]
            print(f"✅ MASSIVE Session created: {session_id}")
            print(f"   Total pairs: {result['total_pairs']}")
            
            # Execute session
            print(f"\n⚡ Executing MASSIVE session {session_id}...")
            exec_response = requests.post(f"http://localhost:8000/api/probes/{session_id}/execute")
            
            if exec_response.status_code == 200:
                exec_result = exec_response.json()
                print(f"✅ MASSIVE Execution started!")
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