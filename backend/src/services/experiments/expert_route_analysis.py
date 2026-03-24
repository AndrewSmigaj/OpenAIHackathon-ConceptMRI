#!/usr/bin/env python3
"""
Expert Route Analysis Service.
Analyzes expert routing patterns from captured MoE data for visualization.
"""

from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import json
import numpy as np

from core.parquet_reader import read_records
from schemas.routing import RoutingRecord, highway_signature
from schemas.tokens import ProbeRecord
from schemas.capture_manifest import CaptureManifest


def _axis_label(axis_id: str, sorted_values: list) -> str:
    """Generate a display label for a color axis based on its cardinality."""
    if len(sorted_values) == 2:
        return f"{sorted_values[0]} vs {sorted_values[1]}"
    return f"{axis_id} ({len(sorted_values)} groups)"


class ExpertRouteAnalysisService:
    """Service for analyzing expert routing patterns from probe captures."""

    def __init__(self, data_lake_path: str):
        self.data_lake_path = Path(data_lake_path)

    def analyze_session_routes(
        self,
        session_id: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        window_layers: List[int] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        top_n_routes: int = 20,
        output_grouping_axes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Analyze expert routes for one or more capture sessions within specified window."""
        ids = session_ids or ([session_id] if session_id else [])
        if not ids:
            raise ValueError("Must provide session_id or session_ids")

        routing_records, token_records, manifest = self._load_multi_session_data(ids)

        if filter_config:
            routing_records, token_records = self._apply_filters(
                routing_records, token_records, filter_config
            )

        routes = self._extract_target_routes(routing_records, token_records, window_layers)

        top_routes_data = self._analyze_top_routes(routes, top_n_routes)

        top_route_signatures = {route["signature"] for route in top_routes_data}
        filtered_routes = {sig: routes[sig] for sig in top_route_signatures if sig in routes}

        sankey_data = self._build_sankey_data(filtered_routes, token_records)

        # Add output category nodes if any probes have output_category set
        from services.experiments.output_category_nodes import build_output_category_layer
        augmented_nodes, augmented_links, output_axes = build_output_category_layer(
            sankey_data["nodes"], sankey_data["links"],
            filtered_routes, token_records, window_layers,
            output_grouping_axes=output_grouping_axes,
        )
        sankey_data["nodes"] = augmented_nodes
        sankey_data["links"] = augmented_links

        statistics = self._calculate_statistics(routes, routing_records, window_layers)
        available_axes = self._compute_available_axes(token_records, manifest)

        return {
            "session_id": ids[0] if len(ids) == 1 else ",".join(ids[:3]),
            "window_layers": window_layers,
            "nodes": sankey_data["nodes"],
            "links": sankey_data["links"],
            "top_routes": top_routes_data,
            "statistics": statistics,
            "available_axes": available_axes,
            "output_available_axes": output_axes if output_axes else None,
        }

    def get_route_details(
        self,
        session_id: str,
        route_signature: str,
        window_layers: List[int]
    ) -> Dict[str, Any]:
        """Get detailed information about a specific expert route."""
        routing_records, token_records, manifest = self._load_session_data(session_id)

        routes = self._extract_target_routes(routing_records, token_records, window_layers)

        if route_signature not in routes:
            raise ValueError(f"Route {route_signature} not found in session {session_id}")

        route_info = routes[route_signature]
        category_breakdown = self._get_label_breakdown(route_info["tokens"], token_records)

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
        routing_records, token_records, manifest = self._load_session_data(session_id)

        expert_tokens = []
        confidence_scores = []

        for record in routing_records:
            if (record.layer == layer and
                record.token_position == 1 and
                record.expert_top1_id == expert_id):

                token = next((t for t in token_records if t.probe_id == record.probe_id), None)
                if token:
                    expert_tokens.append({
                        "target_word": token.target_word,
                        "label": token.label,
                        "input_text": token.input_text,
                        "probe_id": record.probe_id
                    })
                    confidence_scores.append(record.expert_top1_weight)

        category_breakdown = self._get_label_breakdown(
            [{"probe_id": r.probe_id} for r in routing_records
             if r.layer == layer and r.token_position == 1 and r.expert_top1_id == expert_id],
            token_records
        )

        total_target_tokens = sum(1 for r in routing_records if r.token_position == 1 and r.layer == layer)
        usage_rate = len(expert_tokens) / total_target_tokens if total_target_tokens > 0 else 0

        return {
            "layer": layer,
            "expert_id": expert_id,
            "node_name": f"L{layer}E{expert_id}",
            "tokens": expert_tokens[:20],
            "total_tokens": len(expert_tokens),
            "usage_rate": usage_rate,
            "avg_confidence": float(np.mean(confidence_scores)) if confidence_scores else 0,
            "category_breakdown": category_breakdown
        }

    def _load_session_data(
        self,
        session_id: str
    ) -> Tuple[List[RoutingRecord], List[ProbeRecord], Optional[CaptureManifest]]:
        """Load routing, token, and manifest data for a session."""
        session_path = self.data_lake_path / f"session_{session_id}"

        if not session_path.exists():
            session_path = self.data_lake_path / session_id
            if not session_path.exists():
                raise ValueError(f"Session {session_id} not found")

        routing_path = session_path / "routing.parquet"
        routing_records = read_records(str(routing_path), RoutingRecord)

        tokens_path = session_path / "tokens.parquet"
        token_records = read_records(str(tokens_path), ProbeRecord)

        manifest = None
        manifest_path = session_path / "capture_manifest.parquet"
        if manifest_path.exists():
            manifest_records = read_records(str(manifest_path), CaptureManifest)
            manifest = manifest_records[0] if manifest_records else None

        return routing_records, token_records, manifest

    def _load_multi_session_data(
        self,
        session_ids: List[str]
    ) -> Tuple[List[RoutingRecord], List[ProbeRecord], Optional[CaptureManifest]]:
        """Load and merge data from multiple sessions."""
        all_routing = []
        all_tokens = []
        merged_manifest = None

        for sid in session_ids:
            routing, tokens, manifest = self._load_session_data(sid)

            if len(session_ids) > 1:
                prefix = sid[:8] + "_"
                for r in routing:
                    r.probe_id = prefix + r.probe_id
                for t in tokens:
                    t.probe_id = prefix + t.probe_id

            all_routing.extend(routing)
            all_tokens.extend(tokens)

            if manifest:
                if merged_manifest is None:
                    merged_manifest = manifest
                else:
                    # Merge labels lists
                    existing = set(merged_manifest.labels)
                    for label in manifest.labels:
                        if label not in existing:
                            merged_manifest.labels.append(label)

        return all_routing, all_tokens, merged_manifest

    def _apply_filters(
        self,
        routing_records: List[RoutingRecord],
        token_records: List[ProbeRecord],
        filter_config: Dict[str, Any]
    ) -> Tuple[List[RoutingRecord], List[ProbeRecord]]:
        """Apply label-based filtering to records."""
        if not filter_config:
            return routing_records, token_records

        filtered_probe_ids = set()

        for token in token_records:
            include = True

            # Filter by labels
            if "labels" in filter_config and filter_config["labels"]:
                if token.label not in filter_config["labels"]:
                    include = False

            if include:
                filtered_probe_ids.add(token.probe_id)

        filtered_routing = [r for r in routing_records if r.probe_id in filtered_probe_ids]
        filtered_tokens = [t for t in token_records if t.probe_id in filtered_probe_ids]

        return filtered_routing, filtered_tokens

    def _extract_target_routes(
        self,
        routing_records: List[RoutingRecord],
        token_records: List[ProbeRecord],
        window_layers: List[int]
    ) -> Dict[str, Dict]:
        """Extract expert routes for target tokens within specified window layers."""
        routing_by_probe = defaultdict(list)
        for record in routing_records:
            routing_by_probe[record.probe_id].append(record)

        token_by_probe = {t.probe_id: t for t in token_records}

        routes = defaultdict(lambda: {
            "tokens": [],
            "count": 0,
            "confidence_scores": []
        })

        for probe_id, probe_routing in routing_by_probe.items():
            target_routing = [
                r for r in probe_routing
                if r.token_position == 1 and r.layer in window_layers
            ]

            if len(target_routing) != len(window_layers):
                continue

            target_routing.sort(key=lambda r: r.layer)

            try:
                signature = highway_signature(target_routing, target_tokens_only=True)
            except ValueError:
                continue

            if probe_id in token_by_probe:
                token = token_by_probe[probe_id]
                routes[signature]["tokens"].append({
                    "target_word": token.target_word,
                    "label": token.label,
                    "input_text": token.input_text,
                    "probe_id": probe_id
                })

            routes[signature]["count"] += 1

            avg_conf = np.mean([r.routing_confidence() for r in target_routing])
            routes[signature]["confidence_scores"].append(avg_conf)

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
        layer_experts = defaultdict(set)
        expert_label_counts = defaultdict(lambda: defaultdict(int))
        expert_target_word_counts = defaultdict(lambda: defaultdict(int))
        expert_category_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        expert_example_tokens = defaultdict(list)
        expert_all_probe_ids = defaultdict(set)

        token_lookup = {t.probe_id: t for t in token_records}

        for signature, route_info in routes.items():
            parts = signature.split("→")

            for part in parts:
                layer = int(part[1:part.index('E')])
                expert = int(part[part.index('E')+1:])
                layer_experts[layer].add(expert)

                for token_info in route_info["tokens"]:
                    probe_id = token_info["probe_id"]
                    expert_all_probe_ids[part].add(probe_id)
                    token_record = token_lookup.get(probe_id)
                    if token_record:
                        if token_record.label:
                            expert_label_counts[part][token_record.label] += 1
                        if token_record.target_word:
                            expert_target_word_counts[part][token_record.target_word] += 1
                        if token_record.categories_json:
                            cats = json.loads(token_record.categories_json)
                            for axis_id, value in cats.items():
                                expert_category_counts[part][axis_id][value] += 1
                        if len(expert_example_tokens[part]) < 10:
                            expert_example_tokens[part].append({
                                "target_word": token_record.target_word,
                                "label": token_record.label,
                                "input_text": token_record.input_text,
                                "probe_id": probe_id,
                                "generated_text": getattr(token_record, 'generated_text', None),
                                "output_category": getattr(token_record, 'output_category', None),
                            })

            for i in range(len(parts) - 1):
                transitions[parts[i]][parts[i + 1]] += route_info["count"]

        # Build nodes
        nodes = []
        for layer in sorted(layer_experts.keys()):
            for expert in sorted(layer_experts[layer]):
                node_name = f"L{layer}E{expert}"

                label_dist = dict(expert_label_counts.get(node_name, {}))
                tw_dist = dict(expert_target_word_counts.get(node_name, {}))
                cat_dists = {k: dict(v) for k, v in expert_category_counts.get(node_name, {}).items()}
                total_tokens = sum(label_dist.values())

                specialization = self._generate_specialization(label_dist, total_tokens)

                nodes.append({
                    "name": node_name,
                    "id": node_name,
                    "layer": layer,
                    "expert_id": expert,
                    "token_count": total_tokens,
                    "label_distribution": label_dist if label_dist else None,
                    "target_word_distribution": tw_dist if tw_dist else None,
                    "category_distributions": cat_dists if cat_dists else None,
                    "specialization": specialization,
                    "tokens": expert_example_tokens.get(node_name) or None,
                    "probe_ids": sorted(expert_all_probe_ids.get(node_name, set())),
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
                link_examples = []

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
                                if len(link_examples) < 10:
                                    link_examples.append({
                                        "target_word": token_record.target_word,
                                        "label": token_record.label,
                                        "input_text": token_record.input_text,
                                        "probe_id": probe_id,
                                        "generated_text": getattr(token_record, 'generated_text', None),
                                        "output_category": getattr(token_record, 'output_category', None),
                                    })

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
                    "token_count": link_token_count,
                    "tokens": link_examples if link_examples else None,
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
        routing_records: List[RoutingRecord],
        window_layers: List[int]
    ) -> Dict[str, Any]:
        """Calculate overall statistics for the window."""
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

    def _get_label_breakdown(
        self,
        tokens: List[Dict[str, str]],
        token_records: List[ProbeRecord]
    ) -> Dict[str, Any]:
        """Get label breakdown for a set of tokens."""
        token_lookup = {t.probe_id: t for t in token_records}
        label_counts = defaultdict(int)

        for token_info in tokens:
            probe_id = token_info.get("probe_id")
            if probe_id and probe_id in token_lookup:
                label = token_lookup[probe_id].label
                if label:
                    label_counts[label] += 1

        return {"label_distribution": dict(label_counts)}

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
                "label": _axis_label("label", sorted_labels),
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
                    "label": _axis_label(axis_id, sorted_vals),
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
            axes.append({
                "id": "target_word",
                "label": _axis_label("target_word", sorted_tw),
                "label_a": sorted_tw[0],
                "label_b": sorted_tw[1],
                "values": sorted_tw,
            })

        return axes
