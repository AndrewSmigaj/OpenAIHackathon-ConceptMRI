#!/usr/bin/env python3
"""
Expert route analysis endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
import json
import logging

from api.schemas import (
    AnalyzeRoutesRequest, RouteAnalysisResponse,
    RouteDetailsResponse, ExpertDetailsResponse,
)
from api.dependencies import get_route_analysis_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from api.config import DATA_LAKE_PATH
from api.routers.route_utils import _rebuild_output_nodes, _precompute_output_variants

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: AnalyzeRoutesRequest,
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Analyze expert routes for a session within specified window layers.

    Supports named clustering schemas:
    - clustering_schema: load cached result from a named schema (skip computation)
    - save_as: compute AND save result under this schema name
    """
    try:
        ids = request.session_ids or ([request.session_id] if request.session_id else [])
        window_key = f"w_{'_'.join(str(l) for l in request.window_layers)}"

        # Load from cached schema if requested (only for rank 1 — cached results are rank-1)
        if request.clustering_schema and ids and request.expert_rank == 1 and not request.last_occurrence_only and request.max_probes is None:
            schema_dir = DATA_LAKE_PATH / ids[0] / "clusterings" / request.clustering_schema
            wdir_cached = schema_dir / "expert_windows"
            cached_path = wdir_cached / f"{window_key}.json"
            if cached_path.exists():
                result = json.loads(cached_path.read_text())
                # Determine grouping axes: use requested, or default to first output axis
                grouping_axes = request.output_grouping_axes
                if not grouping_axes and result.get("output_available_axes"):
                    grouping_axes = [result["output_available_axes"][0]["id"]]
                if grouping_axes:
                    sorted_axes = sorted(grouping_axes)
                    variant_path = wdir_cached / f"{window_key}__out_{'__'.join(sorted_axes)}.json"
                    if variant_path.exists():
                        logger.info(f"Loading pre-computed expert variant: {variant_path.name}")
                        return json.loads(variant_path.read_text())
                    result = _rebuild_output_nodes(result, ids[0], request.window_layers, grouping_axes)
                return result

        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)

        result = service.analyze_session_routes(
            session_id=request.session_id,
            session_ids=request.session_ids,
            window_layers=request.window_layers,
            filter_config=filter_config_dict,
            steps=request.steps,
            top_n_routes=request.top_n_routes,
            output_grouping_axes=request.output_grouping_axes,
            expert_rank=request.expert_rank,
            last_occurrence_only=request.last_occurrence_only,
            max_probes=request.max_probes,
        )

        # Auto-save if save_as provided (only at rank 1 — schema namespace has no rank dimension)
        if request.save_as and len(ids) == 1 and request.expert_rank == 1 and not request.last_occurrence_only and request.max_probes is None:
            schema_dir = DATA_LAKE_PATH / ids[0] / "clusterings" / request.save_as
            wdir = schema_dir / "expert_windows"
            wdir.mkdir(parents=True, exist_ok=True)
            # Base file: apply first output axis (2 nodes) instead of raw cross-product
            save_result = result
            if result.get("output_available_axes"):
                first_axis = result["output_available_axes"][0]["id"]
                save_result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])
            (wdir / f"{window_key}.json").write_text(json.dumps(save_result))
            # Save meta on first window
            meta_path = schema_dir / "meta.json"
            if not meta_path.exists():
                meta = {
                    "name": request.save_as,
                    "created_at": datetime.now().isoformat(),
                    "created_by": "claude_code",
                    "params": {"type": "expert_routes"},
                }
                meta_path.write_text(json.dumps(meta, indent=2))
            _precompute_output_variants(result, ids[0], request.window_layers, window_key, wdir)
            logger.info(f"Saved expert routes to schema: {request.save_as}/{window_key}")

        # Default to first output axis if none requested (always 2 nodes)
        if not request.output_grouping_axes and result.get("output_available_axes") and ids:
            first_axis = result["output_available_axes"][0]["id"]
            result = _rebuild_output_nodes(result, ids[0], request.window_layers, [first_axis])

        logger.info(f"Analyzed routes, found {result['statistics']['total_routes']} routes")
        return result

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
