#!/usr/bin/env python3
"""
Experiments API router - Expert route analysis and visualization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
import logging

from api.schemas import (
    AnalyzeRoutesRequest, AnalyzeClusterRoutesRequest, RouteAnalysisResponse,
    RouteDetailsResponse, ExpertDetailsResponse,
    LLMInsightsRequest, LLMInsightsResponse,
    ReductionRequest, ReductionResponse
)
from api.dependencies import get_route_analysis_service, get_cluster_analysis_service, get_llm_insights_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from services.experiments.llm_insights_service import LLMInsightsService

router = APIRouter()
logger = logging.getLogger(__name__)

# Resolve data lake path once
_data_lake_path = str(Path(__file__).resolve().parents[4] / "data" / "lake")


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: AnalyzeRoutesRequest,
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """Analyze expert routes for a session within specified window layers."""
    try:
        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)

        result = service.analyze_session_routes(
            session_id=request.session_id,
            session_ids=request.session_ids,
            window_layers=request.window_layers,
            filter_config=filter_config_dict,
            top_n_routes=request.top_n_routes
        )

        logger.info(f"Analyzed routes, found {result['statistics']['total_routes']} routes")
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed: {str(e)}")


@router.post("/experiments/analyze-cluster-routes", response_model=RouteAnalysisResponse)
async def analyze_cluster_routes(
    request: AnalyzeClusterRoutesRequest,
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service)
):
    """Analyze cluster routes for a session within specified window layers."""
    try:
        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)

        clustering_config_dict = request.clustering_config.dict(exclude_none=True)

        result = service.analyze_session_cluster_routes(
            session_id=request.session_id,
            session_ids=request.session_ids,
            window_layers=request.window_layers,
            clustering_config=clustering_config_dict,
            filter_config=filter_config_dict,
            top_n_routes=request.top_n_routes
        )

        logger.info(f"Analyzed cluster routes, found {result['statistics']['total_routes']} routes")
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster route analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster route analysis failed: {str(e)}")


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


@router.post("/experiments/llm-insights", response_model=LLMInsightsResponse)
async def generate_llm_insights(
    request: LLMInsightsRequest,
    service: LLMInsightsService = Depends(get_llm_insights_service)
):
    """Generate LLM insights from expert routing data."""
    try:
        result = await service.analyze_routing_patterns(
            windows=request.windows,
            user_prompt=request.user_prompt,
            api_key=request.api_key,
            provider=request.provider
        )

        return LLMInsightsResponse(**result)

    except Exception as e:
        logger.error(f"LLM insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/reduce", response_model=ReductionResponse)
async def reduce_embeddings(request: ReductionRequest):
    """On-demand dimensionality reduction for one or more sessions."""
    try:
        from services.features.reduction_service import ReductionService
        reducer = ReductionService(n_components=request.n_components)

        points = reducer.reduce_on_demand(
            session_ids=request.session_ids,
            layers=request.layers,
            data_lake_path=_data_lake_path,
            source=request.source,
            method=request.method,
            n_components=request.n_components,
        )

        logger.info(f"Reduced {len(points)} points for {len(request.session_ids)} sessions")
        return ReductionResponse(
            points=points,
            layers=request.layers,
            method=request.method,
            n_components=request.n_components,
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Reduction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reduction failed: {e}")


@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}
