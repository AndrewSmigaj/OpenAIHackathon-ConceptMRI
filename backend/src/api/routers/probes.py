#!/usr/bin/env python3
"""
Probes API router - Session-based MoE data capture with multi-category support.
"""

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from typing import List, Dict, Any
import json

from api.schemas import (
    ProbeRequest, ProbeResponse, ExecutionResponse, StatusResponse,
    SessionListResponse, SessionDetailResponse
)
from api.dependencies import get_capture_service
from services.probes.integrated_capture_service import IntegratedCaptureService, SessionState

router = APIRouter()


@router.post("/probes", response_model=ProbeResponse)
async def create_probe_session(
    request: ProbeRequest,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Create new probe session from word sources."""
    try:
        # Convert Pydantic models to dicts for service
        context_sources = [source.dict() for source in request.context_sources]
        target_sources = [source.dict() for source in request.target_sources]
        
        # Create session using multi-source method
        session_id = service.create_session_from_sources(
            session_name=request.session_name,
            context_sources=context_sources,
            target_sources=target_sources
        )
        
        # Get session status to extract details
        status = service.get_session_status(session_id)
        
        # Mine words to get actual contexts/targets/categories
        contexts, context_categories = service._aggregate_word_sources(context_sources)
        targets, target_categories = service._aggregate_word_sources(target_sources)
        
        return ProbeResponse(
            session_id=session_id,
            total_pairs=status.total_pairs,
            contexts=contexts,
            targets=targets,
            categories={
                "contexts": context_categories,
                "targets": target_categories
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create probe session: {str(e)}")


@router.post("/probes/{session_id}/execute", response_model=ExecutionResponse)
async def execute_probe_session(
    session_id: str,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Execute all captures for a probe session."""
    try:
        # Execute all remaining context-target pairs
        probe_ids = service.capture_session_batch(session_id)
        
        return ExecutionResponse(
            started=True,
            probe_ids=probe_ids,
            status_url=f"/api/probes/{session_id}/status",
            estimated_time="2-5 minutes"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute session: {str(e)}")


@router.get("/probes/{session_id}/status", response_model=StatusResponse)
async def get_probe_session_status(
    session_id: str,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Get current status of probe session."""
    try:
        status = service.get_session_status(session_id)
        
        # Build response
        response_data = {
            "session_id": session_id,
            "state": status.state.value,
            "progress": {
                "completed": status.completed_pairs,
                "total": status.total_pairs,
                "failed": status.failed_pairs,
                "percent": status.progress_percent
            }
        }
        
        # If session is completed, finalize and add manifest + paths
        if status.state == SessionState.COMPLETED:
            manifest = service.finalize_session(session_id)
            
            # Generate data lake paths
            session_dir = Path(service.data_lake_path) / session_id
            data_lake_paths = {
                "tokens": str(session_dir / "tokens.parquet"),
                "routing": str(session_dir / "routing.parquet"),
                "expert_internal": str(session_dir / "expert_internal_activations.parquet"),
                "expert_output": str(session_dir / "expert_output_states.parquet"),
                "manifest": str(session_dir / "capture_manifest.parquet")
            }
            
            # Convert manifest to dict for response
            manifest_dict = {
                "session_name": manifest.session_name,
                "contexts": manifest.contexts,
                "targets": manifest.targets,
                "context_category_assignments": manifest.context_category_assignments,
                "target_category_assignments": manifest.target_category_assignments,
                "probe_count": manifest.probe_count,
                "created_at": manifest.created_at,
                "model_name": manifest.model_name
            }
            
            response_data["manifest"] = manifest_dict
            response_data["data_lake_paths"] = data_lake_paths
        
        return StatusResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")


@router.get("/probes", response_model=List[SessionListResponse])
async def list_probe_sessions(
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """List all available probe sessions."""
    try:
        sessions = []
        sessions_dir = Path(service.data_lake_path).parent / "sessions"
        
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        metadata = json.load(f)
                    
                    sessions.append(SessionListResponse(
                        session_id=metadata["session_id"],
                        session_name=metadata["session_name"],
                        created_at=metadata["created_at"],
                        probe_count=metadata.get("completed_pairs", 0),
                        contexts=metadata["contexts"],
                        targets=metadata["targets"],
                        state=metadata["state"]
                    ))
                except Exception as e:
                    # Skip corrupted session files
                    continue
        
        return sorted(sessions, key=lambda x: x.created_at, reverse=True)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/probes/{session_id}", response_model=SessionDetailResponse)
async def get_probe_session_details(
    session_id: str,
    service: IntegratedCaptureService = Depends(get_capture_service)
):
    """Get complete session details including manifest and data lake paths."""
    try:
        # Check if session exists and get status
        status = service.get_session_status(session_id)
        
        if status.state != SessionState.COMPLETED:
            raise HTTPException(status_code=400, detail="Session not completed yet")
        
        # Get finalized manifest
        manifest = service.finalize_session(session_id)
        
        # Generate data lake paths
        session_dir = Path(service.data_lake_path) / session_id
        data_lake_paths = {
            "tokens": str(session_dir / "tokens.parquet"),
            "routing": str(session_dir / "routing.parquet"),  
            "expert_internal": str(session_dir / "expert_internal_activations.parquet"),
            "expert_output": str(session_dir / "expert_output_states.parquet"),
            "manifest": str(session_dir / "capture_manifest.parquet")
        }
        
        # Build manifest dict
        manifest_dict = {
            "capture_session_id": manifest.capture_session_id,
            "session_name": manifest.session_name,
            "contexts": manifest.contexts,
            "targets": manifest.targets,
            "context_category_assignments": manifest.context_category_assignments,
            "target_category_assignments": manifest.target_category_assignments,
            "layers_captured": manifest.layers_captured,
            "probe_count": manifest.probe_count,
            "created_at": manifest.created_at,
            "model_name": manifest.model_name
        }
        
        return SessionDetailResponse(
            manifest=manifest_dict,
            data_lake_paths=data_lake_paths,
            categories={
                "contexts": manifest.context_category_assignments or {},
                "targets": manifest.target_category_assignments or {}
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found or error: {str(e)}")