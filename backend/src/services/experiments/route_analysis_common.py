#!/usr/bin/env python3
"""
Shared utilities for route analysis services.

Free functions extracted from ExpertRouteAnalysisService and ClusterRouteAnalysisService.
These functions were duplicated verbatim across both services — they take no instance state
and operate purely on their parameters.
"""

from typing import List, Dict, Optional, Any
from collections import defaultdict
import json

from schemas.tokens import ProbeRecord
from schemas.capture_manifest import CaptureManifest


def axis_label(axis_id: str, sorted_values: list) -> str:
    """Generate a display label for a color axis based on its cardinality."""
    if len(sorted_values) == 2:
        return f"{sorted_values[0]} vs {sorted_values[1]}"
    return f"{axis_id} ({len(sorted_values)} groups)"


def generate_specialization(label_dist: Dict[str, int], total_tokens: int) -> str:
    """Generate human-readable specialization from label distribution."""
    if not label_dist or total_tokens == 0:
        return "No clear specialization"

    sorted_labels = sorted(label_dist.items(), key=lambda x: x[1], reverse=True)

    parts = []
    for label, count in sorted_labels[:3]:
        pct = (count / total_tokens) * 100
        parts.append(f"{label} ({pct:.0f}%)")

    return " / ".join(parts)


def analyze_top_routes(routes: Dict[str, Dict], top_n: int) -> List[Dict[str, Any]]:
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
            # No cap — include all unique examples per top route

        top_routes.append({
            "signature": signature,
            "count": route_info["count"],
            "coverage": coverage,
            "avg_confidence": route_info["avg_confidence"],
            "example_tokens": list(unique_examples.values())
        })

    return top_routes


def compute_available_axes(
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
            "label": axis_label("label", sorted_labels),
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
                "label": axis_label(axis_id, sorted_vals),
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
            "label": axis_label("target_word", sorted_tw),
            "label_a": sorted_tw[0],
            "label_b": sorted_tw[1],
            "values": sorted_tw,
        })

    return axes


def build_sankey_links(
    transitions: Dict, routes: Dict, token_lookup: Dict,
    max_examples: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Build Sankey link data from transitions and route information.

    Shared between expert and cluster route analysis — the link-building
    logic is identical regardless of whether nodes represent experts or clusters.
    """
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
                            if max_examples is None or len(link_examples) < max_examples:
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

    return links
