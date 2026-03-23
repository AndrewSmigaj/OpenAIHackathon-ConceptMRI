#!/usr/bin/env python3
"""
Output Category Nodes — builds output category nodes and links for Sankey diagrams.

Shared helper used by both expert and cluster route analysis services.
Appends an additional column of output-category nodes at the right end of any
Sankey window, showing how latent-space routing correlates with behavioral outcomes.
"""

from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import json

from schemas.tokens import ProbeRecord


def build_output_category_layer(
    nodes: List[dict],
    links: List[dict],
    routes: Dict[str, Dict],
    token_records: List[ProbeRecord],
    window_layers: List[int],
    output_grouping_axes: Optional[List[str]] = None,
) -> Tuple[List[dict], List[dict], List[Dict[str, Any]]]:
    """Build output category nodes and links, appending them to existing Sankey data.

    Returns (augmented_nodes, augmented_links, output_available_axes).
    If no probes have output_category set, returns the original data unchanged.
    """
    # Build probe_id -> ProbeRecord lookup
    record_lookup = {t.probe_id: t for t in token_records}

    # Quick check: does ANY probe have output_category?
    has_any = any(
        getattr(record_lookup.get(pid), 'output_category', None)
        for route_info in routes.values()
        for token_info in route_info.get("tokens", [])
        for pid in [token_info.get("probe_id")]
        if pid
    )
    if not has_any:
        return nodes, links, []

    output_layer = max(window_layers) + 1

    # Map: final_layer_node_name -> [probe_id, ...]
    final_node_probes: Dict[str, List[str]] = defaultdict(list)
    for signature, route_info in routes.items():
        parts = signature.split("→")
        final_node = parts[-1]
        for token_info in route_info.get("tokens", []):
            pid = token_info.get("probe_id")
            if pid:
                final_node_probes[final_node].append(pid)

    # Group by (final_node, output_category) -> [ProbeRecord]
    category_groups: Dict[str, List[ProbeRecord]] = defaultdict(list)  # category -> records
    link_groups: Dict[Tuple[str, str], List[ProbeRecord]] = defaultdict(list)  # (final_node, cat) -> records

    for final_node, probe_ids in final_node_probes.items():
        for pid in probe_ids:
            record = record_lookup.get(pid)
            if not record:
                continue
            if output_grouping_axes:
                output_cat_json = getattr(record, 'output_category_json', None)
                if not output_cat_json:
                    continue
                try:
                    cats = json.loads(output_cat_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                key_parts = [cats.get(axis, 'unknown') for axis in output_grouping_axes]
                cat = '_'.join(key_parts)
            else:
                cat = getattr(record, 'output_category', None)
                if not cat:
                    continue
            category_groups[cat].append(record)
            link_groups[(final_node, cat)].append(record)

    # Ensure full cross-product when output_grouping_axes is provided
    # (always 2 nodes for 1 axis, 4 nodes for 2 axes, even if some combos have 0 probes)
    if output_grouping_axes:
        from itertools import product as itertools_product
        all_values = []
        for axis_id in output_grouping_axes:
            vals = set()
            for record in token_records:
                ocj = getattr(record, 'output_category_json', None)
                if ocj:
                    try:
                        cats = json.loads(ocj)
                        if axis_id in cats:
                            vals.add(cats[axis_id])
                    except (json.JSONDecodeError, TypeError):
                        pass
            all_values.append(sorted(vals))
        for combo in itertools_product(*all_values):
            key = '_'.join(combo)
            if key not in category_groups:
                category_groups[key] = []

    if not category_groups:
        return nodes, links, []

    # Build output nodes
    output_nodes = []
    for category, records in sorted(category_groups.items()):
        node_name = f"Out:{category}"

        label_dist: Dict[str, int] = defaultdict(int)
        tw_dist: Dict[str, int] = defaultdict(int)
        cat_dists: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for record in records:
            if record.label:
                label_dist[record.label] += 1
            if record.target_word:
                tw_dist[record.target_word] += 1
            # Parse output_category_json for output axes
            output_cat_json = getattr(record, 'output_category_json', None)
            if output_cat_json:
                try:
                    output_cats = json.loads(output_cat_json)
                    for axis_id, value in output_cats.items():
                        cat_dists[axis_id][value] += 1
                except (json.JSONDecodeError, TypeError):
                    pass

        total = len(records)
        specialization = _generate_specialization(dict(label_dist), total, category)

        # Build example tokens (all records for output nodes)
        example_tokens = []
        for record in records:
            example_tokens.append({
                "target_word": record.target_word,
                "label": record.label,
                "input_text": record.input_text,
                "probe_id": record.probe_id,
                "generated_text": getattr(record, 'generated_text', None),
                "output_category": getattr(record, 'output_category', None),
            })

        output_nodes.append({
            "name": node_name,
            "id": node_name,
            "layer": output_layer,
            "expert_id": -1,
            "token_count": total,
            "label_distribution": dict(label_dist) if label_dist else None,
            "target_word_distribution": dict(tw_dist) if tw_dist else None,
            "category_distributions": {k: dict(v) for k, v in cat_dists.items()} if cat_dists else None,
            "specialization": specialization,
            "tokens": example_tokens if example_tokens else None,
        })

    # Build links from final-layer nodes to output nodes
    output_links = []
    # Pre-compute total probes per final node for probability calculation
    final_node_totals: Dict[str, int] = {}
    for final_node, probe_ids in final_node_probes.items():
        final_node_totals[final_node] = len(probe_ids)

    for (final_node, category), records in sorted(link_groups.items()):
        node_name = f"Out:{category}"
        count = len(records)
        total_from_source = final_node_totals.get(final_node, 1)

        link_label_dist: Dict[str, int] = defaultdict(int)
        link_tw_dist: Dict[str, int] = defaultdict(int)
        link_cat_dists: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for record in records:
            if record.label:
                link_label_dist[record.label] += 1
            if record.target_word:
                link_tw_dist[record.target_word] += 1
            output_cat_json = getattr(record, 'output_category_json', None)
            if output_cat_json:
                try:
                    output_cats = json.loads(output_cat_json)
                    for axis_id, value in output_cats.items():
                        link_cat_dists[axis_id][value] += 1
                except (json.JSONDecodeError, TypeError):
                    pass

        output_links.append({
            "source": final_node,
            "target": node_name,
            "value": count,
            "probability": count / total_from_source if total_from_source > 0 else 0,
            "route_signature": f"{final_node}→{node_name}",
            "label_distribution": dict(link_label_dist) if link_label_dist else None,
            "target_word_distribution": dict(link_tw_dist) if link_tw_dist else None,
            "category_distributions": {k: dict(v) for k, v in link_cat_dists.items()} if link_cat_dists else None,
            "token_count": count,
        })

    # Compute output available axes from output_category_json
    output_axes = _compute_output_axes(category_groups)

    return nodes + output_nodes, links + output_links, output_axes


def _generate_specialization(label_dist: Dict[str, int], total: int, category: str) -> str:
    """Generate specialization string for an output node."""
    if not label_dist or total == 0:
        return f"{category}"

    sorted_labels = sorted(label_dist.items(), key=lambda x: x[1], reverse=True)
    parts = []
    for label, count in sorted_labels[:3]:
        pct = (count / total) * 100
        parts.append(f"{label} ({pct:.0f}%)")

    return f"{category} — " + " / ".join(parts)


def _compute_output_axes(category_groups: Dict[str, List[ProbeRecord]]) -> List[Dict[str, Any]]:
    """Compute available output axes from output_category_json across all categorized probes."""
    axis_values: Dict[str, set] = defaultdict(set)

    for records in category_groups.values():
        for record in records:
            output_cat_json = getattr(record, 'output_category_json', None)
            if output_cat_json:
                try:
                    output_cats = json.loads(output_cat_json)
                    for axis_id, value in output_cats.items():
                        axis_values[axis_id].add(value)
                except (json.JSONDecodeError, TypeError):
                    pass

    axes = []
    for axis_id, values in axis_values.items():
        if len(values) >= 2:
            sorted_vals = sorted(values)
            axes.append({
                "id": axis_id,
                "label": " / ".join(sorted_vals[:3]) + ("\u2026" if len(sorted_vals) > 3 else ""),
                "label_a": sorted_vals[0],
                "label_b": sorted_vals[1],
                "values": sorted_vals,
            })

    return axes
