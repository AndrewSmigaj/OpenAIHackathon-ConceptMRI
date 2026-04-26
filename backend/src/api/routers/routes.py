#!/usr/bin/env python3
"""
Expert route analysis endpoints — load-only.

Schemas are built atomically by `/experiments/build-schema` (see clustering.py).
This router serves cached expert-route windows and the per-route / per-expert
detail GET endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import json
import logging

from api.schemas import (
    LoadExpertRoutesRequest,
    RouteAnalysisResponse,
    RouteDetailsResponse,
    ExpertDetailsResponse,
)
from api.dependencies import get_route_analysis_service
from api.layer_windows import window_id_for_transition
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from api.config import DATA_LAKE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_cached_expert_routes(request: LoadExpertRoutesRequest) -> dict:
    """Load a cached expert-route transition for the requested rank."""
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

    base_name = f"t_{'_'.join(str(l) for l in request.transition_layers)}"
    rank_suffix = f"__rank{request.expert_rank}"
    tdir = schema_dir / "windows" / window_id / "expert"
    base_path = tdir / f"{base_name}{rank_suffix}.json"
    if not base_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Expert routes transition '{base_name}' rank {request.expert_rank} not built for schema '{request.schema_name}' (window {window_id})",
        )

    return json.loads(base_path.read_text())


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: LoadExpertRoutesRequest,
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service),
):
    """Load cached expert-route transition from a schema."""
    try:
        result = _load_cached_expert_routes(request)
        logger.info(
            f"Expert route load returned "
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
