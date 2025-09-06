#!/usr/bin/env python3
"""
Simple Pydantic schemas for API requests/responses.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class WordSource(BaseModel):
    """Word source configuration for flexible mining."""
    source_type: str  # "custom", "pos_pure", "synset_hyponyms"
    source_params: Dict[str, Any]


class ProbeRequest(BaseModel):
    """Request to create a new probe session."""
    session_name: str
    context_sources: List[WordSource]
    target_sources: List[WordSource]
    layers: Optional[List[int]] = [0, 1, 2]


class ProbeResponse(BaseModel):
    """Response after creating probe session."""
    session_id: str
    manifest: Dict[str, Any]
    execution_url: str
    summary: Dict[str, Any]


class ExecutionResponse(BaseModel):
    """Response after starting session execution."""
    started: bool
    status_url: str
    estimated_time: Optional[str] = None


class StatusResponse(BaseModel):
    """Session status response."""
    session_id: str
    state: str
    progress: Dict[str, Any]
    categories: Dict[str, Any]