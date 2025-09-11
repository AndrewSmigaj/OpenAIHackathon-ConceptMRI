#!/usr/bin/env python3
"""
Create a new probe session with POS-pure words for better categorical analysis.
"""

import requests
import json
from pathlib import Path

# API base URL
API_BASE = "http://localhost:8000/api"

def create_pos_probe_session():
    """Create a probe session with POS-pure target words."""
    
    # Load the mined words
    pos_words_file = Path("scripts/pos_mined_words.json")
    if not pos_words_file.exists():
        print("❌ Run mine_pos_categories.py first to generate word lists")
        return None
    
    with open(pos_words_file) as f:
        pos_words = json.load(f)
    
    # Select good words from each category (avoiding weird ones)
    selected_words = {
        "nouns": ["achievement", "application", "communication", "delivery", "entity", 
                 "event", "implementation", "knowledge", "location", "person"],
        "verbs": ["continue", "deliver", "develop", "expect", "expire", 
                 "extend", "generate", "operate", "receive", "reduce"],
        "adjectives": ["adaptive", "analytic", "digital", "existent"] + ["precedented"],  # Only 5 good ones
        "adverbs": ["again", "already", "always", "approximately", "fortunately", 
                   "fully", "never", "often", "quite", "really"]
    }
    
    # Create the probe request
    probe_request = {
        "session_name": "POS Categories Analysis - Pure Words",
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
                    "category": "pure_nouns"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected_words["verbs"], 
                    "category": "pure_verbs"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected_words["adjectives"],
                    "category": "pure_adjectives"
                }
            },
            {
                "source_type": "custom",
                "source_params": {
                    "words": selected_words["adverbs"],
                    "category": "pure_adverbs"
                }
            }
        ],
        "layers": [0, 1, 2]  # Same layers as before for comparison
    }
    
    print("🚀 Creating POS probe session...")
    print(f"   Context: 1 word (determiner)")
    print(f"   Targets: {len(selected_words['nouns']) + len(selected_words['verbs']) + len(selected_words['adjectives']) + len(selected_words['adverbs'])} words across 4 POS categories")
    print(f"   Total pairs: {1 * (len(selected_words['nouns']) + len(selected_words['verbs']) + len(selected_words['adjectives']) + len(selected_words['adverbs']))}")
    
    try:
        response = requests.post(
            f"{API_BASE}/probes",
            json=probe_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Probe session created!")
            print(f"   Session ID: {data['session_id']}")
            print(f"   Total pairs: {data['total_pairs']}")
            print(f"   Categories: {list(data['categories']['targets'].keys())}")
            
            # Show word distribution
            print(f"\n📊 Target word distribution:")
            for category, words in data['categories']['targets'].items():
                print(f"   {category:15}: {len(words):2d} words - {words[:5]}{'...' if len(words) > 5 else ''}")
            
            return data['session_id']
            
        else:
            print(f"❌ Failed to create probe session: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating probe session: {e}")
        return None

def execute_probe_session(session_id: str):
    """Execute the probe session."""
    if not session_id:
        return False
        
    print(f"\n🎯 Executing probe session {session_id}...")
    
    try:
        response = requests.post(f"{API_BASE}/probes/{session_id}/execute")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Execution started!")
            print(f"   Status URL: {data['status_url']}")
            print(f"   Estimated time: {data.get('estimated_time', 'Unknown')}")
            print(f"\n⏳ Monitor execution with:")
            print(f"   curl {API_BASE}/probes/{session_id}/status")
            return True
        else:
            print(f"❌ Failed to execute session: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error executing session: {e}")
        return False

def main():
    """Create and optionally execute POS probe session."""
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code != 200:
            print("❌ API server not responding - start with: uvicorn api.main:app --reload")
            return
    except:
        print("❌ Cannot connect to API server - start with: uvicorn api.main:app --reload")
        return
    
    # Create session
    session_id = create_pos_probe_session()
    
    if session_id:
        # Ask if user wants to execute
        response = input(f"\n🤔 Execute probe session now? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            execute_probe_session(session_id)
        else:
            print(f"💾 Session created but not executed.")
            print(f"   Execute later with: curl -X POST {API_BASE}/probes/{session_id}/execute")

if __name__ == "__main__":
    main()