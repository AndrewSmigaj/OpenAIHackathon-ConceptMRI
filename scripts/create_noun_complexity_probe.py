#!/usr/bin/env python3
"""
Create probe for noun complexity experiment: 'the' + simple nouns vs complex nouns.
100 probes total (50 simple + 50 complex nouns).
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def create_noun_complexity_probe():
    """Create probe with 'the' + 50 simple + 50 complex nouns."""
    
    # Manually selected common nouns - 50 simple, 50 complex
    simple_nouns = [
        "car", "door", "food", "water", "fire", "sun", "moon", "tree", "bird", "fish",
        "house", "ball", "hand", "foot", "head", "eye", "ear", "nose", "face", "arm",
        "book", "chair", "table", "bed", "room", "wall", "road", "park", "shop", "game",
        "cat", "dog", "baby", "man", "woman", "boy", "girl", "mother", "father", "friend",
        "apple", "bread", "milk", "cake", "tea", "cup", "plate", "knife", "fork", "spoon"
    ]
    
    complex_nouns = [
        "architecture", "philosophy", "technology", "democracy", "government", "education", "communication",
        "administration", "organization", "investigation", "development", "implementation", "achievement", "measurement",
        "establishment", "arrangement", "requirement", "environment", "management", "advertisement", "entertainment",
        "relationship", "opportunity", "responsibility", "understanding", "performance", "temperature", "information",
        "population", "generation", "destination", "imagination", "conversation", "celebration", "preparation",
        "consideration", "recommendation", "representation", "transformation", "collaboration", "concentration",
        "demonstration", "specification", "documentation", "configuration", "authorization", "authentication",
        "multiplication", "construction", "destruction"
    ]
    
    # Verify we have exactly 50 each
    assert len(simple_nouns) == 50, f"Need 50 simple nouns, got {len(simple_nouns)}"
    assert len(complex_nouns) == 50, f"Need 50 complex nouns, got {len(complex_nouns)}"
    
    print(f"✅ Simple nouns: {len(simple_nouns)} words (avg: {sum(len(w) for w in simple_nouns)/len(simple_nouns):.1f} chars)")
    print(f"   Examples: {simple_nouns[:5]}")
    print(f"✅ Complex nouns: {len(complex_nouns)} words (avg: {sum(len(w) for w in complex_nouns)/len(complex_nouns):.1f} chars)")
    print(f"   Examples: {complex_nouns[:5]}")
    
    # Create probe request
    probe_request = {
        "session_name": "Noun Complexity Experiment - Simple vs Complex",
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
                    "words": simple_nouns,
                    "category": "simple_nouns"
                }
            },
            {
                "source_type": "custom", 
                "source_params": {
                    "words": complex_nouns,
                    "category": "complex_nouns"
                }
            }
        ],
        "layers": list(range(24))  # All 24 layers: [0, 1, 2, ..., 23]
    }
    
    total_words = len(simple_nouns) + len(complex_nouns)
    print(f"\n🚀 Creating noun complexity probe session...")
    print(f"   Context: 1 word (the)")
    print(f"   Targets: {total_words} nouns (50 simple + 50 complex)")
    print(f"   Layers: ALL 24 layers (0-23)")
    print(f"   Total probes: {total_words}")
    
    return probe_request

def create_and_run_probe():
    """Create the probe session and execute it."""
    
    # Check server
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            print("❌ API server not responding")
            return None
        print("✅ API server is healthy")
    except:
        print("❌ Cannot connect to API server")
        return None
    
    # Build probe
    probe_request = create_noun_complexity_probe()
    
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
                print(f"     {category:15}: {len(words):2d} words")
            
            # Execute immediately
            print(f"\n🚀 Executing probe session...")
            exec_response = requests.post(f"{API_BASE}/probes/{session_id}/execute")
            
            if exec_response.status_code == 200:
                exec_data = exec_response.json()
                print(f"✅ Execution started!")
                print(f"   Estimated time: {exec_data.get('estimated_time', 'Processing 100 probes across 24 layers')}")
                
                # Monitor progress
                print(f"\n⏳ Monitoring progress...")
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
                            print(f"🎉 Noun complexity probe completed successfully!")
                            print(f"   Session ID: {session_id}")
                            print(f"   Ready for expert route analysis!")
                            return session_id
                        elif state == 'failed':
                            print(f"❌ Probe session failed")
                            return None
                        
                        time.sleep(10)  # Check every 10 seconds
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
        print(f"\n✨ Next steps:")
        print(f"   1. Test 2-layer windows for complexity patterns: [0,1], [1,2], [2,3], etc.")
        print(f"   2. Compare simple vs complex noun routing through experts")
        print(f"   3. Session ID: {session_id}")
        print(f"   4. Use expert route analysis API to examine patterns!")