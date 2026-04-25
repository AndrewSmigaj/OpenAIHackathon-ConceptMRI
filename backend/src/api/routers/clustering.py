#!/usr/bin/env python3
"""
Cluster route analysis endpoints.

Discriminated-union request: `mode="load"` reads a cached schema, `mode="compute"`
computes + saves a new schema. Filters are baked into the schema at compute
time and immutable thereafter.
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from datetime import datetime
from typing import Annotated
import json
import logging

from api.schemas import (
    AnalyzeClusterRoutesRequest,
    LoadClusteringRequest,
    ComputeClusteringRequest,
    RouteAnalysisResponse,
)
from api.dependencies import get_cluster_analysis_service
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from api.config import DATA_LAKE_PATH
from api.routers.route_utils import _rebuild_output_nodes, _precompute_output_variants

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_cached_clusters(request: LoadClusteringRequest) -> dict:
    """Load a cached cluster-route artifact from a schema directory."""
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="session_ids is required for load mode")

    sid = request.session_ids[0]
    schema_dir = DATA_LAKE_PATH / sid / "clusterings" / request.schema_name
    if not schema_dir.exists():
        raise HTTPException(status_code=404, detail=f"Schema '{request.schema_name}' not found for session '{sid}'")

    window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"
    wdir = schema_dir / "cluster_windows"
    base_path = wdir / f"{window_key}.json"
    if not base_path.exists():
        raise HTTPException(status_code=404, detail=f"Window '{window_key}' not built for schema '{request.schema_name}'")

    result = json.loads(base_path.read_text())

    grouping_axes = request.output_grouping_axes
    if not grouping_axes and result.get("output_available_axes"):
        grouping_axes = [result["output_available_axes"][0]["id"]]

    if grouping_axes:
        sorted_axes = sorted(grouping_axes)
        variant_path = wdir / f"{window_key}__out_{'__'.join(sorted_axes)}.json"
        if variant_path.exists():
            logger.info(f"Loading pre-computed cluster variant: {variant_path.name}")
            return json.loads(variant_path.read_text())
        result = _rebuild_output_nodes(result, sid, request.window_layers, grouping_axes)

    return result


def _validate_extension(meta: dict, request: ComputeClusteringRequest, clustering_config_dict: dict) -> None:
    """Ensure a re-compute against an existing schema dir uses identical params.

    `meta.json` is the source of truth. Mismatch → 409 with the offending field
    so the caller can either fix the request, archive the old schema, or pick a
    new name.

    `layer_cluster_counts` is per-window: each new window contributes its own
    layer→k entries. We compare it as the intersection of overlapping layers,
    not strict equality.
    """
    expected_params = dict(meta.get("params") or {})
    incoming_params = dict(clustering_config_dict)
    expected_lcc = expected_params.pop("layer_cluster_counts", {}) or {}
    incoming_lcc = incoming_params.pop("layer_cluster_counts", {}) or {}
    expected_lcc = {str(k): v for k, v in expected_lcc.items()}
    incoming_lcc = {str(k): v for k, v in incoming_lcc.items()}
    overlapping = set(expected_lcc) & set(incoming_lcc)
    lcc_overlap_diff = {l: (expected_lcc[l], incoming_lcc[l]) for l in overlapping if expected_lcc[l] != incoming_lcc[l]}

    expected = {
        "params": expected_params,
        "last_occurrence_only": meta.get("last_occurrence_only"),
        "max_probes": meta.get("max_probes"),
        "steps": meta.get("steps"),
        "filter_config": meta.get("filter_config"),
    }
    incoming_filters = request.filter_config.dict(exclude_none=True) if request.filter_config else None
    incoming = {
        "params": incoming_params,
        "last_occurrence_only": request.last_occurrence_only,
        "max_probes": request.max_probes,
        "steps": request.steps,
        "filter_config": incoming_filters,
    }
    diffs = {k: (expected[k], incoming[k]) for k in expected if expected[k] != incoming[k]}
    if lcc_overlap_diff:
        diffs["layer_cluster_counts"] = (
            {l: expected_lcc[l] for l in overlapping},
            {l: incoming_lcc[l] for l in overlapping},
        )
    if diffs:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "schema_params_mismatch",
                "schema": request.save_as,
                "diff": {k: {"existing": v[0], "request": v[1]} for k, v in diffs.items()},
                "hint": "Schemas are immutable. Archive (or pick a new name) instead of changing params.",
            },
        )


def _compute_and_save_clusters(
    request: ComputeClusteringRequest,
    service: ClusterRouteAnalysisService,
) -> dict:
    """Compute cluster routes and persist them under `save_as`."""
    sid = request.session_id
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required for compute mode")

    schema_dir = DATA_LAKE_PATH / sid / "clusterings" / request.save_as
    meta_path = schema_dir / "meta.json"
    window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"
    wdir = schema_dir / "cluster_windows"

    clustering_config_dict = request.clustering_config.dict(exclude_none=True)
    filter_config_dict = request.filter_config.dict(exclude_none=True) if request.filter_config else None

    is_extension = meta_path.exists()
    if is_extension:
        existing_meta = json.loads(meta_path.read_text())
        _validate_extension(existing_meta, request, clustering_config_dict)
        if (wdir / f"{window_key}.json").exists():
            raise HTTPException(
                status_code=409,
                detail=f"Window '{window_key}' already exists in schema '{request.save_as}'. Archive or use a new name.",
            )

    result = service.analyze_session_cluster_routes(
        session_id=sid,
        session_ids=None,
        window_layers=request.window_layers,
        clustering_config=clustering_config_dict,
        filter_config=filter_config_dict,
        steps=request.steps,
        top_n_routes=request.top_n_routes,
        output_grouping_axes=request.output_grouping_axes,
        max_examples_per_node=request.max_examples_per_node,
        last_occurrence_only=request.last_occurrence_only,
        max_probes=request.max_probes,
    )

    _centroids = result.pop("_centroids", None)
    _trajectory_points = result.pop("_trajectory_points", None)
    sample_size = result.pop("sample_size", None)
    result.pop("_reducers", None)

    wdir.mkdir(parents=True, exist_ok=True)

    save_result = result
    if result.get("output_available_axes"):
        first_axis = result["output_available_axes"][0]["id"]
        save_result = _rebuild_output_nodes(result, sid, request.window_layers, [first_axis])
    (wdir / f"{window_key}.json").write_text(json.dumps(save_result))

    if not is_extension:
        meta = {
            "name": request.save_as,
            "created_at": datetime.now().isoformat(),
            "created_by": "claude_code",
            "params": clustering_config_dict,
            "filter_config": filter_config_dict,
            "last_occurrence_only": request.last_occurrence_only,
            "max_probes": request.max_probes,
            "steps": request.steps,
            "sample_size": sample_size,
        }
        meta_path.write_text(json.dumps(meta, indent=2))
    else:
        existing_meta = json.loads(meta_path.read_text())
        existing_lcc = dict(existing_meta.get("params", {}).get("layer_cluster_counts") or {})
        new_lcc = dict(clustering_config_dict.get("layer_cluster_counts") or {})
        merged_lcc = {**{str(k): v for k, v in existing_lcc.items()}, **{str(k): v for k, v in new_lcc.items()}}
        existing_meta.setdefault("params", {})["layer_cluster_counts"] = merged_lcc
        meta_path.write_text(json.dumps(existing_meta, indent=2))

    if "probe_assignments" in result:
        pa_path = schema_dir / "probe_assignments.json"
        if pa_path.exists():
            existing_pa = json.loads(pa_path.read_text())
            for probe_id, layers in result["probe_assignments"].items():
                if probe_id not in existing_pa:
                    existing_pa[probe_id] = {}
                existing_pa[probe_id].update(layers)
            pa_path.write_text(json.dumps(existing_pa))
        else:
            pa_path.write_text(json.dumps(result["probe_assignments"]))

    if _centroids:
        centroids_path = schema_dir / "centroids.json"
        centroids_all = json.loads(centroids_path.read_text()) if centroids_path.exists() else {}
        for layer, cdict in _centroids.items():
            centroids_all[str(layer)] = {
                str(k): v.tolist() for k, v in cdict.items()
            }
        centroids_path.write_text(json.dumps(centroids_all))

    if _trajectory_points:
        traj_path = schema_dir / "trajectory_points.json"
        traj_all = json.loads(traj_path.read_text()) if traj_path.exists() else {}
        for layer, points in _trajectory_points.items():
            traj_all[str(layer)] = points
        traj_path.write_text(json.dumps(traj_all))

    _precompute_output_variants(result, sid, request.window_layers, window_key, wdir)
    logger.info(f"Saved cluster routes to schema: {request.save_as}/{window_key}")

    if not request.output_grouping_axes and result.get("output_available_axes"):
        first_axis = result["output_available_axes"][0]["id"]
        result = _rebuild_output_nodes(result, sid, request.window_layers, [first_axis])

    return result


@router.post("/experiments/analyze-cluster-routes", response_model=RouteAnalysisResponse)
async def analyze_cluster_routes(
    request: Annotated[AnalyzeClusterRoutesRequest, Body(discriminator="mode")],
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service),
):
    """Cluster route analysis. mode="load" reads a cached schema; mode="compute"
    computes + saves a new schema.
    """
    try:
        if request.mode == "load":
            result = _load_cached_clusters(request)
        elif request.mode == "compute":
            result = _compute_and_save_clusters(request, service)
        else:  # pragma: no cover — pydantic discriminator already validates
            raise HTTPException(status_code=400, detail=f"Unknown mode: {request.mode}")

        logger.info(
            f"Cluster route analysis ({request.mode}) returned "
            f"{result['statistics']['total_routes']} routes"
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster route analysis failed: {str(e)}")
