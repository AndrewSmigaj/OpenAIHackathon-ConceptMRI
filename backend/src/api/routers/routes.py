#!/usr/bin/env python3
"""
Expert route analysis endpoints.

Discriminated-union request: `mode="load"` reads cached rank{1,2,3} variants,
`mode="compute"` computes all three ranks and saves them under a schema name.
Filters are baked into the schema at compute time and immutable thereafter.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from datetime import datetime
from typing import Annotated
import json
import logging

from api.schemas import (
    AnalyzeRoutesRequest,
    LoadExpertRoutesRequest,
    ComputeExpertRoutesRequest,
    RouteAnalysisResponse,
    RouteDetailsResponse,
    ExpertDetailsResponse,
)
from api.dependencies import get_route_analysis_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from api.config import DATA_LAKE_PATH
from api.routers.route_utils import _rebuild_output_nodes, _precompute_output_variants

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_cached_expert_routes(request: LoadExpertRoutesRequest) -> dict:
    """Load a cached expert-route artifact for the requested rank."""
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="session_ids is required for load mode")

    sid = request.session_ids[0]
    schema_dir = DATA_LAKE_PATH / sid / "clusterings" / request.schema_name
    if not schema_dir.exists():
        raise HTTPException(status_code=404, detail=f"Schema '{request.schema_name}' not found for session '{sid}'")

    window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"
    rank_suffix = f"__rank{request.expert_rank}"
    wdir = schema_dir / "expert_windows"
    base_path = wdir / f"{window_key}{rank_suffix}.json"
    if not base_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Expert routes window '{window_key}' rank {request.expert_rank} not built for schema '{request.schema_name}'",
        )

    result = json.loads(base_path.read_text())

    grouping_axes = request.output_grouping_axes
    if not grouping_axes and result.get("output_available_axes"):
        grouping_axes = [result["output_available_axes"][0]["id"]]

    if grouping_axes:
        sorted_axes = sorted(grouping_axes)
        variant_path = wdir / f"{window_key}{rank_suffix}__out_{'__'.join(sorted_axes)}.json"
        if variant_path.exists():
            logger.info(f"Loading pre-computed expert variant: {variant_path.name}")
            return json.loads(variant_path.read_text())
        result = _rebuild_output_nodes(result, sid, request.window_layers, grouping_axes)

    return result


def _validate_expert_extension(meta: dict, request: ComputeExpertRoutesRequest) -> None:
    """When extending an existing schema, expert-side filter params must match what
    was previously baked in (either by an earlier expert call or by the cluster call).
    """
    incoming_filters = request.filter_config.dict(exclude_none=True) if request.filter_config else None
    expected = {
        "last_occurrence_only": meta.get("last_occurrence_only"),
        "max_probes": meta.get("max_probes"),
        "steps": meta.get("steps"),
        "filter_config": meta.get("filter_config"),
    }
    incoming = {
        "last_occurrence_only": request.last_occurrence_only,
        "max_probes": request.max_probes,
        "steps": request.steps,
        "filter_config": incoming_filters,
    }
    diffs = {k: (expected[k], incoming[k]) for k in expected if expected[k] != incoming[k]}
    if diffs:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "schema_filter_mismatch",
                "schema": request.save_as,
                "diff": {k: {"existing": v[0], "request": v[1]} for k, v in diffs.items()},
                "hint": "Schemas are immutable. Archive (or pick a new name) instead of changing filters.",
            },
        )


def _compute_and_save_expert_routes(
    request: ComputeExpertRoutesRequest,
    service: ExpertRouteAnalysisService,
) -> dict:
    """Compute expert routes for ranks 1/2/3 and persist all three under `save_as`.

    Returns the rank-1 result so the caller has something to display by default.
    """
    sid = request.session_id
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required for compute mode")

    schema_dir = DATA_LAKE_PATH / sid / "clusterings" / request.save_as
    meta_path = schema_dir / "meta.json"
    window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"
    wdir = schema_dir / "expert_windows"

    filter_config_dict = request.filter_config.dict(exclude_none=True) if request.filter_config else None

    if meta_path.exists():
        existing_meta = json.loads(meta_path.read_text())
        # If cluster created the meta first, params/filters live at the top level.
        # If a previous expert-only build wrote it, same shape.
        _validate_expert_extension(existing_meta, request)
        for rank in (1, 2, 3):
            if (wdir / f"{window_key}__rank{rank}.json").exists():
                raise HTTPException(
                    status_code=409,
                    detail=f"Expert window '{window_key}' rank {rank} already exists in schema '{request.save_as}'. Archive or use a new name.",
                )

    wdir.mkdir(parents=True, exist_ok=True)

    rank1_result = None

    for rank in (1, 2, 3):
        result = service.analyze_session_routes(
            session_id=sid,
            session_ids=None,
            window_layers=request.window_layers,
            filter_config=filter_config_dict,
            steps=request.steps,
            top_n_routes=request.top_n_routes,
            output_grouping_axes=request.output_grouping_axes,
            expert_rank=rank,
            last_occurrence_only=request.last_occurrence_only,
            max_probes=request.max_probes,
        )

        save_result = result
        if result.get("output_available_axes"):
            first_axis = result["output_available_axes"][0]["id"]
            save_result = _rebuild_output_nodes(result, sid, request.window_layers, [first_axis])
        (wdir / f"{window_key}__rank{rank}.json").write_text(json.dumps(save_result))

        # Pre-compute output-axis variants tagged with the rank
        rank_suffix_key = f"{window_key}__rank{rank}"
        _precompute_output_variants(result, sid, request.window_layers, rank_suffix_key, wdir)
        logger.info(f"Saved expert routes (rank {rank}): {request.save_as}/{rank_suffix_key}")

        if rank == 1:
            rank1_result = result

    expert_meta_block = {
        "type": "expert_routes",
        "ranks": [1, 2, 3],
        "computed_at": datetime.now().isoformat(),
    }
    if meta_path.exists():
        existing_meta = json.loads(meta_path.read_text())
        existing_meta["expert_routes_params"] = expert_meta_block
        meta_path.write_text(json.dumps(existing_meta, indent=2))
    else:
        meta = {
            "name": request.save_as,
            "created_at": datetime.now().isoformat(),
            "created_by": "claude_code",
            "filter_config": filter_config_dict,
            "last_occurrence_only": request.last_occurrence_only,
            "max_probes": request.max_probes,
            "steps": request.steps,
            "expert_routes_params": expert_meta_block,
        }
        meta_path.write_text(json.dumps(meta, indent=2))

    if not request.output_grouping_axes and rank1_result.get("output_available_axes"):
        first_axis = rank1_result["output_available_axes"][0]["id"]
        rank1_result = _rebuild_output_nodes(rank1_result, sid, request.window_layers, [first_axis])

    return rank1_result


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: Annotated[AnalyzeRoutesRequest, Body(discriminator="mode")],
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service),
):
    """Expert route analysis. mode="load" reads a cached rank file; mode="compute"
    builds rank{1,2,3} variants and persists them.
    """
    try:
        if request.mode == "load":
            result = _load_cached_expert_routes(request)
        elif request.mode == "compute":
            result = _compute_and_save_expert_routes(request, service)
        else:  # pragma: no cover
            raise HTTPException(status_code=400, detail=f"Unknown mode: {request.mode}")

        logger.info(
            f"Expert route analysis ({request.mode}) returned "
            f"{result['statistics']['total_routes']} routes"
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed: {str(e)}")


@router.get("/experiments/route-details", response_model=RouteDetailsResponse)
async def get_route_details(
    session_id: str = Query(..., description="Session ID"),
    signature: str = Query(..., description="Route signature (e.g., L0E18→L1E11→L2E14)"),
    window_layers: str = Query(..., description="Comma-separated layers (e.g., 0,1,2)"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Get detailed information about a specific expert route."""
    try:
        try:
            window_layers_list = [int(x.strip()) for x in window_layers.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid window_layers format")

        result = service.get_route_details(
            session_id=session_id,
            route_signature=signature,
            window_layers=window_layers_list
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Route details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route details failed: {str(e)}")


@router.get("/experiments/expert-details", response_model=ExpertDetailsResponse)
async def get_expert_details(
    session_id: str = Query(..., description="Session ID"),
    layer: int = Query(..., description="Layer number"),
    expert_id: int = Query(..., description="Expert ID"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Get details about a specific expert's specialization."""
    try:
        result = service.get_expert_details(
            session_id=session_id,
            layer=layer,
            expert_id=expert_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Expert details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Expert details failed: {str(e)}")
