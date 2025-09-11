#!/usr/bin/env python3
"""
Direct test of the expert route analysis service.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend" / "src"))

from services.experiments.expert_route_analysis import ExpertRouteAnalysisService

def test_service():
    """Test the service directly."""
    print("🔍 Testing ExpertRouteAnalysisService directly...")
    
    # Initialize service
    data_lake_path = Path(__file__).parent.parent / "data" / "lake"
    service = ExpertRouteAnalysisService(str(data_lake_path))
    
    session_id = "cd2361b6"
    window_layers = [0, 1, 2]
    
    try:
        # Test route analysis
        print(f"Analyzing routes for session {session_id} with window {window_layers}...")
        result = service.analyze_session_routes(
            session_id=session_id,
            window_layers=window_layers,
            filter_config=None,
            top_n_routes=5
        )
        
        print(f"✅ Analysis succeeded!")
        print(f"   - Session: {result['session_id']}")
        print(f"   - Window: {result['window_layers']}")
        print(f"   - Total routes: {result['statistics']['total_routes']}")
        print(f"   - Total probes: {result['statistics']['total_probes']}")
        print(f"   - Routes coverage: {result['statistics']['routes_coverage']:.1%}")
        print(f"   - Nodes: {len(result['nodes'])}, Links: {len(result['links'])}")
        
        if result['top_routes']:
            print(f"\nTop routes:")
            for i, route in enumerate(result['top_routes'], 1):
                print(f"   {i}. {route['signature']} - {route['count']} ({route['coverage']:.1%})")
        
        # Test route details
        if result['top_routes']:
            top_route = result['top_routes'][0]
            print(f"\nTesting route details for: {top_route['signature']}")
            
            details = service.get_route_details(
                session_id=session_id,
                route_signature=top_route['signature'],
                window_layers=window_layers
            )
            
            print(f"✅ Route details succeeded!")
            print(f"   - Count: {details['count']}")
            print(f"   - Coverage: {details['coverage']:.1%}")
            print(f"   - Tokens: {len(details['tokens'])}")
            if details['tokens']:
                print(f"   - Example: {details['tokens'][0]['context']} → {details['tokens'][0]['target']}")
        
        # Test expert details
        if result['nodes']:
            first_node = result['nodes'][0]
            print(f"\nTesting expert details for: {first_node['name']}")
            
            expert_details = service.get_expert_details(
                session_id=session_id,
                layer=first_node['layer'],
                expert_id=first_node['expert']
            )
            
            print(f"✅ Expert details succeeded!")
            print(f"   - Node: {expert_details['node_name']}")
            print(f"   - Total tokens: {expert_details['total_tokens']}")
            print(f"   - Usage rate: {expert_details['usage_rate']:.1%}")
            print(f"   - Avg confidence: {expert_details['avg_confidence']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_service():
        print("\n🎉 Service test passed!")
    else:
        print("\n❌ Service test failed!")
        sys.exit(1)