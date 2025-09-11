#!/usr/bin/env python3
"""
Experiments API router - Expert route analysis and visualization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
import logging

from api.schemas import (
    AnalyzeRoutesRequest, AnalyzeClusterRoutesRequest, RouteAnalysisResponse,
    RouteDetailsResponse, ExpertDetailsResponse,
    LLMInsightsRequest, LLMInsightsResponse
)
from api.dependencies import get_route_analysis_service, get_cluster_analysis_service, get_llm_insights_service
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from services.experiments.llm_insights_service import LLMInsightsService

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
        # Convert FilterConfig to dict if present
        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)
        
        result = service.analyze_session_routes(
            session_id=request.session_id,
            window_layers=request.window_layers,
            filter_config=filter_config_dict,
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


@router.post("/experiments/analyze-cluster-routes", response_model=RouteAnalysisResponse)
async def analyze_cluster_routes(
    request: AnalyzeClusterRoutesRequest,
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service)
):
    """
    Analyze cluster routes for a session within specified window layers.
    
    Request body:
    {
        "session_id": "abc123",
        "window_layers": [0, 1, 2],
        "clustering_config": {
            "pca_dimensions": 128,
            "clustering_method": "kmeans",
            "layer_cluster_counts": {0: 8, 1: 8, 2: 8}
        },
        "filter_config": {
            "context_categories": ["determiner"],
            "target_categories": ["animals", "nouns"]
        },
        "top_n_routes": 20
    }
    """
    try:
        # Convert FilterConfig to dict if present
        filter_config_dict = None
        if request.filter_config:
            filter_config_dict = request.filter_config.dict(exclude_none=True)
        
        # Convert ClusteringConfig to dict
        clustering_config_dict = request.clustering_config.dict(exclude_none=True)
        
        result = service.analyze_session_cluster_routes(
            session_id=request.session_id,
            window_layers=request.window_layers,
            clustering_config=clustering_config_dict,
            filter_config=filter_config_dict,
            top_n_routes=request.top_n_routes
        )
        
        logger.info(f"✅ Analyzed cluster routes for session {request.session_id}, found {result['statistics']['total_routes']} routes")
        return result
        
    except ValueError as e:
        logger.error(f"❌ Cluster route analysis failed for session {request.session_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error in cluster route analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster route analysis failed: {str(e)}")


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


@router.post("/experiments/llm-insights", response_model=LLMInsightsResponse)
async def generate_llm_insights(
    request: LLMInsightsRequest,
    service: LLMInsightsService = Depends(get_llm_insights_service)
):
    """
    Generate LLM insights from expert routing data.
    
    Request body:
    {
        "session_id": "abc123",
        "nodes": [...],  // SankeyNode data with category_distribution
        "links": [...],  // SankeyLink data with category_distribution
        "user_prompt": "Analyze sentiment routing patterns",
        "api_key": "sk-...",
        "provider": "openai"  // or "anthropic"
    }
    """
    try:
        result = await service.analyze_routing_patterns(
            windows=request.windows,
            user_prompt=request.user_prompt,
            api_key=request.api_key,
            provider=request.provider
        )
        
        logger.info(f"✅ Generated LLM insights for session {request.session_id}")
        return LLMInsightsResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ LLM insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# PCA Trajectory endpoint
@router.get("/experiments/pca-trajectories")
async def get_pca_trajectories(
    session_id: str,
    layers: str,  # comma-separated layer numbers
    n_dims: int = 3,
    max_trajectories: int = 500,
    filter_config: str = None,  # JSON-encoded filter configuration
    service: ClusterRouteAnalysisService = Depends(get_cluster_analysis_service)
):
    """
    Get stepped PCA trajectory data for 3D visualization.
    
    Returns PCA coordinates for each probe across specified layers,
    showing how concepts move through the latent space.
    
    Query Parameters:
        session_id: Session identifier
        layers: Comma-separated layer numbers (e.g., "0,1,2,3,4,5")
        n_dims: Number of PCA dimensions to return (2, 3, 5, etc.)
        max_trajectories: Maximum number of trajectories to return (default 500)
    
    Returns:
        {
            "trajectories": [
                {
                    "probe_id": "...",
                    "context": "...",
                    "target": "...",
                    "coordinates": [
                        {"layer": 0, "x": 0.1, "y": 0.2, "z": 0.3},
                        {"layer": 1, "x": 0.2, "y": 0.3, "z": 0.4},
                        ...
                    ]
                }
            ],
            "metadata": {"layers": [0,1,2], "n_dims": 3, "total_trajectories": 100}
        }
    """
    try:
        # Parse layers
        layer_list = [int(x.strip()) for x in layers.split(',')]
        
        # Validate layers
        if not all(0 <= layer <= 23 for layer in layer_list):
            raise HTTPException(status_code=400, detail="Layer numbers must be between 0 and 23")
        
        if len(layer_list) < 2:
            raise HTTPException(status_code=400, detail="At least 2 layers required for trajectories")
        
        # Validate dimensions
        if not (2 <= n_dims <= 128):
            raise HTTPException(status_code=400, detail="n_dims must be between 2 and 128")
        
        # Parse filter_config if provided
        filter_config_dict = None
        if filter_config:
            try:
                import json
                filter_config_dict = json.loads(filter_config)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filter_config JSON format")
        
        # Get trajectories from service
        result = service.get_pca_trajectories(
            session_id=session_id,
            layers=layer_list,
            n_dims=n_dims,
            filter_config=filter_config_dict,
            max_trajectories=max_trajectories
        )
        
        logger.info(f"✅ Generated {len(result['trajectories'])} PCA trajectories for session {session_id}")
        return result
        
    except ValueError as e:
        logger.error(f"❌ Invalid layer format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid layer format: {e}")
    except Exception as e:
        logger.error(f"❌ PCA trajectory generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint for testing
@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}