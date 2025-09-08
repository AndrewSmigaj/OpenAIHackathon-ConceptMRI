#!/usr/bin/env python3
"""
Experiments API router - Expert route analysis and visualization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
import logging

from api.schemas import (
    AnalyzeRoutesRequest, RouteAnalysisResponse,
    RouteDetailsResponse, ExpertDetailsResponse
)
from api.dependencies import get_route_analysis_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/experiments/analyze-routes", response_model=RouteAnalysisResponse)
async def analyze_expert_routes(
    request: AnalyzeRoutesRequest,
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """
    Analyze expert routes for a session within specified window layers.
    
    Request body:
    {
        "session_id": "abc123",
        "window_layers": [0, 1, 2],
        "filter_config": {
            "context_categories": ["determiner"],
            "target_categories": ["animals", "nouns"]
        },
        "top_n_routes": 20
    }
    """
    try:
        result = service.analyze_session_routes(
            session_id=request.session_id,
            window_layers=request.window_layers,
            filter_config=request.filter_config,
            top_n_routes=request.top_n_routes
        )
        
        logger.info(f"✅ Analyzed routes for session {request.session_id}, found {result['statistics']['total_routes']} routes")
        return result
        
    except ValueError as e:
        logger.error(f"❌ Route analysis failed for session {request.session_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error in route analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed: {str(e)}")


@router.get("/experiments/route-details", response_model=RouteDetailsResponse)
async def get_route_details(
    session_id: str = Query(..., description="Session ID"),
    signature: str = Query(..., description="Route signature (e.g., L0E18→L1E11→L2E14)"),
    window_layers: str = Query(..., description="Comma-separated layers (e.g., 0,1,2)"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """
    Get detailed information about a specific expert route.
    
    Query params:
    - session_id: Session identifier
    - signature: Route signature like "L0E18→L1E11→L2E14" 
    - window_layers: Comma-separated layers like "0,1,2"
    """
    try:
        # Parse window layers with error handling
        try:
            window_layers_list = [int(x.strip()) for x in window_layers.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid window_layers format. Use comma-separated integers like '0,1,2'")
        
        result = service.get_route_details(
            session_id=session_id,
            route_signature=signature,
            window_layers=window_layers_list
        )
        
        logger.info(f"✅ Retrieved details for route {signature} in session {session_id}")
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 400 from above)
    except ValueError as e:
        logger.error(f"❌ Route details failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error getting route details: {e}")
        raise HTTPException(status_code=500, detail=f"Route details failed: {str(e)}")


@router.get("/experiments/expert-details", response_model=ExpertDetailsResponse)
async def get_expert_details(
    session_id: str = Query(..., description="Session ID"),
    layer: int = Query(..., description="Layer number"),
    expert_id: int = Query(..., description="Expert ID"),
    service: ExpertRouteAnalysisService = Depends(get_route_analysis_service)
):
    """
    Get details about a specific expert's specialization.
    
    Query params:
    - session_id: Session identifier
    - layer: Layer number (e.g., 0, 1, 2)
    - expert_id: Expert identifier (e.g., 18, 11, 14)
    """
    try:
        result = service.get_expert_details(
            session_id=session_id,
            layer=layer,
            expert_id=expert_id
        )
        
        logger.info(f"✅ Retrieved details for expert L{layer}E{expert_id} in session {session_id}")
        return result
        
    except ValueError as e:
        logger.error(f"❌ Expert details failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error getting expert details: {e}")
        raise HTTPException(status_code=500, detail=f"Expert details failed: {str(e)}")


# Health check endpoint for testing
@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}