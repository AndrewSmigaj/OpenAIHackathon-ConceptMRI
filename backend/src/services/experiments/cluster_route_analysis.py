#!/usr/bin/env python3
"""
Cluster Route Analysis Service - PCA-based clustering for latent space visualization.
Mirrors ExpertRouteAnalysisService structure but uses clustering instead of expert routing.
"""

from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import silhouette_score

from core.parquet_reader import read_records
from schemas.tokens import TokenRecord
from schemas.capture_manifest import CaptureManifest
from schemas.features_pca128 import PCAFeatureRecord


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


class ClusterRouteAnalysisService:
    """Service for analyzing cluster routing patterns from PCA features."""
    
    def __init__(self, data_lake_path: str):
        """Initialize with data lake path."""
        self.data_lake_path = Path(data_lake_path)
    
    def analyze_session_cluster_routes(
        self,
        session_id: str,
        window_layers: List[int],
        clustering_config: Dict[str, Any],
        filter_config: Optional[Dict[str, Any]] = None,
        top_n_routes: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze cluster routes for a capture session within specified window.
        Returns same structure as ExpertRouteAnalysisService.
        """
        # Load session data (PCA features + tokens + manifest)
        pca_records, token_records, manifest = self._load_session_data(session_id)
        
        # Apply filtering if provided
        if filter_config:
            pca_records, token_records = self._apply_filters(
                pca_records, token_records, manifest, filter_config
            )
        
        # Perform clustering for each layer and get cluster assignments
        cluster_assignments = self._perform_clustering(pca_records, window_layers, clustering_config)
        
        # Extract cluster routes for target tokens in specified window (mirrors _extract_target_routes)
        routes = self._extract_target_cluster_routes(cluster_assignments, token_records, window_layers)
        
        # Get top routes first
        top_routes_data = self._analyze_top_routes(routes, top_n_routes)
        
        # Filter routes to only top N for Sankey visualization
        top_route_signatures = {route["signature"] for route in top_routes_data}
        filtered_routes = {sig: routes[sig] for sig in top_route_signatures if sig in routes}
        
        # Build transition matrix and Sankey data with filtered routes (mirrors _build_sankey_data)
        sankey_data = self._build_sankey_data(filtered_routes, token_records, manifest, filter_config)
        
        # Calculate overall statistics
        statistics = self._calculate_statistics(routes, cluster_assignments, window_layers)
        
        return {
            "session_id": session_id,
            "window_layers": window_layers,
            "nodes": sankey_data["nodes"],
            "links": sankey_data["links"],
            "top_routes": top_routes_data,
            "statistics": statistics
        }
    
    def _load_session_data(
        self,
        session_id: str
    ) -> Tuple[List[PCAFeatureRecord], List[TokenRecord], Optional[CaptureManifest]]:
        """Load PCA features, token, and manifest data for a session."""
        session_path = self.data_lake_path / f"session_{session_id}"
        
        if not session_path.exists():
            # Try without prefix
            session_path = self.data_lake_path / session_id
            if not session_path.exists():
                raise ValueError(f"Session {session_id} not found")
        
        # Load PCA feature records
        pca_path = session_path / "features_pca128.parquet"
        if not pca_path.exists():
            raise ValueError(f"PCA features not found for session {session_id}")
        pca_records = read_records(str(pca_path), PCAFeatureRecord)
        
        # Load token records
        tokens_path = session_path / "tokens.parquet"
        token_records = read_records(str(tokens_path), TokenRecord)
        
        # Load manifest (optional for backward compatibility)
        manifest = None
        manifest_path = session_path / "capture_manifest.parquet"
        if manifest_path.exists():
            manifest_records = read_records(str(manifest_path), CaptureManifest)
            manifest = manifest_records[0] if manifest_records else None
        
        return pca_records, token_records, manifest
    
    def _apply_filters(
        self,
        pca_records: List[PCAFeatureRecord],
        token_records: List[TokenRecord],
        manifest: Optional[CaptureManifest],
        filter_config: Dict[str, Any]
    ) -> Tuple[List[PCAFeatureRecord], List[TokenRecord]]:
        """Apply category-based filtering to records (same logic as expert analysis)."""
        if not manifest or not filter_config:
            return pca_records, token_records
        
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
            
            # Check specific context words filter
            if "context_words" in filter_config and filter_config["context_words"]:
                if token.context_text not in filter_config["context_words"]:
                    include = False
            
            # Check specific target words filter
            if "target_words" in filter_config and filter_config["target_words"]:
                if token.target_text not in filter_config["target_words"]:
                    include = False
            
            if include:
                filtered_probe_ids.add(token.probe_id)
        
        # Filter records
        filtered_pca = [r for r in pca_records if r.probe_id in filtered_probe_ids]
        filtered_tokens = [t for t in token_records if t.probe_id in filtered_probe_ids]
        
        return filtered_pca, filtered_tokens
    
    def _perform_clustering(
        self,
        pca_records: List[PCAFeatureRecord],
        window_layers: List[int],
        clustering_config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Perform clustering for each layer. Returns cluster assignments per probe_id."""
        cluster_assignments = {}  # probe_id -> {layer: {cluster_id, distance_to_centroid}}
        
        # Group PCA records by layer
        pca_by_layer = defaultdict(list)
        for record in pca_records:
            if record.token_position == 1:  # Target tokens only
                pca_by_layer[record.layer].append(record)
        
        # Get clustering parameters
        method = clustering_config.get("clustering_method", "kmeans")
        layer_cluster_counts = clustering_config.get("layer_cluster_counts", {})
        pca_dims = clustering_config.get("pca_dimensions", 128)
        
        for layer in window_layers:
            if layer not in pca_by_layer:
                continue
                
            layer_records = pca_by_layer[layer]
            n_clusters = 4
            
            # Extract PCA features matrix
            X = []
            record_lookup = []
            
            for record in layer_records:
                # Use the numpy array directly, truncated to requested dimensions
                feature_vector = record.pca128[:pca_dims].tolist()
                X.append(feature_vector)
                record_lookup.append(record)
            
            X = np.array(X)
            
            if len(X) == 0:
                continue
            
            # Perform clustering
            try:
                if method == "kmeans":
                    clusterer = KMeans(n_clusters=n_clusters, random_state=1, n_init=10)
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = clusterer.cluster_centers_
                    
                elif method == "hierarchical":
                    clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = None
                    
                elif method == "dbscan":
                    clusterer = DBSCAN(eps=0.5, min_samples=5)
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = None
                    
                else:
                    raise ValueError(f"Unknown clustering method: {method}")
                
                # Store cluster assignments
                for idx, record in enumerate(record_lookup):
                    probe_id = record.probe_id
                    cluster_id = int(cluster_labels[idx])
                    
                    # Calculate distance to centroid if available
                    distance_to_centroid = 0.0
                    if centroids is not None and cluster_id >= 0:
                        distance_to_centroid = float(np.linalg.norm(X[idx] - centroids[cluster_id]))
                    
                    if probe_id not in cluster_assignments:
                        cluster_assignments[probe_id] = {}
                    
                    cluster_assignments[probe_id][layer] = {
                        "cluster_id": cluster_id,
                        "distance_to_centroid": distance_to_centroid
                    }
                    
            except Exception as e:
                print(f"❌ Clustering failed for layer {layer}: {e}")
                continue
        
        return cluster_assignments
    
    def _extract_target_cluster_routes(
        self,
        cluster_assignments: Dict[str, Dict[int, Dict[str, Any]]],
        token_records: List[TokenRecord],
        window_layers: List[int]
    ) -> Dict[str, Dict]:
        """Extract cluster routes for target tokens (mirrors _extract_target_routes)."""
        # Create probe to token mapping
        token_by_probe = {t.probe_id: t for t in token_records}
        
        # Extract routes
        routes = defaultdict(lambda: {
            "tokens": [],
            "count": 0,
            "confidence_scores": []
        })
        
        for probe_id, layer_clusters in cluster_assignments.items():
            # Check if we have cluster assignments for all window layers
            if not all(layer in layer_clusters for layer in window_layers):
                continue  # Skip incomplete data
            
            # Build cluster signature (like highway_signature but for clusters)
            signature_parts = []
            distances = []
            for layer in sorted(window_layers):
                cluster_info = layer_clusters[layer]
                cluster_id = cluster_info["cluster_id"]
                signature_parts.append(f"L{layer}C{cluster_id}")
                distances.append(cluster_info["distance_to_centroid"])
            
            signature = "→".join(signature_parts)
            
            # Add to routes
            if probe_id in token_by_probe:
                token = token_by_probe[probe_id]
                routes[signature]["tokens"].append({
                    "context": token.context_text,
                    "target": token.target_text,
                    "probe_id": probe_id
                })
            
            routes[signature]["count"] += 1
            
            # Track "confidence" scores (use inverse of average distance as confidence)
            avg_distance = np.mean(distances) if distances else 0.0
            confidence = 1.0 / (1.0 + avg_distance)  # Higher confidence for lower distance
            routes[signature]["confidence_scores"].append(confidence)
        
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
        """Build Sankey diagram data (mirrors expert version exactly)."""
        # Count transitions and track token flows
        transitions = defaultdict(lambda: defaultdict(int))
        layer_clusters = defaultdict(set)
        cluster_tokens = defaultdict(lambda: defaultdict(list))  # cluster -> category -> tokens
        cluster_context_targets = defaultdict(lambda: defaultdict(set))  # cluster -> context -> targets
        
        # Create token lookup
        token_lookup = {t.probe_id: t for t in token_records}
        
        for signature, route_info in routes.items():
            parts = signature.split("→")
            
            # Track all clusters by layer and collect tokens for each cluster
            for part in parts:
                layer = int(part[1:part.index('C')])
                cluster = int(part[part.index('C')+1:])
                layer_clusters[layer].add(cluster)
                
                # Collect tokens that flow through this cluster
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
                        
                        # Store tokens by category for this cluster
                        for category in target_categories:
                            cluster_tokens[part][category].append({
                                "context": context,
                                "target": target,
                                "probe_id": probe_id
                            })
                        
                        # Track context-target pairs
                        cluster_context_targets[part][context].add(target)
            
            # Count transitions between consecutive parts
            for i in range(len(parts) - 1):
                transitions[parts[i]][parts[i + 1]] += route_info["count"]
        
        # Build enhanced nodes for ECharts (same structure as expert version)
        nodes = []
        
        for layer in sorted(layer_clusters.keys()):
            for cluster in sorted(layer_clusters[layer]):
                node_name = f"L{layer}C{cluster}"
                
                # Aggregate categories and calculate statistics
                all_categories = set()
                category_counts = defaultdict(int)
                total_tokens = 0
                
                cluster_key = node_name
                if cluster_key in cluster_tokens:
                    for category, tokens in cluster_tokens[cluster_key].items():
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
                
                # Generate specialization description (same logic as expert version)
                specialization = self._generate_specialization(dominant_categories, category_counts, total_tokens)
                
                # Build context-target pairs summary
                context_target_pairs = []
                if cluster_key in cluster_context_targets:
                    for context, targets in cluster_context_targets[cluster_key].items():
                        context_target_pairs.append({
                            "context": context,
                            "targets": sorted(list(targets))[:5],  # Limit to top 5
                            "target_count": len(targets)
                        })
                
                nodes.append({
                    "name": node_name,
                    "id": node_name,
                    "layer": layer,
                    "expert_id": cluster,  # Keep field name for compatibility with frontend
                    "token_count": total_tokens,
                    "categories": dominant_categories,
                    "category_distribution": dict(category_counts),
                    "specialization": specialization,
                    "context_target_pairs": context_target_pairs[:3]  # Limit for performance
                })
        
        # Build enhanced links for ECharts with category distributions (same logic as expert version)
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
        """Generate human-readable specialization description for a cluster (same as expert version)."""
        if not dominant_categories or total_tokens == 0:
            return "No clear specialization"
        
        # Get percentages for top categories
        top_category = dominant_categories[0]
        top_percentage = (category_counts[top_category] / total_tokens) * 100
        
        if len(dominant_categories) == 1:
            return f"Clusters {top_category} ({top_percentage:.0f}%)"
        elif len(dominant_categories) == 2:
            second_category = dominant_categories[1] 
            second_percentage = (category_counts[second_category] / total_tokens) * 100
            return f"Groups {top_category} ({top_percentage:.0f}%) and {second_category} ({second_percentage:.0f}%)"
        else:
            # Three categories
            return f"Combines {top_category} ({top_percentage:.0f}%) plus {len(dominant_categories)-1} other types"
    
    def _analyze_top_routes(
        self,
        routes: Dict[str, Dict],
        top_n: int
    ) -> List[Dict[str, Any]]:
        """Get top N most frequent routes with statistics (same as expert version)."""
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
        cluster_assignments: Dict[str, Dict[int, Dict[str, Any]]],
        window_layers: List[int]
    ) -> Dict[str, Any]:
        """Calculate overall statistics for the window (adapted from expert version)."""
        # Count unique probes that have cluster assignments for all window layers
        unique_probes = set()
        for probe_id, layer_clusters in cluster_assignments.items():
            if all(layer in layer_clusters for layer in window_layers):
                unique_probes.add(probe_id)
        
        total_probes = len(unique_probes)
        routes_coverage = sum(r["count"] for r in routes.values()) / total_probes if total_probes > 0 else 0
        
        return {
            "total_routes": len(routes),
            "total_probes": total_probes,
            "routes_coverage": routes_coverage,
            "window_layers": window_layers,
            "avg_route_confidence": float(np.mean([r["avg_confidence"] for r in routes.values()])) if routes else 0
        }

    def get_pca_trajectories(
        self,
        session_id: str,
        layers: List[int],
        n_dims: int = 3,
        filter_config: Optional[Dict[str, Any]] = None,
        max_trajectories: int = 500
    ) -> Dict[str, Any]:
        """
        Get stepped PCA trajectory data for 3D visualization.
        
        Returns PCA coordinates for each probe across specified layers,
        showing how concepts move through the latent space.
        
        Args:
            session_id: Session identifier
            layers: List of layer numbers to include in trajectory
            n_dims: Number of PCA dimensions to return (2, 3, 5, etc.)
            filter_config: Optional filtering (same as route analysis)
            max_trajectories: Maximum number of trajectories to return
            
        Returns:
            {
                "trajectories": [
                    {
                        "probe_id": "...",
                        "context": "...",
                        "target": "...",
                        "coordinates": [
                            {"layer": 0, "x": 0.1, "y": 0.2, "z": 0.3},
                            {"layer": 1, "x": 0.2, "y": 0.3, "z": 0.4},
                            ...
                        ]
                    }
                ],
                "metadata": {"layers": [0,1,2], "n_dims": 3, "total_trajectories": 100}
            }
        """
        # Load session data (reuse existing method)
        pca_records, token_records, manifest = self._load_session_data(session_id)
        
        # Apply filtering if provided (reuse existing method)
        if filter_config:
            pca_records, token_records = self._apply_filters(
                pca_records, token_records, manifest, filter_config
            )
        
        # Group PCA records by probe_id and layer, target token position only
        pca_by_probe = defaultdict(dict)
        for record in pca_records:
            if record.token_position == 1:  # Target tokens only
                pca_by_probe[record.probe_id][record.layer] = record
        
        # Create token lookup for context/target labels
        token_lookup = {r.probe_id: r for r in token_records}
        
        trajectories = []
        probe_count = 0
        
        for probe_id, layer_data in pca_by_probe.items():
            if probe_count >= max_trajectories:
                break
                
            # Check if this probe has data for all requested layers
            if not all(layer in layer_data for layer in layers):
                continue
            
            # Get context and target from token data
            token_record = token_lookup.get(probe_id)
            context = token_record.context_text if token_record else ""
            target = token_record.target_text if token_record else ""
            
            # Build coordinate sequence across layers
            coordinates = []
            for layer in layers:
                pca_record = layer_data[layer]
                pca_features = pca_record.pca128
                
                # Build coordinate dict based on requested dimensions
                coord = {"layer": layer}
                if n_dims >= 1 and len(pca_features) >= 1:
                    coord["x"] = float(pca_features[0])
                if n_dims >= 2 and len(pca_features) >= 2:
                    coord["y"] = float(pca_features[1])
                if n_dims >= 3 and len(pca_features) >= 3:
                    coord["z"] = float(pca_features[2])
                
                # Add additional dimensions if requested
                for i in range(3, min(n_dims, len(pca_features))):
                    coord[f"dim_{i}"] = float(pca_features[i])
                
                coordinates.append(coord)
            
            trajectories.append({
                "probe_id": probe_id,
                "context": context,
                "target": target,
                "coordinates": coordinates
            })
            
            probe_count += 1
        
        return {
            "trajectories": trajectories,
            "metadata": {
                "layers": layers,
                "n_dims": n_dims,
                "total_trajectories": len(trajectories),
                "session_id": session_id,
                "max_requested": max_trajectories
            }
        }