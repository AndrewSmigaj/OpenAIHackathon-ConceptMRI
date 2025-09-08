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
