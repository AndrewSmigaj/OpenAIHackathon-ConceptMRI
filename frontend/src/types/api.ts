// API types matching backend Pydantic schemas

interface WordSource {
  source_type: 'custom' | 'pos_pure' | 'synset_hyponyms';
  source_params: {
    words?: string[];
    label?: string;
    pos_tag?: string;
    synset_name?: string;
    max_words?: number;
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
// Export all types for Vite compatibility - updated
export type {
  WordSource,
  ProbeRequest,
  ProbeResponse,
  ExecutionResponse,
  CaptureManifest,
  SessionStatus,
  SessionListItem,
  SessionDetailResponse
};
