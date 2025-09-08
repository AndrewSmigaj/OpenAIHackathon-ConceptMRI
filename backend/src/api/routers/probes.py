#!/usr/bin/env python3
"""
Probes API router - Session-based MoE data capture with multi-category support.
"""

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from typing import List, Dict, Any
import json
import logging

from api.schemas import (
    ProbeRequest, ProbeResponse, ExecutionResponse, StatusResponse,
    SessionListResponse, SessionDetailResponse
)
from api.dependencies import get_capture_service
from services.probes.integrated_capture_service import IntegratedCaptureService, SessionState
from schemas.capture_manifest import CaptureManifest

router = APIRouter()
logger = logging.getLogger(__name__)


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
        sessions_dir = Path(service.data_lake_path) / "_sessions"
        
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        metadata = json.load(f)
                    
                    sessions.append(SessionListResponse(
                        session_id=metadata["session_id"],
                        session_name=metadata["session_name"],
                        created_at=metadata["created_at"],
                        probe_count=metadata.get("completed_pairs", metadata.get("total_pairs", 0)),
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
    logger.info(f"📋 Session details requested for: {session_id}")
    
    try:
        # Check if session exists and get status
        logger.info(f"🔍 Checking session status for: {session_id}")
        status = service.get_session_status(session_id)
        logger.info(f"📊 Session status: {status.state}, active sessions count: {len(service.active_sessions)}")
        logger.info(f"🗂️ Active sessions list: {list(service.active_sessions.keys())}")
        
        if status.state != SessionState.COMPLETED:
            logger.warning(f"⚠️ Session {session_id} not completed (state: {status.state})")
            raise HTTPException(status_code=400, detail="Session not completed yet")
        
        # Handle completed sessions - load existing manifest instead of finalizing
        logger.info(f"📝 Session is completed, loading existing manifest for: {session_id}")
        logger.info(f"🔍 Session in active_sessions? {session_id in service.active_sessions}")
        
        if session_id in service.active_sessions:
            # Session is still active but completed - finalize it now
            logger.info(f"🔄 Session still active, finalizing now")
            manifest = service.finalize_session(session_id)
        else:
            # Session was already finalized - load existing manifest from disk
            logger.info(f"📂 Loading existing manifest from disk")
            session_file = Path(service.sessions_dir) / f"{session_id}.json"
            if not session_file.exists():
                logger.error(f"❌ Session file not found: {session_file}")
                raise HTTPException(status_code=404, detail=f"Session metadata file not found")
            
            with open(session_file, 'r') as f:
                session_metadata = json.load(f)
            
            # Load existing manifest from session metadata - no reconstruction needed
            manifest = CaptureManifest(
                capture_session_id=session_metadata["session_id"],
                session_name=session_metadata["session_name"], 
                contexts=session_metadata["contexts"],
                targets=session_metadata["targets"],
                context_category_assignments=session_metadata.get("context_category_assignments", {}),
                target_category_assignments=session_metadata.get("target_category_assignments", {}),
                layers_captured=session_metadata.get("layers", [0, 1, 2]),
                probe_count=session_metadata["total_pairs"],
                created_at=session_metadata["created_at"],
                model_name="gpt-oss-20b"
            )
            
        logger.info(f"✅ Successfully loaded session manifest")
        
        # Generate data lake paths
        logger.info(f"📁 Generating data lake paths for: {session_id}")
        session_dir = Path(service.data_lake_path) / session_id
        logger.info(f"📂 Session directory path: {session_dir}")
        
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
        
        logger.info(f"📦 Successfully built session response for: {session_id}")
        return SessionDetailResponse(
            manifest=manifest_dict,
            data_lake_paths=data_lake_paths,
            categories={
                "contexts": manifest.context_category_assignments or {},
                "targets": manifest.target_category_assignments or {}
            }
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 400 for non-completed sessions)
        logger.error(f"🚫 HTTP Exception for session {session_id}: {e.detail}")
        raise e
    except ValueError as ve:
        # Specific handling for ValueError (likely from finalize_session)
        logger.error(f"❌ ValueError for session {session_id}: {str(ve)}")
        logger.error(f"💡 This likely means session is not in active_sessions")
        raise HTTPException(status_code=404, detail=f"Session not found or error: {str(ve)}")
    except FileNotFoundError as fe:
        # Specific handling for missing files
        logger.error(f"📄 FileNotFoundError for session {session_id}: {str(fe)}")
        raise HTTPException(status_code=404, detail=f"Session data files not found: {str(fe)}")
    except Exception as e:
        # Generic exception handling
        logger.error(f"💥 Unexpected error for session {session_id}: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=404, detail=f"Session not found or error: {str(e)}")