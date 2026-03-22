#!/usr/bin/env python3
"""
Cluster Route Analysis Service - On-demand clustering for latent space visualization.
Loads raw embeddings, reduces dimensionality, then clusters.
"""

from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.decomposition import PCA

from core.parquet_reader import read_records
from schemas.tokens import ProbeRecord
from schemas.capture_manifest import CaptureManifest
import pandas as pd


# Source config: maps source name to parquet filename and column name
SOURCE_CONFIG = {
    "expert_output": {
        "parquet_file": "embeddings.parquet",
        "column": "embedding",
    },
    "residual_stream": {
        "parquet_file": "residual_streams.parquet",
        "column": "residual_stream",
    },
}


class ClusterRouteAnalysisService:
    """Service for analyzing cluster routing patterns from raw embeddings."""

    def __init__(self, data_lake_path: str):
        self.data_lake_path = Path(data_lake_path)

    def analyze_session_cluster_routes(
        self,
        session_id: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        window_layers: List[int] = None,
        clustering_config: Dict[str, Any] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        top_n_routes: int = 20
    ) -> Dict[str, Any]:
        """Analyze cluster routes for one or more capture sessions within specified window."""
        ids = session_ids or ([session_id] if session_id else [])
        if not ids:
            raise ValueError("Must provide session_id or session_ids")

        source = clustering_config.get("embedding_source", "expert_output")
        reduction_method = clustering_config.get("reduction_method", "pca")
        reduction_dims = clustering_config.get("reduction_dimensions", 128)

        # Load raw embeddings and tokens
        embeddings, token_records, manifest = self._load_multi_session_data(ids, source=source)

        # Apply filtering
        if filter_config:
            embeddings, token_records = self._apply_filters(
                embeddings, token_records, filter_config
            )

        # Reduce dimensions, then cluster
        cluster_assignments = self._perform_clustering(
            embeddings, window_layers, clustering_config,
            reduction_method=reduction_method, reduction_dims=reduction_dims
        )

        routes = self._extract_target_cluster_routes(cluster_assignments, token_records, window_layers)

        top_routes_data = self._analyze_top_routes(routes, top_n_routes)

        top_route_signatures = {route["signature"] for route in top_routes_data}
        filtered_routes = {sig: routes[sig] for sig in top_route_signatures if sig in routes}

        sankey_data = self._build_sankey_data(filtered_routes, token_records)

        statistics = self._calculate_statistics(routes, cluster_assignments, window_layers)
        available_axes = self._compute_available_axes(token_records, manifest)

        # Build per-probe cluster assignment map (probe_id -> {layer: cluster_id})
        probe_assignments = {}
        for probe_id, layers in cluster_assignments.items():
            probe_assignments[probe_id] = {
                str(layer): info["cluster_id"]
                for layer, info in layers.items()
            }

        return {
            "session_id": ids[0] if len(ids) == 1 else ",".join(ids[:3]),
            "window_layers": window_layers,
            "nodes": sankey_data["nodes"],
            "links": sankey_data["links"],
            "top_routes": top_routes_data,
            "statistics": statistics,
            "available_axes": available_axes,
            "probe_assignments": probe_assignments,
        }

    def _load_session_data(
        self,
        session_id: str,
        source: str = "expert_output",
    ) -> Tuple[list, List[ProbeRecord], Optional[CaptureManifest]]:
        """Load raw embeddings, tokens, and manifest for a session."""
        session_path = self.data_lake_path / f"session_{session_id}"
        if not session_path.exists():
            session_path = self.data_lake_path / session_id
            if not session_path.exists():
                raise ValueError(f"Session {session_id} not found")

        config = SOURCE_CONFIG.get(source)
        if not config:
            raise ValueError(f"Unknown source '{source}'")

        # Load raw embeddings
        source_path = session_path / config["parquet_file"]
        if not source_path.exists():
            raise FileNotFoundError(f"Source data not found: {source_path}")

        df = pd.read_parquet(source_path)
        column_name = config["column"]

        # Filter to target token position only
        if "token_position" in df.columns:
            df = df[df["token_position"] == 1]

        # Convert to list of dicts for processing
        embedding_records = []
        for _, row in df.iterrows():
            embedding_records.append({
                "probe_id": row["probe_id"],
                "layer": row["layer"],
                "vector": np.array(row[column_name], dtype=np.float32),
            })

        # Load token records
        tokens_path = session_path / "tokens.parquet"
        token_records = read_records(str(tokens_path), ProbeRecord)

        # Load manifest
        manifest = None
        manifest_path = session_path / "capture_manifest.parquet"
        if manifest_path.exists():
            manifest_records = read_records(str(manifest_path), CaptureManifest)
            manifest = manifest_records[0] if manifest_records else None

        return embedding_records, token_records, manifest

    def _load_multi_session_data(
        self,
        session_ids: List[str],
        source: str = "expert_output",
    ) -> Tuple[list, List[ProbeRecord], Optional[CaptureManifest]]:
        """Load and merge data from multiple sessions."""
        all_embeddings = []
        all_tokens = []
        merged_manifest = None

        for sid in session_ids:
            embeddings, tokens, manifest = self._load_session_data(sid, source=source)

            if len(session_ids) > 1:
                prefix = sid[:8] + "_"
                for e in embeddings:
                    e["probe_id"] = prefix + e["probe_id"]
                for t in tokens:
                    t.probe_id = prefix + t.probe_id

            all_embeddings.extend(embeddings)
            all_tokens.extend(tokens)

            if manifest:
                if merged_manifest is None:
                    merged_manifest = manifest
                else:
                    existing = set(merged_manifest.labels)
                    for label in manifest.labels:
                        if label not in existing:
                            merged_manifest.labels.append(label)

        return all_embeddings, all_tokens, merged_manifest

    def _apply_filters(
        self,
        embeddings: list,
        token_records: List[ProbeRecord],
        filter_config: Dict[str, Any]
    ) -> Tuple[list, List[ProbeRecord]]:
        """Apply label-based filtering to records."""
        if not filter_config:
            return embeddings, token_records

        filtered_probe_ids = set()

        for token in token_records:
            include = True

            if "labels" in filter_config and filter_config["labels"]:
                if token.label not in filter_config["labels"]:
                    include = False

            if include:
                filtered_probe_ids.add(token.probe_id)

        filtered_embeddings = [e for e in embeddings if e["probe_id"] in filtered_probe_ids]
        filtered_tokens = [t for t in token_records if t.probe_id in filtered_probe_ids]

        return filtered_embeddings, filtered_tokens

    def _perform_clustering(
        self,
        embeddings: list,
        window_layers: List[int],
        clustering_config: Dict[str, Any],
        reduction_method: str = "pca",
        reduction_dims: int = 128,
    ) -> Dict[str, Dict[str, Any]]:
        """Reduce raw embeddings, then cluster per layer. Returns cluster assignments per probe_id."""
        cluster_assignments = {}

        # Group embeddings by layer
        emb_by_layer = defaultdict(list)
        for record in embeddings:
            emb_by_layer[record["layer"]].append(record)

        clustering_method = clustering_config.get("clustering_method", "kmeans")
        layer_cluster_counts = clustering_config.get("layer_cluster_counts", {})

        for layer in window_layers:
            if layer not in emb_by_layer:
                continue

            layer_records = emb_by_layer[layer]
            n_clusters = layer_cluster_counts.get(str(layer), layer_cluster_counts.get(layer, 4))

            # Build feature matrix from raw embeddings
            X_raw = np.array([r["vector"] for r in layer_records], dtype=np.float32)

            if len(X_raw) == 0:
                continue

            # Reduce dimensionality
            actual_dims = min(reduction_dims, X_raw.shape[0] - 1, X_raw.shape[1])
            if actual_dims < 1:
                actual_dims = 1

            if reduction_method == "umap" and X_raw.shape[0] >= 4:
                try:
                    import umap
                    reducer = umap.UMAP(
                        n_components=actual_dims,
                        random_state=42,
                        n_neighbors=min(15, max(2, X_raw.shape[0] - 1)),
                        min_dist=0.1,
                    )
                    X = reducer.fit_transform(X_raw)
                except Exception:
                    X = PCA(n_components=actual_dims, random_state=42).fit_transform(X_raw)
            else:
                X = PCA(n_components=actual_dims, random_state=42).fit_transform(X_raw)

            # Optionally subset dimensions for clustering
            clustering_dims = clustering_config.get("clustering_dimensions")
            if clustering_dims is not None:
                X = X[:, clustering_dims]

            # Cluster
            try:
                if clustering_method == "kmeans":
                    clusterer = KMeans(n_clusters=min(n_clusters, len(X)), random_state=1, n_init=10)
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = clusterer.cluster_centers_
                elif clustering_method == "hierarchical":
                    clusterer = AgglomerativeClustering(n_clusters=min(n_clusters, len(X)))
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = None
                elif clustering_method == "dbscan":
                    clusterer = DBSCAN(eps=0.5, min_samples=5)
                    cluster_labels = clusterer.fit_predict(X)
                    centroids = None
                else:
                    raise ValueError(f"Unknown clustering method: {clustering_method}")

                for idx, record in enumerate(layer_records):
                    probe_id = record["probe_id"]
                    cluster_id = int(cluster_labels[idx])

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
                print(f"Clustering failed for layer {layer}: {e}")
                continue

        return cluster_assignments

    def _extract_target_cluster_routes(
        self,
        cluster_assignments: Dict[str, Dict[int, Dict[str, Any]]],
        token_records: List[ProbeRecord],
        window_layers: List[int]
    ) -> Dict[str, Dict]:
        """Extract cluster routes for target tokens."""
        token_by_probe = {t.probe_id: t for t in token_records}

        routes = defaultdict(lambda: {
            "tokens": [],
            "count": 0,
            "confidence_scores": []
        })

        for probe_id, layer_clusters in cluster_assignments.items():
            if not all(layer in layer_clusters for layer in window_layers):
                continue

            signature_parts = []
            distances = []
            for layer in sorted(window_layers):
                cluster_info = layer_clusters[layer]
                cluster_id = cluster_info["cluster_id"]
                signature_parts.append(f"L{layer}C{cluster_id}")
                distances.append(cluster_info["distance_to_centroid"])

            signature = "→".join(signature_parts)

            if probe_id in token_by_probe:
                token = token_by_probe[probe_id]
                routes[signature]["tokens"].append({
                    "target_word": token.target_word,
                    "label": token.label,
                    "input_text": token.input_text,
                    "probe_id": probe_id
                })

            routes[signature]["count"] += 1

            avg_distance = np.mean(distances) if distances else 0.0
            confidence = 1.0 / (1.0 + avg_distance)
            routes[signature]["confidence_scores"].append(confidence)

        for signature in routes:
            routes[signature]["avg_confidence"] = float(
                np.mean(routes[signature]["confidence_scores"])
            )
            del routes[signature]["confidence_scores"]

        return dict(routes)

    def _build_sankey_data(
        self,
        routes: Dict[str, Dict],
        token_records: List[ProbeRecord],
    ) -> Dict[str, Any]:
        """Build Sankey diagram data with label-based distributions."""
        transitions = defaultdict(lambda: defaultdict(int))
        layer_clusters = defaultdict(set)
        cluster_label_counts = defaultdict(lambda: defaultdict(int))
        cluster_target_word_counts = defaultdict(lambda: defaultdict(int))
        cluster_category_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        cluster_example_tokens = defaultdict(list)

        token_lookup = {t.probe_id: t for t in token_records}

        for signature, route_info in routes.items():
            parts = signature.split("→")

            for part in parts:
                layer = int(part[1:part.index('C')])
                cluster = int(part[part.index('C')+1:])
                layer_clusters[layer].add(cluster)

                for token_info in route_info["tokens"]:
                    probe_id = token_info["probe_id"]
                    token_record = token_lookup.get(probe_id)
                    if token_record:
                        if token_record.label:
                            cluster_label_counts[part][token_record.label] += 1
                        if token_record.target_word:
                            cluster_target_word_counts[part][token_record.target_word] += 1
                        if token_record.categories_json:
                            cats = json.loads(token_record.categories_json)
                            for axis_id, value in cats.items():
                                cluster_category_counts[part][axis_id][value] += 1
                        if len(cluster_example_tokens[part]) < 10:
                            cluster_example_tokens[part].append({
                                "target_word": token_record.target_word,
                                "label": token_record.label,
                                "input_text": token_record.input_text,
                                "probe_id": probe_id
                            })

            for i in range(len(parts) - 1):
                transitions[parts[i]][parts[i + 1]] += route_info["count"]

        # Build nodes
        nodes = []
        for layer in sorted(layer_clusters.keys()):
            for cluster in sorted(layer_clusters[layer]):
                node_name = f"L{layer}C{cluster}"

                label_dist = dict(cluster_label_counts.get(node_name, {}))
                tw_dist = dict(cluster_target_word_counts.get(node_name, {}))
                cat_dists = {k: dict(v) for k, v in cluster_category_counts.get(node_name, {}).items()}
                total_tokens = sum(label_dist.values())

                specialization = self._generate_specialization(label_dist, total_tokens)

                nodes.append({
                    "name": node_name,
                    "id": node_name,
                    "layer": layer,
                    "expert_id": cluster,  # Kept for frontend compatibility
                    "token_count": total_tokens,
                    "label_distribution": label_dist if label_dist else None,
                    "target_word_distribution": tw_dist if tw_dist else None,
                    "category_distributions": cat_dists if cat_dists else None,
                    "specialization": specialization,
                    "tokens": cluster_example_tokens.get(node_name) or None,
                })

        # Build links
        links = []
        for source in transitions:
            total_from_source = sum(transitions[source].values())
            for target, count in transitions[source].items():
                route_signature = f"{source}→{target}"

                link_label_counts = defaultdict(int)
                link_tw_counts = defaultdict(int)
                link_category_counts = defaultdict(lambda: defaultdict(int))
                link_token_count = 0

                for sig, route_info in routes.items():
                    if sig == route_signature:
                        for token_info in route_info["tokens"]:
                            probe_id = token_info["probe_id"]
                            token_record = token_lookup.get(probe_id)
                            if token_record:
                                link_token_count += 1
                                if token_record.label:
                                    link_label_counts[token_record.label] += 1
                                if token_record.target_word:
                                    link_tw_counts[token_record.target_word] += 1
                                if token_record.categories_json:
                                    cats = json.loads(token_record.categories_json)
                                    for axis_id, value in cats.items():
                                        link_category_counts[axis_id][value] += 1

                link_cat_dists = {k: dict(v) for k, v in link_category_counts.items()}
                links.append({
                    "source": source,
                    "target": target,
                    "value": count,
                    "probability": count / total_from_source if total_from_source > 0 else 0,
                    "route_signature": route_signature,
                    "label_distribution": dict(link_label_counts) if link_label_counts else None,
                    "target_word_distribution": dict(link_tw_counts) if link_tw_counts else None,
                    "category_distributions": link_cat_dists if link_cat_dists else None,
                    "token_count": link_token_count
                })

        return {"nodes": nodes, "links": links}

    def _generate_specialization(
        self,
        label_dist: Dict[str, int],
        total_tokens: int
    ) -> str:
        """Generate human-readable specialization from label distribution."""
        if not label_dist or total_tokens == 0:
            return "No clear specialization"

        sorted_labels = sorted(label_dist.items(), key=lambda x: x[1], reverse=True)

        parts = []
        for label, count in sorted_labels[:3]:
            pct = (count / total_tokens) * 100
            parts.append(f"{label} ({pct:.0f}%)")

        return " / ".join(parts)

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

            unique_examples = {}
            for token in route_info["tokens"]:
                key = f"{token['label']}:{token['probe_id']}"
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
        """Calculate overall statistics for the window."""
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

    def _compute_available_axes(
        self,
        token_records: List[ProbeRecord],
        manifest: Optional[CaptureManifest]
    ) -> List[Dict[str, str]]:
        """Compute available color axes from session data."""
        axes = []

        # Primary label axis
        labels = set()
        for token in token_records:
            if token.label:
                labels.add(token.label)

        if len(labels) >= 2:
            sorted_labels = sorted(labels)
            axes.append({
                "id": "label",
                "label": f"{sorted_labels[0]} vs {sorted_labels[1]}",
                "label_a": sorted_labels[0],
                "label_b": sorted_labels[1],
                "values": sorted_labels,
            })

        # Dynamic category axes from categories_json
        category_values = defaultdict(set)
        for token in token_records:
            if token.categories_json:
                cats = json.loads(token.categories_json)
                for axis_id, value in cats.items():
                    category_values[axis_id].add(value)
        for axis_id, values in sorted(category_values.items()):
            if len(values) >= 2:
                sorted_vals = sorted(values)
                axes.append({
                    "id": axis_id,
                    "label": " / ".join(sorted_vals[:3]) + ("\u2026" if len(sorted_vals) > 3 else ""),
                    "label_a": sorted_vals[0],
                    "label_b": sorted_vals[1],
                    "values": sorted_vals,
                })

        # Target word axis (when multiple target words across sessions)
        target_words = set()
        for token in token_records:
            if token.target_word:
                target_words.add(token.target_word)

        if len(target_words) >= 2:
            sorted_tw = sorted(target_words)
            tw_label = " / ".join(sorted_tw[:3]) + ("…" if len(sorted_tw) > 3 else "")
            axes.append({
                "id": "target_word",
                "label": tw_label,
                "label_a": sorted_tw[0],
                "label_b": sorted_tw[1],
                "values": sorted_tw,
            })

        return axes
