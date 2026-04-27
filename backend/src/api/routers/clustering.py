#!/usr/bin/env python3
"""
Cluster route + schema build endpoints.

`POST /experiments/build-schema` builds an entire schema atomically: cluster
routes plus expert routes (ranks 1/2/3) for every transition in every window,
in one call. There are 4 fixed windows (see `api.layer_windows`); the build
always covers all of them. The schema directory is the unit of work — the
endpoint either succeeds entirely or leaves no trace.

`POST /experiments/analyze-cluster-routes` is load-only: it reads a single
cached transition from a previously-built schema.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import json
import logging
import os
import shutil
import time

from api.schemas import (
    LoadClusteringRequest,
    BuildSchemaRequest,
    RouteAnalysisResponse,
)
from api.dependencies import get_cluster_analysis_service, get_route_analysis_service
from api.layer_windows import LAYER_WINDOWS, window_id_for_transition
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from api.config import DATA_LAKE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)


def _transition_dir(schema_dir, window_id: str, kind: str):
    """`<schema_dir>/windows/<window_id>/<kind>/` (kind = 'cluster' or 'expert')."""
    return schema_dir / "windows" / window_id / kind


def _transition_filename(transition_layers: list[int]) -> str:
    """`t_<a>_<b>` — the basename for a transition cache file."""
    return f"t_{'_'.join(str(l) for l in transition_layers)}"


def _load_cached_clusters(request: LoadClusteringRequest) -> dict:
    """Load a cached cluster-route transition from a schema directory."""
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="session_ids is required")

    sid = request.session_ids[0]
    schema_dir = DATA_LAKE_PATH / sid / "clusterings" / request.schema_name
    if not schema_dir.exists():
        raise HTTPException(status_code=404, detail=f"Schema '{request.schema_name}' not found for session '{sid}'")

    try:
        window_id = window_id_for_transition(request.transition_layers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tdir = _transition_dir(schema_dir, window_id, "cluster")
    base_name = _transition_filename(request.transition_layers)
    base_path = tdir / f"{base_name}.json"
    if not base_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Transition '{base_name}' not built for schema '{request.schema_name}' (window {window_id})",
        )

    return json.loads(base_path.read_text())


def _build_schema_atomic(
    request: BuildSchemaRequest,
    cluster_service: ClusterRouteAnalysisService,
    expert_service: ExpertRouteAnalysisService,
) -> dict:
    """Atomically build cluster + expert routes for every window/transition.

    Strategy: write everything into a temp dir, then `os.rename` it into place.
    On any exception during the build, `shutil.rmtree` the temp dir and re-raise.
    """
    sid = request.session_id
    final_dir = DATA_LAKE_PATH / sid / "clusterings" / request.save_as
    if final_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Schema '{request.save_as}' already exists for session '{sid}'. Pick a new name or delete/archive the old one.",
        )

    parent_dir = DATA_LAKE_PATH / sid / "clusterings"
    parent_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = parent_dir / f".tmp_{request.save_as}_{int(time.time())}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    clustering_config_dict = request.clustering_config.dict(exclude_none=True)
    filter_config_dict = request.filter_config.dict(exclude_none=True) if request.filter_config else None

    centroids_all: dict = {}
    trajectory_all: dict = {}
    probe_assignments_all: dict = {}
    sample_size = None
    total_probes = None
    transition_count = 0

    try:
        for window in LAYER_WINDOWS:
            window_id = window["id"]
            cluster_dir = _transition_dir(tmp_dir, window_id, "cluster")
            expert_dir = _transition_dir(tmp_dir, window_id, "expert")
            cluster_dir.mkdir(parents=True, exist_ok=True)
            expert_dir.mkdir(parents=True, exist_ok=True)

            for transition_layers in window["transitions"]:
                base_name = _transition_filename(transition_layers)
                transition_count += 1

                # --- Cluster routes for this transition ---
                # output_grouping_axes is caller-controlled per build:
                #   - agent + want NPC truth → ["ground_truth"]
                #   - agent + want agent action → ["action_type"] or omit
                #   - sentence (post-categorize) → omit (uses record.output_category)
                cluster_result = cluster_service.analyze_session_cluster_routes(
                    session_id=sid,
                    session_ids=None,
                    window_layers=transition_layers,
                    clustering_config=clustering_config_dict,
                    filter_config=filter_config_dict,
                    steps=request.steps,
                    top_n_routes=request.top_n_routes,
                    output_grouping_axes=request.output_grouping_axes,
                    max_examples_per_node=request.max_examples_per_node,
                    last_occurrence_only=request.last_occurrence_only,
                    max_probes=request.max_probes,
                )

                window_centroids = cluster_result.pop("_centroids", None) or {}
                window_traj = cluster_result.pop("_trajectory_points", None) or {}
                cluster_result.pop("_reducers", None)
                window_sample_size = cluster_result.pop("sample_size", None)
                if sample_size is None:
                    sample_size = window_sample_size
                if total_probes is None and "statistics" in cluster_result:
                    total_probes = cluster_result["statistics"].get("total_probes")

                (cluster_dir / f"{base_name}.json").write_text(json.dumps(cluster_result))

                for layer, cdict in window_centroids.items():
                    centroids_all[str(layer)] = {str(k): v.tolist() for k, v in cdict.items()}
                for layer, points in window_traj.items():
                    trajectory_all[str(layer)] = points
                for probe_id, layers in (cluster_result.get("probe_assignments") or {}).items():
                    probe_assignments_all.setdefault(probe_id, {}).update(layers)

                logger.info(f"Built cluster transition {request.save_as}/{window_id}/{base_name}")

                # --- Expert routes (ranks 1/2/3) for this transition ---
                for rank in (1, 2, 3):
                    expert_result = expert_service.analyze_session_routes(
                        session_id=sid,
                        session_ids=None,
                        window_layers=transition_layers,
                        filter_config=filter_config_dict,
                        steps=request.steps,
                        top_n_routes=request.top_n_routes,
                        output_grouping_axes=request.output_grouping_axes,
                        expert_rank=rank,
                        last_occurrence_only=request.last_occurrence_only,
                        max_probes=request.max_probes,
                    )
                    rank_name = f"{base_name}__rank{rank}"
                    (expert_dir / f"{rank_name}.json").write_text(json.dumps(expert_result))
                    logger.info(f"Built expert transition {request.save_as}/{window_id}/{rank_name}")

        # --- Schema-level files (single write at the end) ---
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
            "windows": [{"id": w["id"], "layers": w["layers"]} for w in LAYER_WINDOWS],
            "expert_routes_params": {
                "type": "expert_routes",
                "ranks": [1, 2, 3],
                "computed_at": datetime.now().isoformat(),
            },
        }
        (tmp_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        (tmp_dir / "centroids.json").write_text(json.dumps(centroids_all))
        (tmp_dir / "trajectory_points.json").write_text(json.dumps(trajectory_all))
        (tmp_dir / "probe_assignments.json").write_text(json.dumps(probe_assignments_all))

        os.rename(tmp_dir, final_dir)
        logger.info(
            f"Schema build complete: {request.save_as} "
            f"({len(LAYER_WINDOWS)} windows × {transition_count // len(LAYER_WINDOWS)} transitions × 3 ranks)"
        )

        return {
            "schema": request.save_as,
            "windows": len(LAYER_WINDOWS),
            "transitions": transition_count,
            "ranks": 3,
            "sample_size": sample_size,
            "total_probes": total_probes,
        }

    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


@router.post("/experiments/analyze-cluster-routes", response_model=RouteAnalysisResponse)
async def analyze_cluster_routes(
    request: LoadClusteringRequest,
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service),
):
    """Load cached cluster-route transition from a schema."""
    try:
        result = _load_cached_clusters(request)
        logger.info(
            f"Cluster route load returned "
            f"{result['statistics']['total_routes']} routes"
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster route load failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster route load failed: {str(e)}")


@router.post("/experiments/build-schema")
async def build_schema(
    request: BuildSchemaRequest,
    cluster_service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service),
    expert_service: ExpertRouteAnalysisService = Depends(get_route_analysis_service),
):
    """Atomic build: cluster + expert routes (ranks 1/2/3) for all 4 fixed windows × 6 transitions in one call."""
    try:
        return _build_schema_atomic(request, cluster_service, expert_service)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Schema build failed for '{request.save_as}': {e}")
        raise HTTPException(status_code=500, detail=f"Schema build failed: {str(e)}")
