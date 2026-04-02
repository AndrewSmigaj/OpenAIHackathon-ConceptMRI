#!/usr/bin/env python3
"""
LLM insights, scaffold steps, and experiments health check endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from api.schemas import (
    LLMInsightsRequest, LLMInsightsResponse,
    ScaffoldStepRequest, ScaffoldStepResponse,
)
from api.dependencies import get_llm_insights_service
from services.experiments.llm_insights_service import LLMInsightsService

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.post("/experiments/scaffold-step", response_model=ScaffoldStepResponse)
async def run_scaffold_step(
    request: ScaffoldStepRequest,
    service: LLMInsightsService = Depends(get_llm_insights_service)
) -> ScaffoldStepResponse:
    """Run a single scaffold step: prompt + data context -> LLM -> result."""
    try:
        result = await service.run_scaffold_step(
            prompt=request.prompt,
            data_sources=request.data_sources,
            output_type=request.output_type,
            expert_windows=request.expert_windows,
            cluster_windows=request.cluster_windows,
            previous_outputs=request.previous_outputs,
            api_key=request.api_key,
            provider=request.provider,
        )
        return ScaffoldStepResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Scaffold step failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/health")
async def health_check():
    """Health check for experiments API."""
    return {"status": "healthy", "service": "expert_route_analysis"}
