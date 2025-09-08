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
    total_pairs: int
    contexts: List[str]
    targets: List[str]
    categories: Dict[str, Dict[str, List[str]]]  # {"contexts": {...}, "targets": {...}}


class ExecutionResponse(BaseModel):
    """Response after starting session execution."""
    started: bool
    probe_ids: List[str]
    status_url: str
    estimated_time: Optional[str] = None


class StatusResponse(BaseModel):
    """Session status response."""
    session_id: str
    state: str
    progress: Dict[str, Any]
    manifest: Optional[Dict[str, Any]] = None
    data_lake_paths: Optional[Dict[str, str]] = None


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    session_id: str
    session_name: str
    created_at: str
    probe_count: int
    contexts: List[str]
    targets: List[str]
    state: str


class SessionDetailResponse(BaseModel):
    """Response for session details."""
    manifest: Dict[str, Any]
    data_lake_paths: Dict[str, str]
    categories: Dict[str, Dict[str, List[str]]]


# Experiment Analysis Schemas
class AnalyzeRoutesRequest(BaseModel):
    """Request to analyze expert routes for a session."""
    session_id: str
    window_layers: List[int]
    filter_config: Optional[Dict[str, Any]] = None
    top_n_routes: int = 20


class SankeyNode(BaseModel):
    """Sankey diagram node."""
    name: str
    layer: int
    expert: int


class SankeyLink(BaseModel):
    """Sankey diagram link."""
    source: int
    target: int
    value: int
    probability: float


class TopRoute(BaseModel):
    """Top route with statistics."""
    signature: str
    count: int
    coverage: float
    avg_confidence: float
    example_tokens: List[Dict[str, str]]


class RouteAnalysisResponse(BaseModel):
    """Response for route analysis."""
    session_id: str
    window_layers: List[int]
    nodes: List[SankeyNode]
    links: List[SankeyLink]
    top_routes: List[TopRoute]
    statistics: Dict[str, Any]


class RouteDetailsResponse(BaseModel):
    """Response for specific route details."""
    signature: str
    window_layers: List[int]
    tokens: List[Dict[str, str]]
    count: int
    coverage: float
    avg_confidence: float
    category_breakdown: Dict[str, Any]


class ExpertDetailsResponse(BaseModel):
    """Response for expert specialization details."""
    layer: int
    expert_id: int
    node_name: str
    tokens: List[Dict[str, str]]
    total_tokens: int
    usage_rate: float
    avg_confidence: float
    category_breakdown: Dict[str, Any]