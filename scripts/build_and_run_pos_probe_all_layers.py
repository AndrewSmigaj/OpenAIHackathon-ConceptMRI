#!/usr/bin/env python3
"""
Build and run the POS probe with manually selected common words - ALL LAYERS.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def build_pos_probe_all_layers():
    """Create the POS probe with manually selected words and all layers."""
    
    # Manually selected common words (50 each category)
    selected_words = {
        "nouns": [
            "ability", "absence", "academy", "accuracy", "achievement", "acre", "activity", "actor", 
            "addition", "agency", "agenda", "agent", "agreement", "airport", "album", "algorithm", 
            "alignment", "allocation", "alphabet", "altar", "america", "americana", "ammunition", 
            "analysis", "ancestor", "anger", "animal", "anniversary", "answer", "anxiety", 
            "apartment", "appearance", "application", "appointment", "approval", "argument", 
            "arrangement", "arrival", "article", "assignment", "assistance", "association", 
            "assumption", "atmosphere", "attention", "attraction", "audience", "authority", 
            "availability", "background", "balance"
        ],
        
        "verbs": [
            "accept", "activate", "adapt", "adjust", "affirm", "agree", "align", "allow", 
            "alter", "announce", "appear", "append", "apply", "appoint", "approve", "ask", 
            "assemble", "assert", "assign", "attach", "avoid", "beg", "bring", "bury", 
            "calculate", "choose", "commit", "compile", "compose", "configure", "connect", 
            "consider", "contain", "continue", "contribute", "convert", "create", "decide", 
            "declare", "define", "deliver", "demonstrate", "describe", "design", "develop", 
            "discover", "display", "distribute", "document", "establish"
        ],
        
        "adjectives": [
            "aware", "digital", "finite", "illegal", "many", "minimal", "random", "solar", 
            "urban", "viral", "adaptive", "analytic", "angular", "avoidable", "biotic", 
            "boolean", "continuous", "eligible", "existent", "financial", "inclusive", 
            "modifiable", "mutable", "optional", "postal", "racial", "renal", "semantic", 
            "successful", "undefined", "unexpected", "unsigned", "vascular", "vedic", 
            "allergenic", "continental", "cutaneous", "doctoral", "forgettable", "immutable", 
            "intestinal", "ovine", "phonic", "precedented", "tractive", "unsupported", 
            "utile"
        ],
        
        "adverbs": [
            "again", "also", "always", "below", "but", "ever", "maybe", "never", "not", 
            "oft", "often", "once", "soon", "too", "yet", "ably", "afar", "along", 
            "around", "before", "fully", "quite", "rather", "really", "actually", 
            "already", "almost", "currently", "finally", "however", "mostly", "perhaps", 
            "usually", "actively", "especially", "formerly", "hopefully", "normally", 
            "possibly", "probably", "sometimes", "typically", "fortunately", "necessarily", 
            "particularly", "approximately", "conditionally", "implicitly"
        ]
    }
    
    # Create probe request with ALL layers (GPT-OSS-20B has 24 layers: 0-23)
    probe_request = {
        "session_name": "POS Analysis - Manual Selection ALL LAYERS",
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
                    "words": selected_words["nouns"],
                    "category": "nouns"
                }
            },
            {
                "source_type": "custom", 
                "source_params": {
                    "words": selected_words["verbs"],
                    "category": "verbs"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected_words["adjectives"],
                    "category": "adjectives"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected_words["adverbs"],
                    "category": "adverbs"
                }
            }
        ],
        "layers": list(range(24))  # All 24 layers: [0, 1, 2, ..., 23]
    }
    
    total_words = sum(len(words) for words in selected_words.values())
    print(f"🚀 Creating POS probe session with ALL LAYERS...")
    print(f"   Context: 1 word (determiner)")
    print(f"   Targets: {total_words} manually selected common words")
    print(f"   Categories: 4 POS types (nouns, verbs, adjectives, adverbs)")
    print(f"   Layers: ALL 24 layers (0-23)")
    print(f"   Total probes: {total_words}")
    
    return probe_request

def create_and_run_probe():
    """Create the probe session and execute it."""
    
    # Check server
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code != 200:
            print("❌ API server not responding")
            return None
    except:
        print("❌ Cannot connect to API server - start with: cd backend/src && uvicorn api.main:app --reload")
        return None
    
    # Build probe
    probe_request = build_pos_probe_all_layers()
    
    try:
        # Create session
        print("\n🎯 Creating probe session...")
        response = requests.post(
            f"{API_BASE}/probes",
            json=probe_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data['session_id']
            print(f"✅ Session created: {session_id}")
            print(f"   Total pairs: {data['total_pairs']}")
            
            # Show categories
            print(f"   Categories:")
            for category, words in data['categories']['targets'].items():
                print(f"     {category:12}: {len(words):2d} words")
            
            # Execute immediately
            print(f"\n🚀 Executing probe session...")
            exec_response = requests.post(f"{API_BASE}/probes/{session_id}/execute")
            
            if exec_response.status_code == 200:
                exec_data = exec_response.json()
                print(f"✅ Execution started!")
                print(f"   Estimated time: {exec_data.get('estimated_time', 'This will take longer with 24 layers')}")
                
                # Monitor progress
                print(f"\n⏳ Monitoring progress (this will take a while with all layers)...")
                while True:
                    status_response = requests.get(f"{API_BASE}/probes/{session_id}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        state = status_data['state']
                        progress = status_data['progress']
                        
                        completed = progress.get('completed', 0)
                        total = progress.get('total', 0)
                        percent = (completed / total * 100) if total > 0 else 0
                        
                        print(f"   Status: {state} - {completed}/{total} ({percent:.1f}%)")
                        
                        if state == 'completed':
                            print(f"🎉 Probe session completed successfully!")
                            print(f"   Session ID: {session_id}")
                            print(f"   Ready for expert route analysis with ANY layer window!")
                            return session_id
                        elif state == 'failed':
                            print(f"❌ Probe session failed")
                            return None
                        
                        time.sleep(15)  # Wait 15 seconds (longer for big session)
                    else:
                        print(f"❌ Failed to check status")
                        return None
            else:
                print(f"❌ Failed to execute session: {exec_response.status_code}")
                print(f"   Response: {exec_response.text}")
                return session_id  # Return session_id even if execution failed
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    session_id = create_and_run_probe()
    if session_id:
        print(f"\n✨ Next steps with ALL LAYERS available:")
        print(f"   1. Test any 2-layer window: [0,1], [5,6], [10,11], [20,21], etc.")
        print(f"   2. Test any 3-layer window: [0,1,2], [10,11,12], [21,22,23], etc.")  
        print(f"   3. Session ID: {session_id}")
        print(f"   4. Much richer analysis possibilities!")