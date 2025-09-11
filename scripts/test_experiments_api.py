#!/usr/bin/env python3
"""
Test script for the experiments API endpoints.
"""

import requests
import json
import sys
from typing import Dict, Any

# API base URL
API_BASE = "http://localhost:8000/api"

def test_health_check():
    """Test the health check endpoint."""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{API_BASE}/experiments/health")
        if response.status_code == 200:
            print("✅ Health check passed:", response.json())
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed with error: {e}")
        return False

def test_analyze_routes(session_id: str = "cd2361b6"):
    """Test the analyze routes endpoint."""
    print(f"\n🔍 Testing analyze routes for session {session_id}...")
    
    request_body = {
        "session_id": session_id,
        "window_layers": [0, 1, 2],
        "filter_config": None,
        "top_n_routes": 10
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/experiments/analyze-routes",
            json=request_body,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Route analysis succeeded!")
            print(f"   - Found {data['statistics']['total_routes']} unique routes")
            print(f"   - {len(data['nodes'])} nodes, {len(data['links'])} links")
            print(f"   - Top route: {data['top_routes'][0]['signature']} ({data['top_routes'][0]['count']} occurrences)")
            return data
        else:
            print(f"❌ Route analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Route analysis failed with error: {e}")
        return None

def test_route_details(session_id: str, route_signature: str):
    """Test the route details endpoint."""
    print(f"\n🔍 Testing route details for {route_signature}...")
    
    # URL encode the signature to handle the → character
    import urllib.parse
    encoded_signature = urllib.parse.quote(route_signature)
    
    try:
        url = f"{API_BASE}/experiments/route-details"
        params = {
            "session_id": session_id,
            "signature": route_signature,  # Don't encode here, requests will handle it
            "window_layers": "0,1,2"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Route details succeeded!")
            print(f"   - Route: {data['signature']}")
            print(f"   - Count: {data['count']}, Coverage: {data['coverage']:.1%}")
            print(f"   - Tokens: {len(data['tokens'])} examples")
            if data['tokens']:
                print(f"   - Example: {data['tokens'][0]['context']} → {data['tokens'][0]['target']}")
            return True
        else:
            print(f"❌ Route details failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Route details failed with error: {e}")
        return False

def test_expert_details(session_id: str, layer: int = 0, expert_id: int = 18):
    """Test the expert details endpoint."""
    print(f"\n🔍 Testing expert details for L{layer}E{expert_id}...")
    
    try:
        url = f"{API_BASE}/experiments/expert-details"
        params = {
            "session_id": session_id,
            "layer": layer,
            "expert_id": expert_id
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Expert details succeeded!")
            print(f"   - Expert: {data['node_name']}")
            print(f"   - Total tokens: {data['total_tokens']}")
            print(f"   - Usage rate: {data['usage_rate']:.1%}")
            print(f"   - Avg confidence: {data['avg_confidence']:.3f}")
            if data['tokens']:
                print(f"   - Example tokens: {', '.join([t['target'] for t in data['tokens'][:5]])}")
            return True
        else:
            print(f"❌ Expert details failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Expert details failed with error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Experiments API Endpoints")
    print("=" * 50)
    
    # Test health check first
    if not test_health_check():
        print("\n❌ Health check failed - is the server running?")
        print("Start server with: uvicorn api.main:app --reload")
        sys.exit(1)
    
    session_id = "cd2361b6"
    
    # Test route analysis
    route_data = test_analyze_routes(session_id)
    if not route_data:
        print("\n❌ Route analysis failed - check session data")
        sys.exit(1)
    
    # Test route details with the top route
    if route_data['top_routes']:
        top_route_signature = route_data['top_routes'][0]['signature']
        test_route_details(session_id, top_route_signature)
    
    # Test expert details with the first node
    if route_data['nodes']:
        first_node = route_data['nodes'][0]
        test_expert_details(session_id, first_node['layer'], first_node['expert'])
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main()