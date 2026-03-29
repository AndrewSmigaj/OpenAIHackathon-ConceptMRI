#!/usr/bin/env python3
"""
Simple dependency injection for shared services.
"""

import logging
import sys
import threading
import time
from pathlib import Path
import torch

logger = logging.getLogger(__name__)

# Add backend to path
backend_src = Path(__file__).parent.parent  # backend/src
project_root = backend_src.parent.parent     # project root
sys.path.insert(0, str(backend_src))

from adapters.registry import get_adapter
from services.probes.integrated_capture_service import IntegratedCaptureService
from services.experiments.expert_route_analysis import ExpertRouteAnalysisService
from services.experiments.cluster_route_analysis import ClusterRouteAnalysisService
from services.experiments.llm_insights_service import LLMInsightsService


# Global service instances (simple approach)
_capture_service = None
_route_analysis_service = None
_cluster_analysis_service = None
_llm_insights_service = None

# Loading stage tracking — readable by health endpoint while model loads in background thread.
# Stages: not_started → initializing → loading_model → creating_service → ready | failed
_loading_stage = "not_started"
_loading_error = None
_loading_start_time = None


def _load_model_sync():
    """Load model in a background thread so the API can serve health checks immediately."""
    global _capture_service, _loading_stage, _loading_error, _loading_start_time

    _loading_start_time = time.time()
    _loading_stage = "initializing"
    logger.info("Initializing capture service")

    try:
        adapter = get_adapter("gpt-oss-20b")
        model_path = project_root / "data" / "models" / adapter.topology.model_dir
        data_lake_path = project_root / "data" / "lake"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at: {model_path}")

        _loading_stage = "loading_model"
        logger.info("Loading model from: %s (adapter: %s)", model_path, adapter.topology.model_name)
        model, tokenizer = adapter.load_model(str(model_path))

        _loading_stage = "creating_service"
        _capture_service = IntegratedCaptureService(
            model=model,
            tokenizer=tokenizer,
            layers_to_capture=adapter.layers_range(),
            data_lake_path=str(data_lake_path),
            adapter=adapter
        )

        elapsed = time.time() - _loading_start_time
        _loading_stage = "ready"
        logger.info("Model loaded successfully in %.0fs — capture service ready", elapsed)

    except Exception as e:
        elapsed = time.time() - _loading_start_time
        _loading_stage = "failed"
        _loading_error = str(e)
        logger.error("Model loading failed after %.0fs: %s", elapsed, e)
        logger.warning("API running in limited mode (analysis endpoints work, probe capture won't)")


async def initialize_capture_service():
    """Start model loading in a background thread. Returns immediately."""
    if _loading_stage != "not_started":
        return  # Already started or completed

    thread = threading.Thread(target=_load_model_sync, daemon=True)
    thread.start()


def get_capture_service() -> IntegratedCaptureService:
    """Get the pre-initialized capture service."""
    if _capture_service is None:
        raise RuntimeError("Capture service not initialized. Should be initialized at startup.")

    return _capture_service


def is_model_loaded() -> bool:
    """Check if the capture service (and model) is initialized."""
    return _capture_service is not None


def get_loading_status() -> dict:
    """Return current loading status for health endpoint."""
    elapsed = None
    if _loading_start_time is not None:
        elapsed = round(time.time() - _loading_start_time, 1)
    return {
        "stage": _loading_stage,
        "elapsed_seconds": elapsed,
        "error": _loading_error,
    }


def get_route_analysis_service() -> ExpertRouteAnalysisService:
    """Get the route analysis service (lazy initialization)."""
    global _route_analysis_service

    if _route_analysis_service is None:
        data_lake_path = project_root / "data" / "lake"
        _route_analysis_service = ExpertRouteAnalysisService(str(data_lake_path))

    return _route_analysis_service


def get_cluster_analysis_service() -> ClusterRouteAnalysisService:
    """Get the cluster analysis service (lazy initialization)."""
    global _cluster_analysis_service

    if _cluster_analysis_service is None:
        data_lake_path = project_root / "data" / "lake"
        _cluster_analysis_service = ClusterRouteAnalysisService(str(data_lake_path))

    return _cluster_analysis_service


def get_llm_insights_service() -> LLMInsightsService:
    """Get the LLM insights service (lazy initialization)."""
    global _llm_insights_service

    if _llm_insights_service is None:
        data_lake_path = project_root / "data" / "lake"
        _llm_insights_service = LLMInsightsService(str(data_lake_path))

    return _llm_insights_service
