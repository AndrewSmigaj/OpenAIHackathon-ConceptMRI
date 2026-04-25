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
import logging

logger = logging.getLogger(__name__)
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.decomposition import PCA

from core.parquet_reader import read_records
from schemas.tokens import ProbeRecord
from schemas.capture_manifest import CaptureManifest
from services.experiments.route_analysis_common import (
    axis_label, generate_specialization, analyze_top_routes,
    compute_available_axes, build_sankey_links,
)
from services.experiments.token_filters import pick_last_occurrence, subsample_probes
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
        steps: Optional[List[int]] = None,
        top_n_routes: int = 20,
        output_grouping_axes: Optional[List[str]] = None,
        max_examples_per_node: Optional[int] = None,
        last_occurrence_only: bool = False,
        max_probes: Optional[int] = None,
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

        # Filter by sequence step (turn_id or sentence_index)
        if steps:
            step_probe_ids = set()
            for t in token_records:
                step = t.turn_id if t.turn_id is not None else t.sentence_index
                if step in steps:
                    step_probe_ids.add(t.probe_id)
            embeddings = [e for e in embeddings if e["probe_id"] in step_probe_ids]
            token_records = [t for t in token_records if t.probe_id in step_probe_ids]

        # Keep only the last target-word occurrence per (session_id, input_text, target_word)
        if last_occurrence_only:
            keep_ids = pick_last_occurrence(token_records)
            embeddings = [e for e in embeddings if e["probe_id"] in keep_ids]
            token_records = [t for t in token_records if t.probe_id in keep_ids]

        # Deterministic stratified subsample (applied after last_occurrence_only
        # so we pick a representative N of the collapsed set).
        subset = subsample_probes(token_records, max_probes)
        if subset is not None:
            embeddings = [e for e in embeddings if e["probe_id"] in subset]
            token_records = [t for t in token_records if t.probe_id in subset]

        # Reduce dimensions, then cluster
        clustering_result = self._perform_clustering(
            embeddings, window_layers, clustering_config,
            reduction_method=reduction_method, reduction_dims=reduction_dims
        )
        cluster_assignments = clustering_result['assignments']

        # Parallel 3D UMAP fit per layer for the trajectory plot.
        # Same filtered embeddings, same seed; no PCA fallback — fail loud if UMAP fails.
        trajectory_points_by_layer = self._compute_trajectory_points(
            embeddings, token_records, window_layers,
            n_neighbors=clustering_config.get("n_neighbors") or 15,
        )

        routes = self._extract_target_cluster_routes(cluster_assignments, token_records, window_layers)

        top_routes_data = analyze_top_routes(routes, top_n_routes)

        top_route_signatures = {route["signature"] for route in top_routes_data}
        filtered_routes = {sig: routes[sig] for sig in top_route_signatures if sig in routes}

        sankey_data = self._build_sankey_data(filtered_routes, token_records, max_examples=max_examples_per_node)

        # Add output category nodes if any probes have output_category set
        from services.experiments.output_category_nodes import build_output_category_layer
        augmented_nodes, augmented_links, output_axes = build_output_category_layer(
            sankey_data["nodes"], sankey_data["links"],
            filtered_routes, token_records, window_layers,
            output_grouping_axes=output_grouping_axes,
        )
        sankey_data["nodes"] = augmented_nodes
        sankey_data["links"] = augmented_links

        statistics = self._calculate_statistics(routes, cluster_assignments, window_layers)
        available_axes = compute_available_axes(token_records, manifest)

        # Build per-probe cluster assignment map (probe_id -> {layer: cluster_id})
        probe_assignments = {}
        for probe_id, layers in cluster_assignments.items():
            probe_assignments[probe_id] = {
                str(layer): info["cluster_id"]
                for layer, info in layers.items()
            }

        # NOTE: probe_assignments is NOT persisted at the session root any more.
        # The schema-dir copy (written by clustering.py save path) is the single
        # source of truth, and temporal.py reads from it directly.

        return {
            "session_id": ids[0] if len(ids) == 1 else ",".join(ids[:3]),
            "window_layers": window_layers,
            "nodes": sankey_data["nodes"],
            "links": sankey_data["links"],
            "top_routes": top_routes_data,
            "statistics": statistics,
            "available_axes": available_axes,
            "output_available_axes": output_axes if output_axes else None,
            "probe_assignments": probe_assignments,
            "sample_size": len(token_records),
            "_centroids": clustering_result['centroids'],
            "_trajectory_points": trajectory_points_by_layer,
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
        from services.probes.scenario_actions import enrich_records_with_scenario_actions
        from services.probes.tick_log_enrichment import enrich_records_with_tick_log
        enrich_records_with_scenario_actions(token_records, session_path)
        enrich_records_with_tick_log(token_records, session_path)

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
    ) -> Dict[str, Any]:
        """Reduce raw embeddings, then cluster per layer.

        Returns dict with:
            'assignments': {probe_id: {layer: {cluster_id, distance_to_centroid}}}
            'centroids': {layer: {cluster_id: ndarray}} — in reduced space
            'reducers': {layer: fitted_model} — fitted PCA/UMAP for transforming new data
        """
        cluster_assignments = {}
        centroids_by_layer = {}
        reducers_by_layer = {}

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

            # Reduce dimensionality — capture fitted model in all branches
            actual_dims = min(reduction_dims, X_raw.shape[0] - 1, X_raw.shape[1])
            if actual_dims < 1:
                actual_dims = 1

            if reduction_method == "umap" and X_raw.shape[0] >= 4:
                try:
                    import umap
                    requested_nn = clustering_config.get("n_neighbors") or 15
                    fitted_reducer = umap.UMAP(
                        n_components=actual_dims,
                        random_state=42,
                        n_neighbors=max(2, min(requested_nn, X_raw.shape[0] - 1)),
                        min_dist=0.1,
                    )
                    X = fitted_reducer.fit_transform(X_raw)
                except Exception:
                    fitted_reducer = PCA(n_components=actual_dims, random_state=42)
                    X = fitted_reducer.fit_transform(X_raw)
            else:
                fitted_reducer = PCA(n_components=actual_dims, random_state=42)
                X = fitted_reducer.fit_transform(X_raw)

            reducers_by_layer[layer] = fitted_reducer

            # Optionally subset dimensions for clustering
            clustering_dims = clustering_config.get("clustering_dimensions")
            if clustering_dims is not None:
                X = X[:, clustering_dims]

            # Cluster
            try:
                if clustering_method == "kmeans":
                    clusterer = KMeans(n_clusters=min(n_clusters, len(X)), random_state=1, n_init=10)
                    cluster_labels = clusterer.fit_predict(X)
                elif clustering_method == "hierarchical":
                    clusterer = AgglomerativeClustering(n_clusters=min(n_clusters, len(X)))
                    cluster_labels = clusterer.fit_predict(X)
                elif clustering_method == "dbscan":
                    clusterer = DBSCAN(eps=0.5, min_samples=5)
                    cluster_labels = clusterer.fit_predict(X)
                else:
                    raise ValueError(f"Unknown clustering method: {clustering_method}")

                # Compute centroids as mean of reduced vectors per cluster
                layer_centroids = {}
                for cid in set(cluster_labels):
                    if cid < 0:  # skip DBSCAN noise
                        continue
                    mask = cluster_labels == cid
                    layer_centroids[int(cid)] = X[mask].mean(axis=0)
                centroids_by_layer[layer] = layer_centroids

                for idx, record in enumerate(layer_records):
                    probe_id = record["probe_id"]
                    cluster_id = int(cluster_labels[idx])

                    distance_to_centroid = 0.0
                    if cluster_id in layer_centroids:
                        distance_to_centroid = float(np.linalg.norm(X[idx] - layer_centroids[cluster_id]))

                    if probe_id not in cluster_assignments:
                        cluster_assignments[probe_id] = {}

                    cluster_assignments[probe_id][layer] = {
                        "cluster_id": cluster_id,
                        "distance_to_centroid": distance_to_centroid
                    }

            except Exception as e:
                logger.error(f"Clustering failed for layer {layer}: {e}")
                continue

        return {
            'assignments': cluster_assignments,
            'centroids': centroids_by_layer,
            'reducers': reducers_by_layer,
        }

    def _compute_trajectory_points(
        self,
        embeddings: list,
        token_records: List[ProbeRecord],
        window_layers: List[int],
        n_neighbors: int = 15,
    ) -> Dict[int, list]:
        """Fit a 3D UMAP per layer for the trajectory plot.

        Same filtered embeddings as the clustering, same seed (42). No PCA
        fallback — if UMAP fails for a layer, raise. The 3D coords would be
        silently miscalibrated relative to the 6D-clustered space if we fell
        back, so the trajectory plot must use UMAP-3D or nothing.

        Returns: {layer: [{probe_id, x, y, z, label, target_word, step,
                           categories_json}, ...]}
        """
        import umap

        token_lookup = {t.probe_id: t for t in token_records}

        emb_by_layer = defaultdict(list)
        for record in embeddings:
            emb_by_layer[record["layer"]].append(record)

        trajectory_by_layer: Dict[int, list] = {}

        for layer in window_layers:
            if layer not in emb_by_layer:
                continue
            layer_records = emb_by_layer[layer]
            if not layer_records:
                continue

            X_raw = np.array([r["vector"] for r in layer_records], dtype=np.float32)
            if X_raw.shape[0] < 4:
                # UMAP requires at least 4 samples to fit reliably.
                logger.warning(f"Skipping trajectory points for layer {layer}: only {X_raw.shape[0]} samples")
                continue

            reducer_3d = umap.UMAP(
                n_components=3,
                random_state=42,
                n_neighbors=max(2, min(n_neighbors, X_raw.shape[0] - 1)),
                min_dist=0.1,
            )
            X_3d = reducer_3d.fit_transform(X_raw)

            points = []
            for idx, record in enumerate(layer_records):
                pid = record["probe_id"]
                tok = token_lookup.get(pid)
                step = None
                label = None
                target_word = None
                categories_json = None
                if tok is not None:
                    turn_id = getattr(tok, 'turn_id', None)
                    step = turn_id if turn_id is not None else getattr(tok, 'sentence_index', None)
                    label = getattr(tok, 'label', None)
                    target_word = getattr(tok, 'target_word', None)
                    categories_json = getattr(tok, 'categories_json', None)
                points.append({
                    "probe_id": pid,
                    "x": float(X_3d[idx, 0]),
                    "y": float(X_3d[idx, 1]),
                    "z": float(X_3d[idx, 2]),
                    "label": label,
                    "target_word": target_word,
                    "step": step,
                    "categories_json": categories_json,
                })

            trajectory_by_layer[int(layer)] = points

        return trajectory_by_layer

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
        max_examples: Optional[int] = None,
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
                        if max_examples is None or len(cluster_example_tokens[part]) < max_examples:
                            turn_id = getattr(token_record, 'turn_id', None)
                            cluster_example_tokens[part].append({
                                "target_word": token_record.target_word,
                                "label": token_record.label,
                                "input_text": token_record.input_text,
                                "probe_id": probe_id,
                                "generated_text": getattr(token_record, 'generated_text', None),
                                "output_category": getattr(token_record, 'output_category', None),
                                "target_char_offset": getattr(token_record, 'target_char_offset', None),
                                "turn_id": turn_id,
                                "step": turn_id if turn_id is not None else getattr(token_record, 'sentence_index', None),
                                "game_text": getattr(token_record, 'game_text', None),
                                "analysis": getattr(token_record, 'analysis', None),
                                "action": getattr(token_record, 'action', None),
                                "system_prompt": getattr(token_record, 'system_prompt', None),
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

                specialization = generate_specialization(label_dist, total_tokens)

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

        links = build_sankey_links(transitions, routes, token_lookup, max_examples=max_examples)

        return {"nodes": nodes, "links": links}

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
