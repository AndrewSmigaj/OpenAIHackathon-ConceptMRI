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
class FilterConfig(BaseModel):
    """Configuration for filtering probes by categories and specific words."""
    context_categories: Optional[List[str]] = None
    target_categories: Optional[List[str]] = None
    context_words: Optional[List[str]] = None  # NEW: Specific context words
    target_words: Optional[List[str]] = None   # NEW: Specific target words
    max_per_category: Optional[int] = None     # NEW: For UI reference


class AnalyzeRoutesRequest(BaseModel):
    """Request to analyze expert routes for a session."""
    session_id: str
    window_layers: List[int]
    filter_config: Optional[FilterConfig] = None
    top_n_routes: int = 20


class ClusteringConfig(BaseModel):
    """Configuration for clustering analysis."""
    pca_dimensions: int = 128
    clustering_method: str = "kmeans"  # "kmeans", "hierarchical", "dbscan"
    layer_cluster_counts: Dict[int, int] = {}  # {layer: num_clusters}


class AnalyzeClusterRoutesRequest(BaseModel):
    """Request to analyze cluster routes for a session."""
    session_id: str
    window_layers: List[int]
    clustering_config: ClusteringConfig
    filter_config: Optional[FilterConfig] = None
    top_n_routes: int = 20


class SankeyNode(BaseModel):
    """Sankey diagram node with enhanced data."""
    name: str
    id: str
    layer: int
    expert_id: int
    token_count: int
    categories: List[str]
    category_distribution: Dict[str, int]
    specialization: str
    context_target_pairs: List[Dict[str, Any]]


class SankeyLink(BaseModel):
    """Sankey diagram link with enhanced data."""
    source: str
    target: str
    value: int
    probability: float
    route_signature: str
    category_distribution: Dict[str, int]
    token_count: int


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


class LLMInsightsRequest(BaseModel):
    """Request for LLM insights generation."""
    session_id: str
    windows: List[Dict[str, Any]]  # Array of window data with nodes/links
    user_prompt: str
    api_key: str
    provider: str = "openai"


class LLMInsightsResponse(BaseModel):
    """Response from LLM insights generation."""
    narrative: str
    statistics: Dict[str, Any]