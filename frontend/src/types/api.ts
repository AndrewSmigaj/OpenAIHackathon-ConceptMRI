// API types matching backend Pydantic schemas

interface ExecutionResponse {
  started: boolean;
  probe_ids: string[];
  status_url: string;
  estimated_time?: string;
}

interface CaptureManifest {
  capture_session_id?: string;
  session_name: string;
  target_word: string;
  labels: string[];
  layers_captured?: number[];
  probe_count: number;
  created_at: string;
  model_name: string;
}

interface SessionStatus {
  session_id: string;
  state: 'pending' | 'running' | 'completed' | 'failed';
  progress: {
    completed: number;
    total: number;
    failed: number;
    percent: number;
  };
  manifest?: CaptureManifest;
  data_lake_paths?: {
    tokens: string;
    routing: string;
    expert_output: string;
    manifest: string;
  };
}

interface SessionListItem {
  session_id: string;
  session_name: string;
  created_at: string;
  probe_count: number;
  target_word?: string;
  labels?: string[];
  state: string;
}

interface SessionDetailResponse {
  manifest: CaptureManifest;
  data_lake_paths: {
    tokens: string;
    routing: string;
    expert_output: string;
    manifest: string;
  };
  labels: string[];
  target_word?: string;
  sentences?: ProbeExample[];
}

// Expert Route Analysis Types
interface ProbeExample {
  target_word: string
  label?: string
  input_text: string
  probe_id: string
  generated_text?: string
  output_category?: string
}

interface RouteStatistics {
  total_routes: number
  total_probes: number
  routes_coverage: number
  window_layers: number[]
  [key: string]: any
}

interface FilterConfig {
  labels?: string[]
}

interface AnalyzeRoutesRequest {
  session_id?: string
  session_ids?: string[]
  window_layers: number[]
  filter_config?: FilterConfig
  top_n_routes: number
  clustering_schema?: string
  save_as?: string
  output_grouping_axes?: string[]
}

interface ClusteringConfig {
  reduction_dimensions: number
  clustering_method: string
  layer_cluster_counts: Record<number, number>
  embedding_source?: string
  reduction_method?: string
  clustering_dimensions?: number[]
}

interface AnalyzeClusterRoutesRequest {
  session_id?: string
  session_ids?: string[]
  window_layers: number[]
  clustering_config: ClusteringConfig
  filter_config?: FilterConfig
  top_n_routes: number
  clustering_schema?: string
  save_as?: string
  output_grouping_axes?: string[]
}

interface SankeyNode {
  name: string
  id: string
  layer: number
  expert_id: number
  token_count: number
  label_distribution?: Record<string, number>
  target_word_distribution?: Record<string, number>
  category_distributions?: Record<string, Record<string, number>>
  specialization: string
  tokens?: ProbeExample[]
}

interface SankeyLink {
  source: string
  target: string
  value: number
  probability: number
  route_signature: string
  label_distribution?: Record<string, number>
  target_word_distribution?: Record<string, number>
  category_distributions?: Record<string, Record<string, number>>
  token_count: number
}

interface TopRoute {
  signature: string
  count: number
  coverage: number
  avg_confidence: number
  example_tokens: ProbeExample[]
}

interface DynamicAxis {
  id: string
  label: string
  label_a: string
  label_b: string
  values?: string[]
}

interface RouteAnalysisResponse {
  session_id: string
  window_layers: number[]
  nodes: SankeyNode[]
  links: SankeyLink[]
  top_routes: TopRoute[]
  statistics: RouteStatistics
  available_axes?: DynamicAxis[]
  output_available_axes?: DynamicAxis[]
  probe_assignments?: Record<string, Record<string, number>>
}

interface RouteDetailsResponse {
  signature: string
  window_layers: number[]
  tokens: ProbeExample[]
  count: number
  coverage: number
  avg_confidence: number
  category_breakdown: Record<string, any>
}

interface ExpertDetailsResponse {
  layer: number
  expert_id: number
  node_name: string
  tokens: ProbeExample[]
  total_tokens: number
  usage_rate: number
  avg_confidence: number
  category_breakdown: Record<string, any>
}

// LLM Insights Types
interface LLMInsightsRequest {
  session_id: string
  windows: Record<string, any>[]
  user_prompt: string
  api_key: string
  provider?: 'openai' | 'anthropic'
}

interface LLMInsightsResponse {
  narrative: string
  statistics: Record<string, any>
}

// Trajectory Types
interface TrajectoryCoordinate {
  layer: number
  x: number
  y?: number
  z?: number
  [key: string]: number | undefined
}

interface TrajectoryPath {
  probe_id: string
  target: string
  label?: string
  coordinates: TrajectoryCoordinate[]
}

interface TrajectoryResponse {
  trajectories: TrajectoryPath[]
  metadata: {
    layers: number[]
    n_dims: number
    total_trajectories: number
    session_id: string
    max_requested: number
  }
}

// Sentence Experiment Types
interface SentenceExperimentRequest {
  sentence_set_name: string
  session_name?: string
  generate_output?: boolean
}

interface SentenceExperimentResponse {
  session_id: string
  session_name: string
  total_probes: number
  labels: string[]
  counts: Record<string, number>
}

// On-demand reduction types
interface ReductionRequest {
  session_ids: string[]
  layers: number[]
  source?: string
  method?: string
  n_components?: number
}

interface ReductionPoint {
  probe_id: string
  session_id: string
  layer: number
  x: number
  y?: number
  z?: number
  coordinates?: number[]
  target_word: string
  label?: string
  categories?: Record<string, string>
}

interface ReductionResponse {
  points: ReductionPoint[]
  layers: number[]
  method: string
  n_components: number
}

// --- Scaffold Step Types ---

interface ScaffoldTemplate {
  id: string
  name: string
  description: string
  prompt: string
  data_sources: string[]
  output_type: 'narrative' | 'element_labels'
}

interface ScaffoldStepRequest {
  session_id: string
  step_id: string
  prompt: string
  data_sources: string[]
  output_type: string
  expert_windows?: any[] | null
  cluster_windows?: any[] | null
  previous_outputs?: string[] | null
  api_key: string
  provider?: string
}

interface ScaffoldStepResponse {
  narrative?: string | null
  element_labels?: Record<string, string> | null
}

// Clustering Schema Types
interface ClusteringSchema {
  name: string
  created_at: string
  created_by: string
  params: {
    clustering_method: string
    reduction_method: string
    reduction_dimensions: number
    n_clusters?: number
    embedding_source: string
    [key: string]: any
  }
  windows?: number[][]
}

// Export all types
export type {
  ExecutionResponse,
  CaptureManifest,
  SessionStatus,
  SessionListItem,
  SessionDetailResponse,
  ProbeExample,
  RouteStatistics,
  FilterConfig,
  AnalyzeRoutesRequest,
  ClusteringConfig,
  AnalyzeClusterRoutesRequest,
  RouteAnalysisResponse,
  SankeyNode,
  SankeyLink,
  TopRoute,
  RouteDetailsResponse,
  ExpertDetailsResponse,
  LLMInsightsRequest,
  LLMInsightsResponse,
  DynamicAxis,
  TrajectoryCoordinate,
  TrajectoryPath,
  TrajectoryResponse,
  SentenceExperimentRequest,
  SentenceExperimentResponse,
  ReductionRequest,
  ReductionPoint,
  ReductionResponse,
  ScaffoldTemplate,
  ScaffoldStepRequest,
  ScaffoldStepResponse,
  ClusteringSchema
};
