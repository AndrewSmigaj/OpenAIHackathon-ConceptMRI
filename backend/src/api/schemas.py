#!/usr/bin/env python3
"""
Simple Pydantic schemas for API requests/responses.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


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
    target_word: Optional[str] = None
    labels: Optional[List[str]] = None
    state: str


class SessionDetailResponse(BaseModel):
    """Response for session details."""
    manifest: Dict[str, Any]
    data_lake_paths: Dict[str, str]
    labels: List[str]
    target_word: Optional[str] = None
    sentences: Optional[List['ProbeExample']] = None


# Experiment Analysis Schemas
class FilterConfig(BaseModel):
    """Configuration for filtering probes by label."""
    labels: Optional[List[str]] = None


class AnalyzeRoutesRequest(BaseModel):
    """Request to analyze expert routes for a session."""
    session_id: Optional[str] = None
    session_ids: Optional[List[str]] = None
    window_layers: List[int]
    filter_config: Optional[FilterConfig] = None
    top_n_routes: int = 20
    clustering_schema: Optional[str] = None  # Load from named schema (skip computation)
    save_as: Optional[str] = None            # Compute AND save result under this name
    output_grouping_axes: Optional[List[str]] = None  # Dynamic output node grouping


class ClusteringConfig(BaseModel):
    """Configuration for clustering analysis."""
    reduction_dimensions: int = 128
    clustering_method: str = "kmeans"  # "kmeans", "hierarchical", "dbscan"
    layer_cluster_counts: Dict[int, int] = {}  # {layer: num_clusters}
    embedding_source: str = "expert_output"  # "expert_output" or "residual_stream"
    reduction_method: str = "pca"  # "pca" or "umap"
    clustering_dimensions: Optional[List[int]] = None  # 0-indexed dim subset; None = all


class AnalyzeClusterRoutesRequest(BaseModel):
    """Request to analyze cluster routes for a session."""
    session_id: Optional[str] = None
    session_ids: Optional[List[str]] = None
    window_layers: List[int]
    clustering_config: ClusteringConfig
    filter_config: Optional[FilterConfig] = None
    top_n_routes: int = 20
    clustering_schema: Optional[str] = None  # Load from named schema (skip computation)
    save_as: Optional[str] = None            # Compute AND save result under this name
    output_grouping_axes: Optional[List[str]] = None  # Dynamic output node grouping


class ProbeExample(BaseModel):
    """Example probe for route display."""
    target_word: str
    label: Optional[str] = None
    input_text: str
    probe_id: str
    generated_text: Optional[str] = None
    output_category: Optional[str] = None

# Resolve forward reference in SessionDetailResponse
SessionDetailResponse.model_rebuild()


class SankeyNode(BaseModel):
    """Sankey diagram node with enhanced data."""
    name: str
    id: str
    layer: int
    expert_id: int
    token_count: int
    label_distribution: Optional[Dict[str, int]] = None
    target_word_distribution: Optional[Dict[str, int]] = None
    category_distributions: Optional[Dict[str, Dict[str, int]]] = None
    specialization: str
    tokens: Optional[List[ProbeExample]] = None


class SankeyLink(BaseModel):
    """Sankey diagram link with enhanced data."""
    source: str
    target: str
    value: int
    probability: float
    route_signature: str
    label_distribution: Optional[Dict[str, int]] = None
    target_word_distribution: Optional[Dict[str, int]] = None
    category_distributions: Optional[Dict[str, Dict[str, int]]] = None
    token_count: int


class TopRoute(BaseModel):
    """Top route with statistics."""
    signature: str
    count: int
    coverage: float
    avg_confidence: float
    example_tokens: List[ProbeExample]


class RouteAnalysisResponse(BaseModel):
    """Response for route analysis."""
    session_id: str
    window_layers: List[int]
    nodes: List[SankeyNode]
    links: List[SankeyLink]
    top_routes: List[TopRoute]
    statistics: Dict[str, Any]
    available_axes: Optional[List[Dict[str, Any]]] = None
    output_available_axes: Optional[List[Dict[str, Any]]] = None
    probe_assignments: Optional[Dict[str, Dict[str, int]]] = None


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
    tokens: List[ProbeExample]
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


# --- Sentence Generation Schemas ---

class GenerateSentenceSetRequest(BaseModel):
    """Request to generate a sentence set via LLM."""
    name: str
    target_word: str = "said"
    label_a: str = "narrative"
    label_b: str = "factual"
    description_a: str = "Narrative storytelling context"
    description_b: str = "Factual reporting context"
    count_per_group: int = 20
    neutral_count: int = 5
    api_key: Optional[str] = None
    provider: str = "openai"
    save: bool = True


class SentenceSetResponse(BaseModel):
    """Response with sentence set summary."""
    name: str
    version: str
    target_word: str
    label_a: str
    label_b: str
    count_a: int
    count_b: int
    count_neutral: int


class SentenceSetDetailResponse(BaseModel):
    """Full sentence set with all sentences."""
    name: str
    version: str
    target_word: str
    label_a: str
    label_b: str
    description_a: str
    description_b: str
    sentences_a: List[Dict[str, Any]]
    sentences_b: List[Dict[str, Any]]
    sentences_neutral: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class SentenceSetListResponse(BaseModel):
    """Response listing available sentence sets."""
    sentence_sets: List[Dict[str, Any]]


# --- Sentence Experiment Schemas ---

class SentenceExperimentRequest(BaseModel):
    """Request to run a sentence experiment capture."""
    sentence_set_name: str
    session_name: Optional[str] = None
    layers: Optional[List[int]] = None  # defaults to adapter's layer list
    generate_output: bool = True  # generate continuation text for each probe


class SentenceExperimentResponse(BaseModel):
    """Response after running a sentence experiment."""
    session_id: str
    session_name: str
    total_probes: int
    label_a: str
    label_b: str
    count_a: int
    count_b: int


# --- On-Demand Reduction Schemas ---

class ReductionRequest(BaseModel):
    """Request for on-demand PCA/UMAP reduction."""
    session_ids: List[str]
    layers: List[int]
    source: str = "expert_output"  # "expert_output" or "residual_stream"
    method: str = "umap"           # "pca" or "umap"
    n_components: int = 3


class ReductionResponse(BaseModel):
    """Response from on-demand reduction."""
    points: List[Dict[str, Any]]
    layers: List[int]
    method: str
    n_components: int


# --- Scaffold Step Schemas ---

class ScaffoldStepRequest(BaseModel):
    """Request to run a single scaffold step via LLM."""
    session_id: str
    step_id: str
    prompt: str  # The (possibly edited) prompt
    data_sources: List[str]  # ["expert_routes", "cluster_routes", ...]
    output_type: str  # "narrative" or "element_labels"
    expert_windows: Optional[List[Dict]] = None
    cluster_windows: Optional[List[Dict]] = None
    previous_outputs: Optional[List[str]] = None
    api_key: str
    provider: str = "openai"


class ScaffoldStepResponse(BaseModel):
    """Response from a scaffold step."""
    narrative: Optional[str] = None
    element_labels: Optional[Dict[str, str]] = None


# --- Temporal Capture Schemas ---

class TemporalCaptureRequest(BaseModel):
    """Request to run a temporal basin transition experiment."""
    session_id: str
    basin_a_cluster_id: int
    basin_b_cluster_id: int
    basin_layer: int
    sentences_per_block: int = 20
    processing_mode: str = "expanding_cache_on"  # expanding_cache_off, expanding_cache_on, single_cache_on
    sequence_config: str = "block_ab"  # block_ab, block_ba, block_aba
    clustering_schema: Optional[str] = None  # Named schema to read assignments from
    layers: Optional[List[int]] = None
    run_label: Optional[str] = None
    generate_output: bool = True  # generate continuation text for each probe


class TemporalCaptureResponse(BaseModel):
    """Response from a temporal capture experiment."""
    temporal_run_id: str
    new_session_id: str
    sequence_positions: int
    regime_boundary: int
    processing_mode: str
    basin_a_sentences: int
    basin_b_sentences: int
