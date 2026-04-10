#!/usr/bin/env python3
"""
Shared helpers for route analysis endpoints (expert and cluster).
"""

import json
import logging

from api.config import DATA_LAKE_PATH

logger = logging.getLogger(__name__)


def _rebuild_output_nodes(
    result: dict,
    session_id: str,
    window_layers: list,
    output_grouping_axes: list,
) -> dict:
    """Strip existing output nodes/links from cached result and rebuild with dynamic grouping."""
    from core.parquet_reader import read_records
    from schemas.tokens import ProbeRecord
    from services.experiments.output_category_nodes import build_output_category_layer, strip_output_nodes
    from services.probes.scenario_actions import enrich_records_with_scenario_actions

    base_nodes, base_links = strip_output_nodes(result["nodes"], result["links"])

    # Load token records from parquet
    session_path = DATA_LAKE_PATH / session_id
    if not session_path.exists():
        session_path = DATA_LAKE_PATH / f"session_{session_id}"
    token_records = read_records(str(session_path / "tokens.parquet"), ProbeRecord)
    enrich_records_with_scenario_actions(token_records, session_path)

    # Simpler approach: build a synthetic routes dict from final-layer nodes
    final_layer = max(window_layers)
    final_nodes = [n for n in base_nodes if n.get("layer") == final_layer]

    # Build probe->final_node mapping from the full token_records
    # For cluster routes: use probe_assignments if available
    probe_assignments = result.get("probe_assignments", {})
    final_node_probes = {}

    if probe_assignments:
        # Use probe_assignments to map probes to final-layer clusters
        layer_key = str(final_layer)
        for probe_id, layers in probe_assignments.items():
            if layer_key in layers:
                cluster_id = layers[layer_key]
                node_name = f"L{final_layer}C{cluster_id}"
                if node_name not in final_node_probes:
                    final_node_probes[node_name] = []
                final_node_probes[node_name].append(probe_id)
    else:
        # For expert routes: use probe_ids field (complete list) or fall back to tokens (limited)
        for node in final_nodes:
            node_name = node["name"]
            if node.get("probe_ids"):
                final_node_probes[node_name] = node["probe_ids"]
            elif node.get("tokens"):
                final_node_probes[node_name] = [
                    t["probe_id"] for t in node["tokens"] if t.get("probe_id")
                ]

    # Build synthetic routes dict that build_output_category_layer expects
    routes = {}
    for node_name, probe_ids in final_node_probes.items():
        sig = node_name  # Single-node "route"
        routes[sig] = {
            "tokens": [{"probe_id": pid} for pid in probe_ids],
            "count": len(probe_ids),
            "avg_confidence": 0.0,
        }

    augmented_nodes, augmented_links, output_axes = build_output_category_layer(
        base_nodes, base_links, routes, token_records, window_layers,
        output_grouping_axes=output_grouping_axes,
    )

    result = dict(result)
    result["nodes"] = augmented_nodes
    result["links"] = augmented_links
    if output_axes:
        result["output_available_axes"] = output_axes

    return result


def _precompute_output_variants(result, session_id, window_layers, window_key, wdir):
    """Pre-compute all output axis combination variants and save to cache."""
    output_axes = result.get("output_available_axes")
    if not output_axes:
        return
    axis_ids = [a["id"] for a in output_axes]
    # Single axes
    for axis in axis_ids:
        variant = _rebuild_output_nodes(result, session_id, window_layers, [axis])
        (wdir / f"{window_key}__out_{axis}.json").write_text(json.dumps(variant))
    # Axis pairs
    for i, a1 in enumerate(axis_ids):
        for a2 in axis_ids[i + 1:]:
            sorted_pair = sorted([a1, a2])
            variant = _rebuild_output_nodes(result, session_id, window_layers, sorted_pair)
            key = f"{window_key}__out_{'__'.join(sorted_pair)}"
            (wdir / f"{key}.json").write_text(json.dumps(variant))
    logger.info(f"Pre-computed {len(axis_ids)} single + {len(axis_ids) * (len(axis_ids) - 1) // 2} pair output variants for {window_key}")
