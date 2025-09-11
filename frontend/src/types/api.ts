// API types matching backend Pydantic schemas

interface WordSource {
  source_type: 'custom' | 'pos_pure' | 'synset_hyponyms';
  source_params: {
    // For custom word lists
    words?: string[];      // Array of words to include
    label?: string;        // Category label (default: "custom")
    
    // For POS-pure words (words that are ONLY one part of speech)
    pos?: string;          // Part of speech: 'n' (noun), 'v' (verb), 'a' (adj), 'r' (adv)
    max_words?: number;    // Maximum words to mine (default: 30)
    
    // For WordNet synset hyponyms (semantic categories)
    synset_id?: string;    // WordNet synset ID (e.g., "animal.n.01")
    max_depth?: number;    // Hyponym tree depth (default: 2)
    unambiguous_only?: boolean; // Filter to single-sense words only (default: true)
  };
}

interface ProbeRequest {
  session_name: string;
  context_sources: WordSource[];
  target_sources: WordSource[];
  layers?: number[];  // Optional, defaults to [0, 1, 2] in backend
}

interface ProbeResponse {
  session_id: string;
  total_pairs: number;
  contexts: string[];
  targets: string[];
  categories: {
    contexts: Record<string, string[]>;
    targets: Record<string, string[]>;
  };
}

interface ExecutionResponse {
  started: boolean;
  probe_ids: string[];
  status_url: string;
  estimated_time?: string;  // Optional in backend
}

interface CaptureManifest {
  capture_session_id?: string;  // Added from backend manifest schema
  session_name: string;
  contexts: string[];
  targets: string[];
  context_category_assignments: Record<string, string[]>;
  target_category_assignments: Record<string, string[]>;
  layers_captured?: number[];  // Added from backend manifest schema
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
    expert_internal: string;
    expert_output: string;
    manifest: string;
  };
}

interface SessionListItem {
  session_id: string;
  session_name: string;
  created_at: string;
  probe_count: number;
  contexts: string[];
  targets: string[];
  state: string;
}

interface SessionDetailResponse {
  manifest: CaptureManifest;
  data_lake_paths: {
    tokens: string;
    routing: string;
    expert_internal: string;
    expert_output: string;
    manifest: string;
  };
  categories: {
    contexts: Record<string, string[]>;
    targets: Record<string, string[]>;
  };
}

// Expert Route Analysis Types
interface TokenExample {
  context: string
  target: string
  probe_id: string
}

interface RouteStatistics {
  total_routes: number
  total_probes: number
  routes_coverage: number
  window_layers: number[]
  [key: string]: any // Allow additional backend fields
}

interface FilterConfig {
  context_categories?: string[]
  target_categories?: string[]
  context_words?: string[]      // NEW: Specific context words  
  target_words?: string[]       // NEW: Specific target words
  max_per_category?: number     // NEW: For UI reference
}

interface AnalyzeRoutesRequest {
  session_id: string
  window_layers: number[]
  filter_config?: FilterConfig
  top_n_routes: number
}

interface ClusteringConfig {
  pca_dimensions: number
  clustering_method: string  // "kmeans" | "hierarchical" | "dbscan"
  layer_cluster_counts: Record<number, number>  // {layer: num_clusters}
}

interface AnalyzeClusterRoutesRequest {
  session_id: string
  window_layers: number[]
  clustering_config: ClusteringConfig
  filter_config?: FilterConfig
  top_n_routes: number
}

interface SankeyNode {
  name: string
  id: string
  layer: number
  expert_id: number
  token_count: number
  categories: string[]
  category_distribution: Record<string, number>
  specialization: string
  context_target_pairs: Array<{
    context: string
    targets: string[]
    target_count: number
  }>
}

interface SankeyLink {
  source: string
  target: string
  value: number
  probability: number
  route_signature: string
  category_distribution: Record<string, number>
  token_count: number
}

interface TopRoute {
  signature: string
  count: number
  coverage: number
  avg_confidence: number
  example_tokens: TokenExample[]
}

interface RouteAnalysisResponse {
  session_id: string
  window_layers: number[]
  nodes: SankeyNode[]
  links: SankeyLink[]
  top_routes: TopRoute[]
  statistics: RouteStatistics
}

interface RouteDetailsResponse {
  signature: string
  window_layers: number[]
  tokens: TokenExample[]
  count: number
  coverage: number
  avg_confidence: number
  category_breakdown: Record<string, any>
}

interface ExpertDetailsResponse {
  layer: number
  expert_id: number
  node_name: string
  tokens: TokenExample[]
  total_tokens: number
  usage_rate: number
  avg_confidence: number
  category_breakdown: Record<string, any>
}

// LLM Insights Types
interface LLMInsightsRequest {
  session_id: string
  windows: Record<string, any>[]  // Complete RouteAnalysisResponse data
  user_prompt: string
  api_key: string
  provider?: 'openai' | 'anthropic'  // defaults to 'openai'
}

interface LLMInsightsResponse {
  narrative: string
  statistics: Record<string, any>
}

// PCA Trajectory Types
interface PCACoordinate {
  layer: number
  x: number
  y?: number
  z?: number
  [key: string]: number | undefined  // for additional dimensions like dim_3, dim_4, etc.
}

interface PCATrajectory {
  probe_id: string
  context: string
  target: string
  coordinates: PCACoordinate[]
}

interface PCATrajectoryResponse {
  trajectories: PCATrajectory[]
  metadata: {
    layers: number[]
    n_dims: number
    total_trajectories: number
    session_id: string
    max_requested: number
  }
}

// Export all types for Vite compatibility - updated
export type {
  WordSource,
  ProbeRequest,
  ProbeResponse,
  ExecutionResponse,
  CaptureManifest,
  SessionStatus,
  SessionListItem,
  SessionDetailResponse,
  TokenExample,
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
  PCACoordinate,
  PCATrajectory,
  PCATrajectoryResponse
};
