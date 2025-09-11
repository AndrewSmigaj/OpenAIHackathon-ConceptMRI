#!/usr/bin/env python3
"""
Create validated noun complexity probe: 'the' + simple vs complex nouns.
Uses ONLY validated single-token words from comprehensive mining.
"""

import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000/api"

def load_validated_nouns():
    """Load validated single-token nouns from comprehensive mining."""
    
    # Load comprehensive validated words
    pos_file = Path("scripts/comprehensive_pos_words.json")
    with open(pos_file) as f:
        validated_words = json.load(f)
    
    all_nouns = validated_words["nouns"]
    print(f"📚 Loaded {len(all_nouns)} validated single-token nouns")
    
    # Filter for real words (alphabetic, reasonable length, skip numbers/codes)
    real_nouns = [
        word for word in all_nouns 
        if (word.isalpha() and 
            3 <= len(word) <= 15 and
            not word.startswith(('aaa', 'aa', 'aba')))
    ]
    
    # Sort by length to separate simple vs complex
    real_nouns.sort(key=len)
    
    # Take 50 simple (short) and 50 complex (long)
    simple_nouns = real_nouns[:len(real_nouns)//2][:50]
    complex_nouns = real_nouns[len(real_nouns)//2:][-50:]  # Take from end (longest)
    
    print(f"✅ Simple nouns: {len(simple_nouns)} words (avg: {sum(len(w) for w in simple_nouns)/len(simple_nouns):.1f} chars)")
    print(f"   Examples: {simple_nouns[:5]}")
    print(f"✅ Complex nouns: {len(complex_nouns)} words (avg: {sum(len(w) for w in complex_nouns)/len(complex_nouns):.1f} chars)")
    print(f"   Examples: {complex_nouns[:5]}")
    
    return simple_nouns, complex_nouns

def create_validated_noun_complexity_probe():
    """Create probe with validated single-token nouns."""
    
    simple_nouns, complex_nouns = load_validated_nouns()
    
    # Create probe request
    probe_request = {
        "session_name": "Validated Noun Complexity - Simple vs Complex (Single Token)",
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
    print(f"\n🚀 Creating validated noun complexity probe session...")
    print(f"   Context: 1 word (the)")
    print(f"   Targets: {total_words} validated single-token nouns (50 simple + 50 complex)")
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
    probe_request = create_validated_noun_complexity_probe()
    
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
                print(f"   Estimated time: {exec_data.get('estimated_time', 'Processing 100 validated single-token probes across 24 layers')}")
                
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
                            print(f"🎉 Validated noun complexity probe completed successfully!")
                            print(f"   Session ID: {session_id}")
                            print(f"   Ready for expert route analysis with ALL single-token words!")
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
        print(f"   1. All 100 probes should be successful (validated single-token)")
        print(f"   2. Test 2-layer windows for complexity patterns: [0,1], [1,2], [2,3], etc.")
        print(f"   3. Compare simple vs complex noun routing through experts")
        print(f"   4. Session ID: {session_id}")
        print(f"   5. Use expert route analysis API to examine patterns!")