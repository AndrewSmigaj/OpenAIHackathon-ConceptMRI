#!/usr/bin/env python3
"""
Create 'very' + adjectives/adverbs probe for POS comparison.
Uses ONLY validated single-token words from comprehensive mining.
"""

import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000/api"

def load_validated_adjectives_adverbs():
    """Load validated single-token adjectives and adverbs."""
    
    # Load comprehensive validated words
    pos_file = Path("scripts/comprehensive_pos_words.json")
    with open(pos_file) as f:
        validated_words = json.load(f)
    
    # Get adjectives (combine regular adjectives + adjective_satellites)
    all_adjectives = validated_words["adjectives"] + validated_words["adjective_satellites"]
    all_adverbs = validated_words["adverbs"]
    
    print(f"📚 Loaded {len(all_adjectives)} validated adjectives + {len(all_adverbs)} validated adverbs")
    
    # Filter for real words (skip numbers, weird codes)
    real_adjectives = [
        word for word in all_adjectives 
        if (word.isalpha() and 
            len(word) >= 3 and
            not word.startswith(('aaa', 'aa', 'aba')))
    ]
    
    real_adverbs = [
        word for word in all_adverbs 
        if (word.isalpha() and 
            len(word) >= 3 and
            not word.startswith(('aaa', 'aa', 'aba')))
    ]
    
    # Take 50 of each (or as many as available)
    selected_adjectives = real_adjectives[:50]
    selected_adverbs = real_adverbs[:50]
    
    print(f"✅ Selected adjectives: {len(selected_adjectives)} words")
    print(f"   Examples: {selected_adjectives[:8]}")
    print(f"✅ Selected adverbs: {len(selected_adverbs)} words")
    print(f"   Examples: {selected_adverbs[:8]}")
    
    return selected_adjectives, selected_adverbs

def create_very_pos_probe():
    """Create probe with 'very' + adjectives/adverbs for POS comparison."""
    
    adjectives, adverbs = load_validated_adjectives_adverbs()
    
    # Create probe request
    probe_request = {
        "session_name": "Very POS Comparison - Adjectives vs Adverbs (Single Token)",
        "context_sources": [
            {
                "source_type": "custom",
                "source_params": {
                    "words": ["very"],
                    "category": "intensifier"
                }
            }
        ],
        "target_sources": [
            {
                "source_type": "custom",
                "source_params": {
                    "words": adjectives,
                    "category": "adjectives"
                }
            },
            {
                "source_type": "custom", 
                "source_params": {
                    "words": adverbs,
                    "category": "adverbs"
                }
            }
        ],
        "layers": list(range(24))  # All 24 layers: [0, 1, 2, ..., 23]
    }
    
    total_words = len(adjectives) + len(adverbs)
    print(f"\n🚀 Creating 'very' POS comparison probe session...")
    print(f"   Context: 1 word (very)")
    print(f"   Targets: {total_words} validated single-token words ({len(adjectives)} adj + {len(adverbs)} adv)")
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
    probe_request = create_very_pos_probe()
    
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
                print(f"   Estimated time: {exec_data.get('estimated_time', 'Processing validated single-token POS probes across 24 layers')}")
                
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
                            print(f"🎉 'Very' POS comparison probe completed successfully!")
                            print(f"   Session ID: {session_id}")
                            print(f"   Ready for expert route analysis comparing adjective vs adverb routing!")
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
        print(f"   1. All probes should be successful (validated single-token)")
        print(f"   2. Test 2-layer windows for POS routing patterns: [0,1], [1,2], [2,3], etc.")
        print(f"   3. Compare adjective vs adverb routing through experts")
        print(f"   4. Session ID: {session_id}")
        print(f"   5. Use expert route analysis API to examine POS-based patterns!")