#!/usr/bin/env python3
"""
Test script to analyze expert routes from session data.
Loads routing Parquet files and computes expert route statistics.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend" / "src"))

from core.parquet_reader import read_records
from schemas.routing import RoutingRecord, highway_signature
from schemas.tokens import TokenRecord
from collections import defaultdict
import numpy as np
from typing import List, Dict, Tuple
import json


def load_session_data(session_id: str) -> Tuple[List[RoutingRecord], List[TokenRecord]]:
    """Load routing and token records for a session."""
    session_path = Path(f"data/lake/session_{session_id}")
    
    if not session_path.exists():
        raise ValueError(f"Session path not found: {session_path}")
    
    # Load routing records
    routing_path = session_path / "routing.parquet"
    routing_records = read_records(str(routing_path), RoutingRecord)
    
    # Load token records for context
    tokens_path = session_path / "tokens.parquet"
    token_records = read_records(str(tokens_path), TokenRecord)
    
    print(f"Loaded {len(routing_records)} routing records")
    print(f"Loaded {len(token_records)} token records")
    
    return routing_records, token_records


def extract_expert_routes(routing_records: List[RoutingRecord], 
                         token_records: List[TokenRecord]) -> Dict[str, Dict]:
    """
    Extract expert routes for target tokens (position=1).
    Returns mapping of route signatures to token information.
    """
    # Group routing records by probe_id
    routing_by_probe = defaultdict(list)
    for record in routing_records:
        routing_by_probe[record.probe_id].append(record)
    
    # Create probe_id to token mapping
    token_by_probe = {t.probe_id: t for t in token_records}
    
    # Extract routes for target tokens
    routes = defaultdict(lambda: {"tokens": [], "count": 0, "avg_confidence": []})
    
    for probe_id, probe_routing in routing_by_probe.items():
        # Filter to target token only (position=1)
        target_routing = [r for r in probe_routing if r.token_position == 1]
        
        if not target_routing:
            continue
            
        # Sort by layer
        target_routing.sort(key=lambda r: r.layer)
        
        # Generate route signature (e.g., "L6E2→L7E15→L8E7")
        try:
            signature = highway_signature(target_routing, target_tokens_only=True)
        except ValueError as e:
            print(f"Skipping probe {probe_id}: {e}")
            continue
        
        # Get token information
        if probe_id in token_by_probe:
            token_info = token_by_probe[probe_id]
            routes[signature]["tokens"].append({
                "context": token_info.context_text,
                "target": token_info.target_text
            })
        
        routes[signature]["count"] += 1
        
        # Calculate average confidence for this route
        avg_conf = np.mean([r.routing_confidence() for r in target_routing])
        routes[signature]["avg_confidence"].append(avg_conf)
    
    # Finalize statistics
    for signature in routes:
        routes[signature]["avg_confidence"] = float(np.mean(routes[signature]["avg_confidence"]))
    
    return dict(routes)


def build_transition_matrix(routes: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Build transition probability matrix P(E_l+1 | E_l) from route data.
    Returns nodes and edges for Sankey visualization.
    """
    # Count transitions between experts at consecutive layers
    transitions = defaultdict(lambda: defaultdict(int))
    layer_experts = defaultdict(set)
    
    for signature, route_info in routes.items():
        # Parse signature (e.g., "L6E2→L7E15→L8E7")
        parts = signature.split("→")
        
        for i in range(len(parts) - 1):
            source = parts[i]  # e.g., "L6E2"
            target = parts[i + 1]  # e.g., "L7E15"
            
            # Extract layer and expert info
            source_layer = int(source[1:source.index('E')])
            source_expert = int(source[source.index('E')+1:])
            target_layer = int(target[1:target.index('E')])
            target_expert = int(target[target.index('E')+1:])
            
            layer_experts[source_layer].add(source_expert)
            layer_experts[target_layer].add(target_expert)
            
            # Count this transition weighted by route frequency
            transitions[source][target] += route_info["count"]
    
    # Build nodes list for Sankey
    nodes = []
    node_index = {}
    idx = 0
    
    for layer in sorted(layer_experts.keys()):
        for expert in sorted(layer_experts[layer]):
            node_name = f"L{layer}E{expert}"
            nodes.append({
                "name": node_name,
                "layer": layer,
                "expert": expert
            })
            node_index[node_name] = idx
            idx += 1
    
    # Build edges list with probabilities
    links = []
    for source in transitions:
        total_from_source = sum(transitions[source].values())
        for target, count in transitions[source].items():
            probability = count / total_from_source if total_from_source > 0 else 0
            links.append({
                "source": node_index[source],
                "target": node_index[target],
                "value": count,
                "probability": probability
            })
    
    return {
        "nodes": nodes,
        "links": links,
        "statistics": {
            "total_routes": len(routes),
            "unique_experts": len(nodes),
            "total_transitions": len(links)
        }
    }


def analyze_top_routes(routes: Dict[str, Dict], top_n: int = 10) -> List[Dict]:
    """Analyze and return top N most frequent routes."""
    # Sort routes by frequency
    sorted_routes = sorted(
        routes.items(), 
        key=lambda x: x[1]["count"], 
        reverse=True
    )[:top_n]
    
    total_count = sum(r["count"] for _, r in routes.items())
    
    top_routes = []
    for signature, route_info in sorted_routes:
        coverage = route_info["count"] / total_count if total_count > 0 else 0
        
        # Get unique token examples (up to 5)
        unique_tokens = {}
        for token in route_info["tokens"][:20]:  # Look at more to find unique
            key = f"{token['context']}→{token['target']}"
            if key not in unique_tokens:
                unique_tokens[key] = token
            if len(unique_tokens) >= 5:
                break
        
        top_routes.append({
            "signature": signature,
            "count": route_info["count"],
            "coverage": coverage,
            "avg_confidence": route_info["avg_confidence"],
            "example_tokens": list(unique_tokens.values())
        })
    
    return top_routes


def main():
    # Test with existing session
    session_id = "cd2361b6"
    
    print(f"\n{'='*60}")
    print(f"Expert Route Analysis for Session {session_id}")
    print(f"{'='*60}\n")
    
    # Load data
    routing_records, token_records = load_session_data(session_id)
    
    # Extract expert routes
    print("\nExtracting expert routes for target tokens...")
    routes = extract_expert_routes(routing_records, token_records)
    print(f"Found {len(routes)} unique expert routes")
    
    # Analyze top routes
    print("\nTop 10 Expert Routes:")
    print("-" * 40)
    top_routes = analyze_top_routes(routes, top_n=10)
    
    for i, route in enumerate(top_routes, 1):
        print(f"\n{i}. {route['signature']}")
        print(f"   Count: {route['count']} ({route['coverage']:.1%} coverage)")
        print(f"   Avg Confidence: {route['avg_confidence']:.3f}")
        print(f"   Examples:")
        for ex in route['example_tokens'][:3]:
            print(f"     - {ex['context']} → {ex['target']}")
    
    # Build transition matrix
    print("\n\nBuilding transition probability matrix...")
    sankey_data = build_transition_matrix(routes)
    
    print(f"\nSankey Visualization Data:")
    print(f"  - {len(sankey_data['nodes'])} expert nodes")
    print(f"  - {len(sankey_data['links'])} transitions")
    print(f"  - {sankey_data['statistics']['total_routes']} total routes")
    
    # Sample some transitions
    print("\nTop 5 Transitions by Frequency:")
    sorted_links = sorted(sankey_data['links'], key=lambda x: x['value'], reverse=True)[:5]
    for link in sorted_links:
        source_node = sankey_data['nodes'][link['source']]
        target_node = sankey_data['nodes'][link['target']]
        print(f"  {source_node['name']} → {target_node['name']}: "
              f"{link['value']} ({link['probability']:.1%})")
    
    # Save sample data for frontend testing
    sample_output = {
        "session_id": session_id,
        "top_routes": top_routes[:5],
        "sankey_data": {
            "nodes": sankey_data["nodes"][:20],  # Sample nodes
            "links": sankey_data["links"][:30],  # Sample links
        },
        "statistics": sankey_data["statistics"]
    }
    
    output_file = Path("scripts/sample_expert_routes.json")
    with open(output_file, "w") as f:
        json.dump(sample_output, f, indent=2)
    print(f"\nSample data saved to {output_file}")


if __name__ == "__main__":
    main()