#!/usr/bin/env python3
"""
Expert Route Analysis Service.
Analyzes expert routing patterns from captured MoE data for visualization.
"""

from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import numpy as np

from core.parquet_reader import read_records
from schemas.routing import RoutingRecord, highway_signature
from schemas.tokens import TokenRecord
from schemas.capture_manifest import CaptureManifest


# Simple category axis pairs for percentage calculations
CATEGORY_AXES = {
    "grammatical": ["nouns", "verbs"],
    "sentiment": ["positive", "negative", "neutral"],
    "abstraction": ["concrete", "abstract"],
    "conceptual": ["temporal", "cognitive"],
}

# Reverse mapping for quick lookup
CATEGORY_TO_AXIS = {}
for axis_name, categories in CATEGORY_AXES.items():
    for cat in categories:
        CATEGORY_TO_AXIS[cat] = axis_name


class ExpertRouteAnalysisService:
    """Service for analyzing expert routing patterns from probe captures."""
    
    def __init__(self, data_lake_path: str):
        """Initialize with data lake path."""
        self.data_lake_path = Path(data_lake_path)
    
    def analyze_session_routes(
        self,
        session_id: str,
        window_layers: List[int],
        filter_config: Optional[Dict[str, Any]] = None,
        top_n_routes: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze expert routes for a capture session within specified window.
        
        Args:
            session_id: Capture session ID
            window_layers: List of layers to analyze (e.g., [0, 1, 2])
            filter_config: Optional filtering by categories
            top_n_routes: Number of top routes to return
            
        Returns:
            Dictionary with Sankey visualization data and statistics
        """
        # Load session data
        routing_records, token_records, manifest = self._load_session_data(session_id)
        
        # Apply filtering if provided
        if filter_config:
            routing_records, token_records = self._apply_filters(
                routing_records, token_records, manifest, filter_config
            )
        
        # Extract expert routes for target tokens in specified window
        routes = self._extract_target_routes(routing_records, token_records, window_layers)
        
        # Get top routes first
        top_routes_data = self._analyze_top_routes(routes, top_n_routes)
        
        # Filter routes to only top N for Sankey visualization
        top_route_signatures = {route["signature"] for route in top_routes_data}
        filtered_routes = {sig: routes[sig] for sig in top_route_signatures if sig in routes}
        
        # Build transition matrix and Sankey data with filtered routes
        sankey_data = self._build_sankey_data(filtered_routes, token_records, manifest, filter_config)
        
        # Calculate overall statistics
        statistics = self._calculate_statistics(routes, routing_records, window_layers)
        
        return {
            "session_id": session_id,
            "window_layers": window_layers,
            "nodes": sankey_data["nodes"],
            "links": sankey_data["links"],
            "top_routes": top_routes_data,
            "statistics": statistics
        }
    
    def get_route_details(
        self,
        session_id: str,
        route_signature: str,
        window_layers: List[int]
    ) -> Dict[str, Any]:
        """Get detailed information about a specific expert route."""
        # Load session data
        routing_records, token_records, manifest = self._load_session_data(session_id)
        
        # Extract routes for the same window
        routes = self._extract_target_routes(routing_records, token_records, window_layers)
        
        # Find the specific route
        if route_signature not in routes:
            raise ValueError(f"Route {route_signature} not found in session {session_id}")
        
        route_info = routes[route_signature]
        category_breakdown = self._get_category_breakdown(route_info["tokens"], manifest)
        
        total_tokens = len(token_records)
        coverage = len(route_info["tokens"]) / total_tokens if total_tokens > 0 else 0
        
        return {
            "signature": route_signature,
            "window_layers": window_layers,
            "tokens": route_info["tokens"],
            "count": route_info["count"],
            "coverage": coverage,
            "avg_confidence": route_info["avg_confidence"],
            "category_breakdown": category_breakdown
        }
    
    def get_expert_details(
        self,
        session_id: str,
        layer: int,
        expert_id: int
    ) -> Dict[str, Any]:
        """Get details about a specific expert's specialization."""
        # Load session data
        routing_records, token_records, manifest = self._load_session_data(session_id)
        
        # Find all tokens routed through this expert
        expert_tokens = []
        confidence_scores = []
        
        for record in routing_records:
            if (record.layer == layer and 
                record.token_position == 1 and  # Target tokens only
                record.expert_top1_id == expert_id):
                
                # Find corresponding token
                token = next((t for t in token_records if t.probe_id == record.probe_id), None)
                if token:
                    expert_tokens.append({
                        "context": token.context_text,
                        "target": token.target_text
                    })
                    confidence_scores.append(record.expert_top1_weight)
        
        # Get category breakdown and statistics
        category_breakdown = self._get_category_breakdown(expert_tokens, manifest)
        
        total_target_tokens = sum(1 for r in routing_records if r.token_position == 1 and r.layer == layer)
        usage_rate = len(expert_tokens) / total_target_tokens if total_target_tokens > 0 else 0
        
        return {
            "layer": layer,
            "expert_id": expert_id,
            "node_name": f"L{layer}E{expert_id}",
            "tokens": expert_tokens[:20],  # Sample of tokens
            "total_tokens": len(expert_tokens),
            "usage_rate": usage_rate,
            "avg_confidence": float(np.mean(confidence_scores)) if confidence_scores else 0,
            "category_breakdown": category_breakdown
        }
    
    def _load_session_data(
        self,
        session_id: str
    ) -> Tuple[List[RoutingRecord], List[TokenRecord], Optional[CaptureManifest]]:
        """Load routing, token, and manifest data for a session."""
        session_path = self.data_lake_path / f"session_{session_id}"
        
        if not session_path.exists():
            # Try without prefix
            session_path = self.data_lake_path / session_id
            if not session_path.exists():
                raise ValueError(f"Session {session_id} not found")
        
        # Load routing records
        routing_path = session_path / "routing.parquet"
        routing_records = read_records(str(routing_path), RoutingRecord)
        
        # Load token records
        tokens_path = session_path / "tokens.parquet"
        token_records = read_records(str(tokens_path), TokenRecord)
        
        # Load manifest (optional for backward compatibility)
        manifest = None
        manifest_path = session_path / "capture_manifest.parquet"
        if manifest_path.exists():
            manifest_records = read_records(str(manifest_path), CaptureManifest)
            manifest = manifest_records[0] if manifest_records else None
        
        return routing_records, token_records, manifest
    
    def _apply_filters(
        self,
        routing_records: List[RoutingRecord],
        token_records: List[TokenRecord],
        manifest: Optional[CaptureManifest],
        filter_config: Dict[str, Any]
    ) -> Tuple[List[RoutingRecord], List[TokenRecord]]:
        """Apply category-based filtering to records."""
        print(f"🔍 _apply_filters called with filter_config: {filter_config}")
        
        if not manifest or not filter_config:
            print("🔍 No filtering applied - returning all records")
            return routing_records, token_records
        
        print(f"🔍 Starting filtering with {len(token_records)} token records")
        filtered_probe_ids = set()
        
        for token in token_records:
            include = True
            
            # Check context category filter
            if "context_categories" in filter_config and filter_config["context_categories"]:
                context_cats = manifest.context_category_assignments.get(token.context_text, [])
                if not any(cat in filter_config["context_categories"] for cat in context_cats):
                    include = False
            
            # Check target category filter
            if "target_categories" in filter_config and filter_config["target_categories"]:
                target_cats = manifest.target_category_assignments.get(token.target_text, [])
                if not any(cat in filter_config["target_categories"] for cat in target_cats):
                    include = False
            
            # Check specific context words filter (NEW)
            if "context_words" in filter_config and filter_config["context_words"]:
                if token.context_text not in filter_config["context_words"]:
                    include = False
            
            # Check specific target words filter (NEW)
            if "target_words" in filter_config and filter_config["target_words"]:
                if token.target_text not in filter_config["target_words"]:
                    include = False
            
            if include:
                filtered_probe_ids.add(token.probe_id)
        
        # Filter records
        filtered_routing = [r for r in routing_records if r.probe_id in filtered_probe_ids]
        filtered_tokens = [t for t in token_records if t.probe_id in filtered_probe_ids]
        
        return filtered_routing, filtered_tokens
    
    def _extract_target_routes(
        self,
        routing_records: List[RoutingRecord],
        token_records: List[TokenRecord],
        window_layers: List[int]
    ) -> Dict[str, Dict]:
        """Extract expert routes for target tokens within specified window layers."""
        # Group routing by probe_id
        routing_by_probe = defaultdict(list)
        for record in routing_records:
            routing_by_probe[record.probe_id].append(record)
        
        # Create probe to token mapping
        token_by_probe = {t.probe_id: t for t in token_records}
        
        # Extract routes
        routes = defaultdict(lambda: {
            "tokens": [],
            "count": 0,
            "confidence_scores": []
        })
        
        for probe_id, probe_routing in routing_by_probe.items():
            # Get target token (position=1) for specified window layers
            target_routing = [
                r for r in probe_routing 
                if r.token_position == 1 and r.layer in window_layers
            ]
            
            # Should have exactly len(window_layers) records
            if len(target_routing) != len(window_layers):
                continue  # Skip incomplete data
            
            # Sort by layer and generate route signature
            target_routing.sort(key=lambda r: r.layer)
            
            try:
                signature = highway_signature(target_routing, target_tokens_only=True)
            except ValueError:
                continue
            
            # Add to routes
            if probe_id in token_by_probe:
                token = token_by_probe[probe_id]
                routes[signature]["tokens"].append({
                    "context": token.context_text,
                    "target": token.target_text,
                    "probe_id": probe_id
                })
            
            routes[signature]["count"] += 1
            
            # Track confidence scores
            avg_conf = np.mean([r.routing_confidence() for r in target_routing])
            routes[signature]["confidence_scores"].append(avg_conf)
        
        # Calculate average confidence
        for signature in routes:
            routes[signature]["avg_confidence"] = float(
                np.mean(routes[signature]["confidence_scores"])
            )
            del routes[signature]["confidence_scores"]
        
        return dict(routes)
    
    def _build_sankey_data(
        self, 
        routes: Dict[str, Dict],
        token_records: List[TokenRecord],
        manifest: CaptureManifest,
        filter_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Build enhanced Sankey diagram data with category aggregation."""
        # Count transitions and track token flows
        transitions = defaultdict(lambda: defaultdict(int))
        layer_experts = defaultdict(set)
        expert_tokens = defaultdict(lambda: defaultdict(list))  # expert -> category -> tokens
        expert_context_targets = defaultdict(lambda: defaultdict(set))  # expert -> context -> targets
        
        # Create token lookup
        token_lookup = {t.probe_id: t for t in token_records}
        
        for signature, route_info in routes.items():
            parts = signature.split("→")
            
            # Track all experts by layer and collect tokens for each expert
            for part in parts:
                layer = int(part[1:part.index('E')])
                expert = int(part[part.index('E')+1:])
                layer_experts[layer].add(expert)
                
                # Collect tokens that flow through this expert
                for token_info in route_info["tokens"]:
                    probe_id = token_info["probe_id"]
                    token_record = token_lookup.get(probe_id)
                    if token_record:
                        context = token_record.context_text
                        target = token_record.target_text
                        
                        # Get categories for target token, filtered if config provided
                        target_categories = manifest.target_category_assignments.get(target, [])
                        
                        # Filter categories based on filter_config if present
                        if filter_config and "target_categories" in filter_config and filter_config["target_categories"]:
                            target_categories = [cat for cat in target_categories if cat in filter_config["target_categories"]]
                        
                        # Store tokens by category for this expert
                        for category in target_categories:
                            expert_tokens[part][category].append({
                                "context": context,
                                "target": target,
                                "probe_id": probe_id
                            })
                        
                        # Track context-target pairs
                        expert_context_targets[part][context].add(target)
            
            # Count transitions between consecutive parts
            for i in range(len(parts) - 1):
                transitions[parts[i]][parts[i + 1]] += route_info["count"]
        
        # Build enhanced nodes for ECharts
        nodes = []
        node_index = {}
        
        for layer in sorted(layer_experts.keys()):
            for expert in sorted(layer_experts[layer]):
                node_name = f"L{layer}E{expert}"
                
                # Aggregate categories and calculate statistics
                all_categories = set()
                category_counts = defaultdict(int)
                total_tokens = 0
                
                expert_key = node_name
                if expert_key in expert_tokens:
                    for category, tokens in expert_tokens[expert_key].items():
                        all_categories.add(category)
                        category_counts[category] = len(tokens)
                        total_tokens += len(tokens)
                
                # Get most common categories (top 3)
                top_categories = sorted(
                    category_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:3]
                dominant_categories = [cat for cat, count in top_categories if count > 0]
                
                # Generate specialization description
                specialization = self._generate_specialization(dominant_categories, category_counts, total_tokens)
                
                # Calculate axis-based distributions
                axis_distributions = {}
                for axis_name, axis_categories in CATEGORY_AXES.items():
                    axis_counts = {cat: category_counts.get(cat, 0) for cat in axis_categories}
                    axis_total = sum(axis_counts.values())
                    if axis_total > 0:
                        axis_percentages = {cat: (count/axis_total)*100 for cat, count in axis_counts.items() if count > 0}
                        if axis_percentages:
                            axis_distributions[axis_name] = axis_percentages
                
                # Build context-target pairs summary
                context_target_pairs = []
                if expert_key in expert_context_targets:
                    for context, targets in expert_context_targets[expert_key].items():
                        context_target_pairs.append({
                            "context": context,
                            "targets": sorted(list(targets))[:5],  # Limit to top 5
                            "target_count": len(targets)
                        })
                
                nodes.append({
                    "name": node_name,
                    "id": node_name,
                    "layer": layer,
                    "expert_id": expert,
                    "token_count": total_tokens,
                    "categories": dominant_categories,
                    "category_distribution": dict(category_counts),
                    "axis_distributions": axis_distributions,
                    "specialization": specialization,
                    "context_target_pairs": context_target_pairs[:3]  # Limit for performance
                })
                node_index[node_name] = len(nodes) - 1
        
        # Build enhanced links for ECharts with category distributions
        links = []
        for source in transitions:
            total_from_source = sum(transitions[source].values())
            for target, count in transitions[source].items():
                # Generate route signature for this link
                route_signature = f"{source}→{target}"
                
                # Calculate category distribution for this specific route
                route_category_counts = defaultdict(int)
                route_token_count = 0
                
                # Find all tokens that use this specific route
                for signature, route_info in routes.items():
                    if signature == route_signature:
                        for token_info in route_info["tokens"]:
                            probe_id = token_info["probe_id"]
                            token_record = token_lookup.get(probe_id)
                            if token_record:
                                target_text = token_record.target_text
                                
                                # Get categories for target token, filtered if config provided
                                target_categories = manifest.target_category_assignments.get(target_text, [])
                                
                                # Apply same filtering as nodes
                                if filter_config and "target_categories" in filter_config and filter_config["target_categories"]:
                                    target_categories = [cat for cat in target_categories if cat in filter_config["target_categories"]]
                                
                                # Count categories for this route
                                for category in target_categories:
                                    route_category_counts[category] += 1
                                    route_token_count += 1
                
                links.append({
                    "source": source,
                    "target": target,
                    "value": count,
                    "probability": count / total_from_source if total_from_source > 0 else 0,
                    "route_signature": route_signature,
                    "category_distribution": dict(route_category_counts),
                    "token_count": route_token_count
                })
        
        return {"nodes": nodes, "links": links}
    
    def _generate_specialization(
        self, 
        dominant_categories: List[str], 
        category_counts: Dict[str, int], 
        total_tokens: int
    ) -> str:
        """Generate human-readable specialization description with axis-aware percentages."""
        if not dominant_categories or total_tokens == 0:
            return "No clear specialization"
        
        # Group categories by axis for proper percentage calculation
        axis_groups = defaultdict(lambda: {"categories": {}, "total": 0})
        
        for category, count in category_counts.items():
            if category in CATEGORY_TO_AXIS:
                axis = CATEGORY_TO_AXIS[category]
                axis_groups[axis]["categories"][category] = count
                axis_groups[axis]["total"] += count
        
        # Build description parts for each axis
        descriptions = []
        
        for axis_name in ["grammatical", "sentiment", "abstraction", "conceptual"]:
            if axis_name not in axis_groups:
                continue
                
            axis_data = axis_groups[axis_name]
            if axis_data["total"] == 0:
                continue
            
            # Get dominant category in this axis
            dominant = max(axis_data["categories"].items(), key=lambda x: x[1])
            percentage = (dominant[1] / axis_data["total"]) * 100
            
            # Only include if significant
            if percentage > 60:
                descriptions.append(f"{dominant[0]} ({percentage:.0f}%)")
        
        if not descriptions:
            # Fall back to global percentages if no clear axis dominance
            top_category = dominant_categories[0]
            top_percentage = (category_counts[top_category] / total_tokens) * 100
            return f"Mixed: {top_category} ({top_percentage:.0f}%)"
        
        return " & ".join(descriptions)
    
    def _analyze_top_routes(
        self,
        routes: Dict[str, Dict],
        top_n: int
    ) -> List[Dict[str, Any]]:
        """Get top N most frequent routes with statistics."""
        sorted_routes = sorted(
            routes.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:top_n]
        
        total_count = sum(r["count"] for _, r in routes.items())
        
        top_routes = []
        for signature, route_info in sorted_routes:
            coverage = route_info["count"] / total_count if total_count > 0 else 0
            
            # Get unique examples (up to 5)
            unique_examples = {}
            for token in route_info["tokens"]:
                key = f"{token['context']}→{token['target']}"
                if key not in unique_examples:
                    unique_examples[key] = token
                if len(unique_examples) >= 5:
                    break
            
            top_routes.append({
                "signature": signature,
                "count": route_info["count"],
                "coverage": coverage,
                "avg_confidence": route_info["avg_confidence"],
                "example_tokens": list(unique_examples.values())
            })
        
        return top_routes
    
    def _calculate_statistics(
        self,
        routes: Dict[str, Dict],
        routing_records: List[RoutingRecord],
        window_layers: List[int]
    ) -> Dict[str, Any]:
        """Calculate overall statistics for the window."""
        # Count unique probes in the window
        unique_probes = set()
        for record in routing_records:
            if record.token_position == 1 and record.layer in window_layers:
                unique_probes.add(record.probe_id)
        
        total_probes = len(unique_probes)
        routes_coverage = sum(r["count"] for r in routes.values()) / total_probes if total_probes > 0 else 0
        
        return {
            "total_routes": len(routes),
            "total_probes": total_probes,
            "routes_coverage": routes_coverage,
            "window_layers": window_layers,
            "avg_route_confidence": float(np.mean([r["avg_confidence"] for r in routes.values()])) if routes else 0
        }
    
    def _get_category_breakdown(
        self,
        tokens: List[Dict[str, str]],
        manifest: Optional[CaptureManifest]
    ) -> Dict[str, Any]:
        """Get category breakdown for a set of tokens."""
        if not manifest:
            return {}
        
        context_categories = defaultdict(int)
        target_categories = defaultdict(int)
        
        for token in tokens:
            # Count context categories
            if manifest.context_category_assignments:
                context_cats = manifest.context_category_assignments.get(token["context"], [])
                for cat in context_cats:
                    context_categories[cat] += 1
            
            # Count target categories
            if manifest.target_category_assignments:
                target_cats = manifest.target_category_assignments.get(token["target"], [])
                for cat in target_cats:
                    target_categories[cat] += 1
        
        return {
            "context_categories": dict(context_categories),
            "target_categories": dict(target_categories)
        }