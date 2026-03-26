// Types for temporal analysis — basin transition experiments

export interface TemporalCaptureRequest {
  session_id: string
  basin_a_cluster_id: number
  basin_b_cluster_id: number
  basin_layer: number
  sentences_per_block?: number
  processing_mode?: string
  sequence_config?: string
  clustering_schema?: string
  run_label?: string
  generate_output?: boolean
}

export interface TemporalCaptureResponse {
  temporal_run_id: string
  new_session_id: string
  sequence_positions: number
  regime_boundary: number
  processing_mode: string
  basin_a_sentences: number
  basin_b_sentences: number
}

export interface TemporalRunMetadata {
  temporal_run_id: string
  new_session_id: string
  processing_mode: string
  sequence_config: string
  basin_a_cluster_id: number
  basin_b_cluster_id: number
  basin_layer: number
  clustering_schema: string | null
  sentences_per_block: number
  regime_boundary: number
  sequence_positions: number
  sentence_texts: Record<string, string>  // position (as string) → individual sentence
}

export interface TemporalLagPoint {
  position: number
  regime: string          // "A" or "B"
  projection: number      // 0.0 = basin A, 1.0 = basin B
  sentence_text: string
  probe_id: string
  target_word: string
}

export interface TemporalLagData {
  points: TemporalLagPoint[]
  regime_boundary: number
  processing_mode: string
  temporal_run_id: string
  basin_separation: number
}

// Basin option derived from cluster route data for the selection UI
export interface BasinOption {
  clusterId: number
  layer: number
  label: string                // e.g. "L22C3 — aquarium (87%)"
  dominantCategory: string
  purity: number
  tokenCount: number
}

// Condition group: runs sharing the same schema + basins + mode + config
export interface RunGroup {
  key: string                  // e.g. "polysemy_test_1_5_4_23_expanding_cache_on_block_ab"
  label: string                // e.g. "L23C5→L23C4 cache_on"
  color: string                // base color for this condition
  runs: TemporalRunMetadata[]
}

// Aggregate (mean) line computed from multiple runs in a group
export interface AggregateLine {
  positions: number[]
  meanProjection: number[]
  stdProjection: number[]      // ±1 std dev at each position
}
