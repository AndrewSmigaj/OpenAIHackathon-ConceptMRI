# Backend Architecture Review

Thorough file-by-file review of `backend/src/`. Every file read in full.
Date: 2026-04-07

---

## Table of Contents

1. [Top-Level API Layer](#1-top-level-api-layer)
2. [API Routers](#2-api-routers)
3. [Services: Probes](#3-services-probes)
4. [Services: Agent](#4-services-agent)
5. [Services: Experiments](#5-services-experiments)
6. [Services: Generation](#6-services-generation)
7. [Services: Features](#7-services-features)
8. [Core Layer](#8-core-layer)
9. [Schemas](#9-schemas)
10. [Adapters](#10-adapters)
11. [Utilities](#11-utilities)
12. [Dead Code Inventory](#12-dead-code-inventory)
13. [Data Flow Diagrams](#13-data-flow-diagrams)
14. [Issues and Inconsistencies](#14-issues-and-inconsistencies)

---

## 1. Top-Level API Layer

### `api/main.py`
**Purpose:** FastAPI application entry point. Creates the app, configures CORS, registers routers, defines health check.

**Key elements:**
- `lifespan()` (line 17): async context manager that calls `initialize_capture_service()` at startup — starts model loading in background thread.
- 8 routers registered under `/api` prefix (lines 38-45): probes, routes, clustering, insights, temporal, generation, prompts, agent.
- `/health` endpoint (line 52): returns model_loaded, loading status, GPU info, sessions_available (hardcoded True).

**Issues:**
- **Unused import** (line 8): `import time` is imported but never used.
- `sessions_available: True` is hardcoded — not meaningful.

**Dependencies:** `api.routers.*`, `api.dependencies`, `torch`

---

### `api/config.py`
**Purpose:** Centralized config. Single constant: `DATA_LAKE_PATH`.

**Key elements:**
- `_project_root` (line 9): resolves to project root via `Path(__file__).resolve().parents[3]`.
- `DATA_LAKE_PATH` (line 10): defaults to `{project_root}/data/lake/`, overridable via env var.

**No issues.** Clean, minimal.

---

### `api/dependencies.py`
**Purpose:** Dependency injection via global singletons. Provides `get_capture_service()`, `get_route_analysis_service()`, `get_cluster_analysis_service()`, `get_llm_insights_service()`.

**Key elements:**
- `_load_model_sync()` (line 41): Background thread that loads the model. Tracks loading stages: not_started → initializing → loading_model → creating_service → ready | failed.
- `initialize_capture_service()` (line 81): Starts background thread, returns immediately. Called from lifespan.
- Lazy initialization for analysis services (lines 115-142): `ExpertRouteAnalysisService`, `ClusterRouteAnalysisService`, `LLMInsightsService` created on first access.
- `sys.path.insert(0, str(backend_src))` (line 18): Modifies sys.path for import resolution.

**Design notes:**
- Simple global singleton pattern — no DI framework, appropriate for the scale.
- API serves health checks immediately while model loads in background — good UX.

**No significant issues.**

---

### `api/schemas.py`
**Purpose:** Pydantic models for all API request/response shapes. 467 lines, covers probes, routes, clustering, generation, temporal, and agent schemas.

**Key elements (organized by domain):**
- **Probes:** `ExecutionResponse`, `StatusResponse`, `SessionListResponse`, `SessionDetailResponse`, `ProbeExample`
- **Route Analysis:** `FilterConfig`, `AnalyzeRoutesRequest`, `ClusteringConfig`, `AnalyzeClusterRoutesRequest`, `SankeyNode`, `SankeyLink`, `TopRoute`, `RouteAnalysisResponse`, `RouteDetailsResponse`, `ExpertDetailsResponse`
- **LLM Insights:** `LLMInsightsRequest`, `LLMInsightsResponse`, `ScaffoldStepRequest`, `ScaffoldStepResponse`
- **Generation:** `GenerateSentenceSetRequest`, `SentenceSetResponse`, `SentenceSetDetailResponse`, `SentenceSetListResponse`, `SentenceEntry`
- **Reduction:** `ReductionRequest`, `ReductionResponse`, `ReductionPoint`
- **Temporal:** `TemporalCaptureRequest`, `TemporalCaptureResponse`, `TemporalLagDataRequest`, `TemporalLagPoint`, `TemporalLagDataResponse`
- **Agent:** `AgentStartRequest`, `AgentStartResponse`, `AgentStopRequest`, `AgentStopResponse`, `AgentGenerateRequest`, `AgentGenerateResponse`

**Issues:**
- **`SentenceEntry` naming collision** (line 39): `api/schemas.py` defines a `SentenceEntry` Pydantic model that is different from `services/generation/sentence_set.SentenceEntry` (a dataclass). Both have `text`, `group`, `target_word`, `categories` but different types (Pydantic vs dataclass).
- **`SentenceSetDetailResponse` uses legacy A/B fields** (lines 284-291): Has `label_a`, `label_b`, `description_a`, `description_b`, `sentences_a`, `sentences_b`, `sentences_neutral` — but `SentenceSet` uses N-group design with `groups: List[SentenceGroup]`. See [Issue #1](#issue-1-sentenceset-a-b-vs-n-group-mismatch).
- **`TemporalLagDataResponse` missing fields** (lines 412-416): Schema only has `points`, `regime_boundary`, `processing_mode`. But `temporal.py` router (line 489) passes extra fields `temporal_run_id` and `basin_separation` — silently dropped by Pydantic. See [Issue #2](#issue-2-temporallagdataresponse-schema-drift).
- `DynamicAxis` (line 29): has `label_a`/`label_b` — artifacts of binary design, but works for N>2 since `values` list is also present.

---

## 2. API Routers

### `api/routers/probes.py` (376 lines)
**Purpose:** Session management and sentence experiment capture endpoints.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/probes/{session_id}/status` | Session status with progress |
| GET | `/api/probes` | List all sessions |
| GET | `/api/probes/{session_id}` | Session details + sentence list |
| POST | `/api/probes/sentence-experiment` | Run sentence experiment capture |
| GET | `/api/probes/sessions/{session_id}/generated-outputs` | Read generated outputs for categorization |
| POST | `/api/probes/sessions/{session_id}/output-categories` | Write output categories back |
| GET | `/api/probes/sessions/{session_id}/clusterings` | List clustering schemas |
| GET | `/api/probes/sessions/{session_id}/clusterings/{schema_name}` | Load specific clustering schema |
| POST | `/api/probes/sessions/{session_id}/clusterings/{schema_name}/element-descriptions` | Save element descriptions |
| POST | `/api/probes/sessions/{session_id}/clusterings/{schema_name}/reports/{window_key}` | Save analysis report |

**Key data flow (sentence experiment, line 209):**
1. Load sentence set by name from `data/sentence_sets/`
2. Create session via `service.create_sentence_session()`
3. Loop through sentences, call `service.capture_probe()` for each
4. Finalize session via `service.finalize_session()`

**Issues:**
- **Route ordering problem** (lines 288, 321): FastAPI matches routes top-to-bottom. `/api/probes/sessions/{session_id}/generated-outputs` could conflict with `/api/probes/{session_id}` if "sessions" is interpreted as a session_id. However, since "sessions" is a fixed path segment after `/probes/`, this actually works correctly because `/probes/sessions/...` is a different prefix than `/probes/{session_id}`.
- Line 104: `metadata.get("session_id", session_file.stem)` — uses `metadata` variable before the `try` block fully establishes it; if `json.load(f)` succeeds but the dict lacks `session_id`, `session_file.stem` is the fallback. This is fine.
- Line 219 import inside function: `from services.generation.sentence_set import load_sentence_set_by_name` — could be top-level.

---

### `api/routers/routes.py` (164 lines)
**Purpose:** Expert route analysis endpoints.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/experiments/analyze-routes` | Analyze expert routes (Sankey data) |
| GET | `/api/experiments/route-details` | Details for a specific route |
| GET | `/api/experiments/expert-details` | Details for a specific expert |

**Key behaviors:**
- Supports named clustering schemas: `clustering_schema` loads cached results, `save_as` computes and saves.
- Pre-computes output axis variants via `_precompute_output_variants()` for fast subsequent loads.
- Default behavior: if no `output_grouping_axes` requested, applies first output axis to collapse output nodes to 2.

**No significant issues.** Uses `.dict(exclude_none=True)` which is Pydantic v1 API — should be `.model_dump(exclude_none=True)` for v2. Depends on which Pydantic version is installed.

---

### `api/routers/clustering.py` (184 lines)
**Purpose:** Cluster route analysis and on-demand dimensionality reduction.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/experiments/analyze-cluster-routes` | Analyze cluster routes (Sankey data) |
| POST | `/api/experiments/reduce` | On-demand PCA/UMAP reduction |

**Key behaviors:**
- Mirrors `routes.py` caching logic for cluster routes.
- Cluster analysis pops internal `_centroids` and `_reducers` from result before returning (line 89-90).
- Persists `probe_assignments.json` and `centroids.json` when `save_as` is provided.

**Issues:**
- Same `.dict()` vs `.model_dump()` Pydantic v1/v2 concern as routes.py (line 66).

---

### `api/routers/insights.py` (71 lines)
**Purpose:** LLM insights and scaffold step endpoints.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/experiments/llm-insights` | Generate LLM insights from routing data |
| POST | `/api/experiments/scaffold-step` | Run single scaffold analysis step |
| GET | `/api/experiments/health` | Experiments health check |

**No issues.** Clean delegation to `LLMInsightsService`.

---

### `api/routers/temporal.py` (498 lines)
**Purpose:** Temporal basin capture and lag analysis. The longest router.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/experiments/temporal-capture` | Run temporal basin transition experiment |
| GET | `/api/experiments/temporal-runs/{session_id}` | List temporal runs for a session |
| POST | `/api/experiments/temporal-lag-data` | Compute basin axis projection |

**Key behaviors:**
- `_run_temporal_capture_sync()` (line 24): 285-line function that handles both standard basin-based mode and custom sentences mode. Runs synchronously in a thread pool.
- Single-instance enforcement via `_temporal_capture_busy` global (line 21).
- Three processing modes: `expanding_cache_off`, `expanding_cache_on`, `single_cache_on`.
- Temporal lag data endpoint re-fits PCA/UMAP reducer from source session data for projection.

**Issues:**
- **Schema drift** (line 485-491): `TemporalLagDataResponse` only has 3 fields, but router passes 5 fields (`temporal_run_id`, `basin_separation` are extras). These get silently dropped.
- **Massive function** (line 24-308): `_run_temporal_capture_sync` is 285 lines with two large branches (custom sentences vs standard). Should be split.
- **Duplicate UMAP/PCA fitting logic**: Lines 402-417 duplicate the same reduction fitting code that exists in `cluster_route_analysis.py` `_perform_clustering`. No shared helper.

---

### `api/routers/generation.py` (99 lines)
**Purpose:** Sentence set CRUD and LLM generation.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/generation/sentence-sets` | List available sentence sets |
| GET | `/api/generation/sentence-sets/{name}` | Load specific sentence set |
| POST | `/api/generation/sentence-sets/generate` | Generate new sentence set via LLM |

**Issues:**
- **Critical: A/B field mismatch** (lines 44-50): Router accesses `ss.label_a`, `ss.label_b`, `ss.description_a`, `ss.description_b`, `ss.sentences_a`, `ss.sentences_b`, `ss.sentences_neutral` — but the current `SentenceSet` data model uses `groups: List[SentenceGroup]` and does NOT have these attributes. This endpoint **will crash** for any sentence set using the v3 N-group format. See [Issue #1](#issue-1-sentenceset-a-b-vs-n-group-mismatch).

---

### `api/routers/prompts.py` (39 lines)
**Purpose:** Serve scaffold prompt templates from disk.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/prompts/scaffold-templates` | Read all scaffold JSON files |

**No issues.** Simple file-serving endpoint.

---

### `api/routers/agent.py` (288 lines)
**Purpose:** Agent session lifecycle and generate tick endpoint.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/agent/start` | Create agent session (optionally auto-start loop) |
| POST | `/api/agent/stop` | Stop and finalize agent session |
| POST | `/api/agent/generate` | Execute one agent generate tick |

**Key behaviors:**
- **Note:** Router has `prefix="/agent"` (line 32), and is included with `prefix="/api"` in main.py, so actual paths are `/api/agent/start` etc.
- Single-agent enforcement via `_active_loops` dict (line 35).
- Generate tick (line 145): generate (hooks OFF) → parse harmony channels → forward pass (hooks ON) → extract at target positions → write Parquet → return analysis + action.
- Knowledge probe: optional secondary capture with a different prompt (line 247).
- Tick log written as JSONL to session directory (line 276).

**Issues:**
- Line 208: Inline import `from services.probes.integrated_capture_service import SessionBatchWriters` — could be top-level since it's in the same module tree.
- Line 128: `status.current_turn_id` is accessed after `validate_active_session` but if session was already finalized and no longer active, this would have raised. The flow is correct.

---

### `api/routers/route_utils.py` (105 lines)
**Purpose:** Shared helpers for rebuilding output nodes across expert and cluster route endpoints.

**Key functions:**
- `_rebuild_output_nodes()` (line 14): Strips existing output nodes from cached result, rebuilds with dynamic grouping axes. Loads token records from Parquet.
- `_precompute_output_variants()` (line 87): Pre-computes all single-axis and pair-axis output variants and saves to cache for fast subsequent loads.

**No issues.** Well-factored shared code.

---

## 3. Services: Probes

### `services/probes/capture_orchestrator.py` (134 lines)
**Purpose:** Model inference and hook lifecycle management. Wraps the GPU.

**Key class:** `CaptureOrchestrator`
- `initialize_hooks()` (line 32): Lazy creation of `EnhancedRoutingCapture`, registers hooks.
- `cleanup_hooks()` (line 41): Removes hooks, frees GPU cache.
- `run_forward_pass()` (line 55): Single forward pass with optional KV cache.
- `generate_continuation()` (line 77): Temporarily removes hooks, runs `model.generate()`, re-registers hooks.
- `generate_continuation_with_ids()` (line 101): Same but returns raw token IDs too.
- `get_captured_data()` (line 127): Returns routing_data, embedding_data, residual_stream_data dicts.

**Design:** Clean boundary — everything GPU touches lives here.

**No significant issues.**

---

### `services/probes/integrated_capture_service.py` (329 lines)
**Purpose:** Facade over SessionManager, ProbeProcessor, CaptureOrchestrator. The main service that routers interact with.

**Key class:** `IntegratedCaptureService`

**Nested class:** `SessionBatchWriters` (line 32)
- Coordinated batch writers for 4 Parquet files: tokens, routing, embeddings, residual_streams.
- Uses `BatchWriter` from `core/parquet_writer.py`.

**Key methods:**
- `create_sentence_session()` (line 125): Creates session + batch writers.
- `capture_probe()` (line 140): Full probe capture pipeline — validate session, init hooks, tokenize, forward pass, convert to schemas, optionally generate continuation, write to Parquet.
- `probe_tick()` (line 238): KV-cached forward pass for agent sessions — captures at ALL target word positions.
- `finalize_session()` (line 302): Closes writers, creates manifest, cleans up hooks.
- `abort_session()` (line 323): Emergency cleanup.

**Data flow for `capture_probe()`:**
1. Validate session (restore from disk if needed)
2. Initialize hooks (lazy)
3. Tokenize input, find target word position
4. Clear captured data, run forward pass
5. Extract routing/embedding/residual data
6. Convert to schema records via `ProbeProcessor.convert_to_schemas()`
7. Optionally generate continuation text
8. Write to Parquet via `SessionBatchWriters`
9. Update progress counter

**Issues:**
- Line 154: Return type annotation `Tuple[str, any]` — `any` should be `Any` (from typing) or `Optional[object]`. Currently works but is technically incorrect.
- The `capture_probe()` method has 17 parameters — a very wide interface. Categories dict, temporal metadata, and agent metadata are all passed through.

---

### `services/probes/probe_processor.py` (222 lines)
**Purpose:** Text processing and schema conversion. No model inference, no I/O, no GPU.

**Key class:** `ProbeProcessor`

**Key methods:**
- `find_word_token_position()` (line 44): Finds target word in tokenized sequence. Handles BPE whitespace sensitivity (tries both "word" and " word"). Returns last occurrence.
- `find_all_word_token_positions()` (line 77): Like above but returns ALL occurrences. Returns empty list instead of raising.
- `convert_to_schemas()` (line 109): Converts raw capture data to `ProbeCapture` dataclass containing `ProbeRecord`, `RoutingRecord`s, `EmbeddingRecord`s, `ResidualStreamState`s. Extracts at target position (semantic pos=1) and optionally context position (semantic pos=0).

**Data class:** `ProbeCapture` (line 26) — bundles all capture data for one probe.

**Design:** Clean separation — pure data transformation, no side effects.

**No issues.**

---

### `services/probes/session_manager.py` (291 lines)
**Purpose:** Session lifecycle management. No model knowledge.

**Key class:** `SessionManager`

**Enums/dataclasses:**
- `SessionState` (line 26): ACTIVE, COMPLETED, FAILED, PAUSED
- `SessionStatus` (line 34): Runtime tracking including probe counts, current_turn_id for agents

**Key methods:**
- `create_session()` (line 78): Creates session JSON file in `_sessions/` dir. Returns session_id.
- `create_agent_session()` (line 121): Agent variant with scenario_id, target_words, bootstrap_session_id.
- `get_session_status()` (line 171): Returns status, loading from disk if not in memory.
- `validate_active_session()` (line 190): Ensures session is active, restoring from disk if needed. Used by capture_probe().
- `finalize_session()` (line 220): Creates manifest Parquet, updates session JSON, removes from active_sessions.
- `_restore_session()` (line 268): Restores active session from disk. For agent sessions, recovers turn_id from tick_log line count.

**Design note:** Sessions persist to JSON files in `data/lake/_sessions/`. This allows recovery after server restart.

**No significant issues.**

---

### `services/probes/probe_ids.py` (35 lines)
**Purpose:** UUID-based ID generation.

**Functions:**
- `generate_probe_id()`: Returns `"probe_{hex8}"`
- `generate_capture_id()`: Returns `"{prefix}_{hex8}"` — used for session IDs, capture IDs, temporal run IDs.

**Note:** Only 8 hex chars = 32 bits of entropy = ~4 billion unique IDs. Fine for research use but would collide in production. Not a real issue here.

---

### `services/probes/routing_capture.py` (217 lines)
**Purpose:** PyTorch hook registration for MoE routing, expert output, and residual stream capture.

**Key class:** `EnhancedRoutingCapture`

**Hook types:**
1. **MLP combined hook** (line 74): Registered on the MoE block. Captures:
   - Routing weights (softmaxed) via adapter or manual computation
   - Gate entropy
   - MLP output (expert collective output) → stored as embedding_data
2. **Residual hook** (line 128): Registered on decoder layer. Captures full residual stream output.

**Data storage:** Three dicts keyed by `"layer_{N}"`:
- `routing_data`: routing_weights, gate_entropy, shape, num_experts
- `embedding_data`: embedding tensor, shape
- `residual_stream_data`: residual_stream tensor, shape

**Other methods:**
- `extract_highways()` (line 169): Build highway signatures from routing data. Not used by main pipeline (analysis builds signatures from Parquet data).
- `get_summary()` (line 191): Summary statistics. Not used by main pipeline.

**Issues:**
- `extract_highways()` and `get_summary()` appear to be **unused** by any caller. They were likely useful during development but are now dead methods.

---

## 4. Services: Agent

### `services/agent/agent_loop.py` (279 lines)
**Purpose:** Automated scenario loop — connects to Evennia, plays scenarios, captures probe data with KV cache.

**Key class:** `AgentLoop`

**Flow (per scenario):**
1. Load scenario YAML from `data/worlds/scenarios/`
2. Teleport agent to scenario room
3. Bootstrap: system prompt + initial "look"
4. Loop up to `max_ticks`:
   a. Capture game text via `service.probe_tick()` (KV cache)
   b. Generate action from full token history
   c. Parse harmony channels (analysis + action)
   d. Send action to Evennia
   e. Write tick log
   f. Check for `[SCENARIO_COMPLETE]` in response
5. Record result to `probe_results.jsonl`

**Constants:**
- `SYSTEM_PROMPT` (line 22): Fixed prompt instructing agent how to interact with MUD world.
- `SCENARIOS_DIR` (line 49): `data/worlds/scenarios/`

**Design notes:**
- Uses `service.probe_tick()` for capture — specialized method that does forward pass with KV cache and captures at all target word positions.
- Action lookup built from scenario YAML — maps commands to metadata (correct/incorrect, canary, etc.).

**No significant issues.** Well-structured async loop.

---

### `services/agent/evennia_client.py` (151 lines)
**Purpose:** Async WebSocket client for Evennia MUD server.

**Key class:** `EvenniaClient`

**Protocol:** JSON arrays matching Evennia's WebSocket protocol:
- Send: `["text", ["command"], {}]`
- Recv: `["text", ["..."], {}]` or `["prompt", [">>>"], {}]`

**Key methods:**
- `connect()`: WebSocket connect, sets raw mode, starts reader task.
- `authenticate()`: Sends connect command, waits for `logged_in` signal.
- `send_command()`: Sends text command.
- `read_until_prompt()`: Accumulates text until prompt sentinel, strips ANSI codes.
- `disconnect()`: Sends quit, cancels reader, closes WebSocket.

**Design:** Clean async implementation with proper timeout handling.

**No significant issues.**

---

### `services/agent/harmony_parser.py` (46 lines)
**Purpose:** Extract `<analysis>` and `<action>` tags from model output.

**Function:** `parse_harmony_channels(text)` → `{"analysis": str, "action": str, "raw": str}`

**Behavior:** Uses `str.find()` (not regex). If no valid tags found, treats entire output as action with warning.

**No issues.** Simple and correct.

---

## 5. Services: Experiments

### `services/experiments/expert_route_analysis.py` (426 lines)
**Purpose:** Analyze expert routing patterns for Sankey visualization.

**Key class:** `ExpertRouteAnalysisService`

**Key methods:**
- `analyze_session_routes()` (line 29): Main entry point. Loads data, applies filters, extracts routes, builds Sankey data.
- `get_route_details()` (line 83): Details for a specific route signature.
- `get_expert_details()` (line 113): Details for a specific expert.
- `_load_session_data()` (line 160): Loads routing.parquet + tokens.parquet + manifest.
- `_load_multi_session_data()` (line 186): Merges multiple sessions, prefixing probe_ids.
- `_extract_target_routes()` (line 248): Groups probes by highway signature within window layers.
- `_build_sankey_data()` (line 305): Builds nodes and links for Sankey diagram.

**Design notes:**
- Uses `route_analysis_common` for shared functions.
- Output category layer built via `build_output_category_layer()` from `output_category_nodes.py`.
- Nodes include full probe_ids list for output node rebuilding.

**Issues:**
- `_load_session_data()` (line 165): Tries `session_{session_id}` then `{session_id}` — double path lookup. This is a legacy compatibility pattern.
- `_build_sankey_data()` (line 305) and `_extract_target_routes()` (line 248) are ~100 lines each of tight loop logic — functional but could be clearer.

---

### `services/experiments/cluster_route_analysis.py` (520 lines)
**Purpose:** On-demand clustering analysis — loads raw embeddings, reduces dimensionality, clusters, builds Sankey data.

**Key class:** `ClusterRouteAnalysisService`

**Key methods:**
- `analyze_session_cluster_routes()` (line 47): Main entry. Loads embeddings, reduces, clusters, builds routes and Sankey data.
- `_perform_clustering()` (line 249): Core ML pipeline — PCA/UMAP reduction then KMeans/hierarchical/DBSCAN per layer. Returns assignments, centroids, and fitted reducers.
- `_extract_target_cluster_routes()` (line 367): Groups probes by cluster signature.
- `_build_sankey_data()` (line 419): Builds Sankey nodes/links from cluster routes.

**Persistence:** When `save_as` is provided, persists `probe_assignments.json` and `centroids.json` to the clustering schema directory. Also writes `probe_assignments.json` at session root level for temporal endpoint (line 120-123).

**Issues:**
- **SOURCE_CONFIG duplication** (lines 29-38): Same dict defined in `reduction_service.py`. Should be shared.
- **UMAP/PCA fitting logic duplication**: Same fallback pattern (try UMAP, fall back to PCA) appears in `_perform_clustering()`, `temporal.py:get_temporal_lag_data()`, and `reduction_service.py`. Should be a shared utility.
- Node `expert_id` field (line 485): Set to cluster ID with comment "Kept for frontend compatibility" — misleading field name.

---

### `services/experiments/route_analysis_common.py` (193 lines)
**Purpose:** Shared utilities extracted from expert and cluster route analysis.

**Functions:**
- `axis_label()`: Generate display label for an axis.
- `generate_specialization()`: Human-readable specialization from label distribution.
- `analyze_top_routes()`: Get top N most frequent routes.
- `compute_available_axes()`: Compute color axes from token records and manifest.
- `build_sankey_links()`: Build Sankey link data from transitions.

**No issues.** Clean extraction of shared logic.

---

### `services/experiments/output_category_nodes.py` (284 lines)
**Purpose:** Builds output category nodes and links for Sankey diagrams. Appends a behavioral outcome layer.

**Key function:** `build_output_category_layer()` (line 41)
- Scans probes for `output_category` or `output_category_json`.
- Groups by category, creates output nodes at `max(window_layers) + 1`.
- Supports multi-axis grouping via cross-product of axis values.
- Returns augmented nodes, links, and available output axes.

**Helper functions:**
- `is_output_node()`, `is_output_link()`, `strip_output_prefix()`, `strip_output_nodes()`: Utility functions for identifying and stripping output nodes from cached data.

**No significant issues.** Well-structured.

---

### `services/experiments/llm_insights_service.py` (243 lines)
**Purpose:** LLM-powered analysis of routing patterns.

**Key class:** `LLMInsightsService`

**Key methods:**
- `analyze_routing_patterns()` (line 23): Passes complete window data to LLM with user prompt.
- `run_scaffold_step()` (line 139): Combines prompt + data context, calls LLM, returns narrative or element labels.
- `_parse_json_labels()` (line 213): Strips markdown fences, parses JSON, handles nested keys.

**Issues:**
- **Hardcoded model names**: Line 124 uses `"gpt-5"`, line 195 uses `"gpt-5.4"`. These should probably be configurable or at least use the same model.
- **Emoji in logging** (lines 42, 136): Uses emoji in logger.info/error calls.
- `_calculate_entropy()` (line 60): Private method that is **never called** by any code path.

---

### `services/experiments/category_axis_analyzer.py` (260 lines)
**Purpose:** Groups categories into semantic axes for percentage calculations.

**Key class:** `CategoryAxisAnalyzer`

**Status:** **DEAD CODE** — this file is never imported by any other file in the codebase. It defines a `CategoryAxisAnalyzer` class with hardcoded linguistic axes (grammatical, sentiment, abstraction, etc.) but nothing uses it.

---

## 6. Services: Generation

### `services/generation/sentence_set.py` (251 lines)
**Purpose:** SentenceSet data model (N-group), validation, and I/O.

**Key data classes:**
- `SentenceEntry` (line 16): text, group, target_word, categories
- `SentenceGroup` (line 23): label, description, sentences list
- `SentenceSet` (line 29): name, version, target_word, groups list, axes, output_axes, generate_output, metadata

**Key functions:**
- `validate_sentence()`: Checks word count (10-30), punctuation, target word occurrence (exactly once), duplicates.
- `validate_sentence_set()`: Validates group/entry consistency.
- `save_sentence_set()` / `load_sentence_set()`: JSON serialization.
- `load_sentence_set_by_name()`: Recursive file search by name.
- `list_available_sentence_sets()`: Quick metadata listing.

**Design:** N-group design supports arbitrary number of groups. Version "3.0".

**No issues with this file itself.** The issue is with callers that assume A/B structure.

---

### `services/generation/sentence_generator.py` (289 lines)
**Purpose:** LLM-powered sentence generation with validation and retries.

**Key class:** `SentenceGenerator`

**Issues:**
- **Critical: Uses legacy A/B SentenceSet constructor** (lines 74-91): Creates `SentenceSet` with `label_a`, `label_b`, `sentences_a`, `sentences_b`, `sentences_neutral` — but the current `SentenceSet.__init__` expects `groups: List[SentenceGroup]`. This **will crash at runtime**. See [Issue #1](#issue-1-sentenceset-a-b-vs-n-group-mismatch).

---

## 7. Services: Features

### `services/features/reduction_service.py` (174 lines)
**Purpose:** Generic PCA/UMAP dimensionality reduction service.

**Key class:** `ReductionService`

**Key method:** `reduce_on_demand()` (line 36): Loads raw embeddings from Parquet, fits reducer per layer, returns point dicts with coordinates and probe metadata.

**Issues:**
- **SOURCE_CONFIG duplication** (lines 18-27): Same dict as in `cluster_route_analysis.py`.
- `_create_reducer()` (line 158): For UMAP, `n_neighbors=min(15, max(2, n - 1))` where `n` is `n_components`, not `n_samples`. This is likely wrong — n_neighbors should be based on the number of samples, not dimensions. However, the caller in `reduce_on_demand()` separately handles the `n_samples < 4` case.

---

## 8. Core Layer

### `core/data_lake.py` (23 lines)
**Purpose:** Data lake file path utilities.

**Status:** **DEAD CODE** — never imported by any file. The project uses `DATA_LAKE_PATH` directly from `api/config.py` instead.

---

### `core/parquet_reader.py` (49 lines)
**Purpose:** Read Parquet files and reconstruct dataclass objects.

**Function:** `read_records(file_path, dataclass_type)` — reads Parquet, calls `dataclass_type.from_parquet_dict()` on each row.

**No issues.** Clean and simple.

---

### `core/parquet_writer.py` (116 lines)
**Purpose:** Batch Parquet writer with numpy array serialization.

**Key class:** `BatchWriter`
- Accumulates records in memory, auto-flushes at `batch_size`.
- On flush: converts to Arrow table, appends to existing file if present.
- Handles numpy arrays via `serialize_array_for_parquet()`.

**Design note:** Appending to Parquet works by reading the entire existing file, concatenating, and rewriting. This is O(n) on total records but acceptable for research scale.

**Convenience function:** `write_records_batch()` — wraps `BatchWriter` in a context manager.

**No significant issues.**

---

## 9. Schemas

### `schemas/tokens.py` — ProbeRecord
Links probe_id to input text, target word, and metadata. Fields include temporal metadata (experiment_id, sequence_id, sentence_index, label), generated output fields, and agent session fields.

### `schemas/routing.py` — RoutingRecord
Full routing weights vector + top-1 extraction. Includes validation in `__post_init__`. Has `highway_signature()` free function for building route signatures.

### `schemas/embedding.py` — EmbeddingRecord
Post-expert MLP output. Includes clustering preparation utilities.

### `schemas/residual_stream.py` — ResidualStreamState
Full decoder layer output. Mirrors EmbeddingRecord structure.

### `schemas/capture_manifest.py` — CaptureManifest
Session-level metadata. Stored as single-row Parquet.

### `schemas/clustering.py` — ClusteringRecord
**DEAD CODE.** Defined but never imported. The cluster analysis service builds assignments as dicts in memory and persists as JSON, not as ClusteringRecord Parquet files.

### `schemas/experiment_manifest.py` — ExperimentManifest
**DEAD CODE.** Defined but never imported. Experiment metadata is tracked via session JSON files instead.

---

## 10. Adapters

### `adapters/base_adapter.py`
Abstract base class `ModelAdapter` with `ModelTopology`, `ModelCapabilities`, `RouterStyle`, `ExpertStyle`. Defines the interface for model-specific access patterns.

### `adapters/gptoss_adapter.py`
Concrete adapter for gpt-oss-20b. 24 layers, 32 experts, K=4, hidden_size=2880. Uses `torch.float16` and `trust_remote_code=True`.

### `adapters/olmoe_adapter.py`
Concrete adapter for OLMoE-1B-7B. 16 layers, 64 experts, K=8, hidden_size=2048. Uses `torch.bfloat16`.

### `adapters/registry.py`
Simple dict-based registry. Registers gpt-oss-20b and olmoe-1b-7b adapters with aliases.

**No issues.** Clean adapter pattern.

---

## 11. Utilities

### `utils/parquet_utils.py` (18 lines)
Numpy array serialization/deserialization for Parquet. Used by `BatchWriter` and schema `from_parquet_dict` methods.

### `utils/numpy_utils.py` (144 lines)
Array handling: ensure_numpy_array, validate_finite_array, norms, stats, cosine similarity, normalization, sparsity. Used by EmbeddingRecord and ResidualStreamState.

### `utils/errors.py` (33 lines)
**DEAD CODE.** Custom exception classes (ConceptMRIError, ModelLoadError, CaptureServiceError, GPUMemoryError, SessionError) — none are imported or used anywhere.

### `utils/memory_utils.py` (28 lines)
**DEAD CODE.** GPU memory cleanup and info functions — never imported. `CaptureOrchestrator.cleanup_hooks()` calls `torch.cuda.empty_cache()` directly.

### `utils/wordnet_mining.py` (189 lines)
**DEAD CODE.** WordNet-based word mining for semantic categories. Never imported by any file. Was likely used in earlier experiment designs.

---

## 12. Dead Code Inventory

| File | Lines | Why dead |
|------|-------|----------|
| `core/data_lake.py` | 23 | Never imported; `DATA_LAKE_PATH` used directly from `api/config.py` |
| `schemas/clustering.py` | 200 | Never imported; cluster assignments stored as JSON dicts |
| `schemas/experiment_manifest.py` | 133 | Never imported; experiment tracking uses session JSON |
| `services/experiments/category_axis_analyzer.py` | 260 | Never imported |
| `utils/errors.py` | 33 | Custom exceptions never imported |
| `utils/memory_utils.py` | 28 | GPU utils never imported; inlined in CaptureOrchestrator |
| `utils/wordnet_mining.py` | 189 | WordNet mining never imported |
| `routing_capture.extract_highways()` | ~20 | Method never called |
| `routing_capture.get_summary()` | ~20 | Method never called |
| `llm_insights_service._calculate_entropy()` | ~15 | Private method never called |
| **Total dead lines** | **~920** | |

Additionally, `backend/src/algorithms/` and `backend/src/cli/` are empty directories.

---

## 13. Data Flow Diagrams

### Probe Capture (Sentence Experiment)

```
POST /api/probes/sentence-experiment
  │
  ├── load_sentence_set_by_name() ─── data/sentence_sets/*.json
  │
  ├── service.create_sentence_session()
  │     └── SessionManager.create_session()
  │           └── writes _sessions/{session_id}.json
  │           └── creates SessionBatchWriters (4 Parquet files)
  │
  ├── for each sentence:
  │     service.capture_probe()
  │       ├── SessionManager.validate_active_session()
  │       ├── CaptureOrchestrator.initialize_hooks() [lazy]
  │       │     └── EnhancedRoutingCapture.register_hooks()
  │       │           ├── MLP hook (routing weights + expert output)
  │       │           └── Residual hook (decoder layer output)
  │       ├── ProbeProcessor.find_word_token_position()
  │       ├── CaptureOrchestrator.run_forward_pass() ─── GPU
  │       ├── CaptureOrchestrator.get_captured_data()
  │       ├── ProbeProcessor.convert_to_schemas()
  │       │     ├── ProbeRecord
  │       │     ├── RoutingRecord (per layer)
  │       │     ├── EmbeddingRecord (per layer)
  │       │     └── ResidualStreamState (per layer)
  │       ├── [optional] CaptureOrchestrator.generate_continuation()
  │       └── SessionBatchWriters.write_probe_data()
  │             ├── tokens.parquet
  │             ├── routing.parquet
  │             ├── embeddings.parquet
  │             └── residual_streams.parquet
  │
  └── service.finalize_session()
        ├── SessionBatchWriters.close_all() (flush + close)
        ├── SessionManager.finalize_session()
        │     ├── writes capture_manifest.parquet
        │     └── updates _sessions/{session_id}.json (state=completed)
        └── CaptureOrchestrator.cleanup_hooks()
```

### Agent Generate Tick

```
POST /api/agent/generate
  │
  ├── SessionManager.validate_active_session()
  ├── Tokenize prompt
  ├── CaptureOrchestrator.generate_continuation_with_ids() [hooks OFF]
  ├── parse_harmony_channels() → {analysis, action}
  ├── Concatenate prompt + generated token IDs
  ├── CaptureOrchestrator.clear_captured_data()
  ├── CaptureOrchestrator.run_forward_pass() [hooks ON]
  ├── CaptureOrchestrator.get_captured_data()
  ├── For each target word:
  │     ProbeProcessor.find_all_word_token_positions()
  │     ProbeProcessor.convert_to_schemas()
  │     SessionBatchWriters.write_probe_data()
  │     SessionManager.record_probe_success()
  ├── [optional] service.capture_probe() for knowledge probe
  ├── Write tick_log.jsonl entry
  └── Return AgentGenerateResponse
```

### Agent Auto-Start Loop

```
POST /api/agent/start (auto_start=true)
  │
  ├── SessionManager.create_agent_session()
  ├── Create AgentLoop
  ├── asyncio.create_task(_run_and_cleanup(loop))
  │     └── AgentLoop.run()
  │           ├── EvenniaClient.connect()
  │           ├── EvenniaClient.authenticate()
  │           ├── For each scenario in scenario_list:
  │           │     _run_one_scenario()
  │           │       ├── Load scenario YAML
  │           │       ├── Teleport to room
  │           │       ├── Loop ticks:
  │           │       │     ├── service.probe_tick() [KV cache]
  │           │       │     ├── generate_continuation_with_ids()
  │           │       │     ├── parse_harmony_channels()
  │           │       │     ├── send_command() to Evennia
  │           │       │     ├── read_until_prompt()
  │           │       │     └── Write tick_log.jsonl
  │           │       └── Write probe_results.jsonl
  │           └── EvenniaClient.disconnect()
  │
  └── Return AgentStartResponse
```

### Cluster Route Analysis

```
POST /api/experiments/analyze-cluster-routes
  │
  ├── Check clustering_schema cache → return if found
  │
  ├── Load raw embeddings (Parquet)
  │     embeddings.parquet or residual_streams.parquet
  ├── Load tokens.parquet + capture_manifest.parquet
  │
  ├── Apply label filters
  │
  ├── _perform_clustering() per layer:
  │     ├── Stack feature vectors
  │     ├── PCA/UMAP reduction (128D default)
  │     ├── KMeans/hierarchical/DBSCAN clustering
  │     └── Compute centroids in reduced space
  │
  ├── _extract_target_cluster_routes()
  │     └── Build cluster signatures (L0C2→L1C5→L2C1)
  │
  ├── analyze_top_routes() → top N routes
  │
  ├── _build_sankey_data() → nodes + links
  │
  ├── build_output_category_layer() → add output nodes
  │
  ├── [if save_as] Save to clusterings/{name}/:
  │     ├── cluster_windows/{window_key}.json
  │     ├── meta.json
  │     ├── probe_assignments.json
  │     ├── centroids.json
  │     └── Pre-compute output variants
  │
  └── Return RouteAnalysisResponse
```

### Session Storage Layout

```
data/lake/
├── _sessions/
│   └── {session_id}.json          # Session metadata (state, config)
├── {session_id}/
│   ├── tokens.parquet             # ProbeRecord per probe
│   ├── routing.parquet            # RoutingRecord per probe per layer
│   ├── embeddings.parquet         # EmbeddingRecord per probe per layer
│   ├── residual_streams.parquet   # ResidualStreamState per probe per layer
│   ├── capture_manifest.parquet   # Single-row session manifest
│   ├── probe_assignments.json     # Cluster assignments (written by analysis)
│   ├── temporal_runs.json         # Temporal run metadata
│   ├── tick_log.jsonl             # Agent tick entries
│   ├── probe_results.jsonl        # Agent scenario results
│   └── clusterings/
│       └── {schema_name}/
│           ├── meta.json
│           ├── probe_assignments.json
│           ├── centroids.json
│           ├── element_descriptions.json
│           ├── expert_windows/
│           │   ├── w_0_1_2.json
│           │   └── w_0_1_2__out_axis.json
│           ├── cluster_windows/
│           │   ├── w_0_1_2.json
│           │   └── w_0_1_2__out_axis.json
│           └── reports/
│               └── {window_key}.md
```

---

## 14. Issues and Inconsistencies

### Issue #1: SentenceSet A/B vs N-group Mismatch

**Severity: CRITICAL (runtime crash)**

The `SentenceSet` data model (`services/generation/sentence_set.py`) was migrated to N-group design (v3) using `groups: List[SentenceGroup]`. However, multiple files still assume the old A/B structure:

1. **`services/generation/sentence_generator.py` lines 74-91**: Constructs `SentenceSet` with `label_a`, `label_b`, `sentences_a`, `sentences_b`, `sentences_neutral` — fields that don't exist on the current dataclass. **Will crash at runtime** when generating sentence sets via API.

2. **`api/routers/generation.py` lines 44-50**: Accesses `ss.label_a`, `ss.label_b`, `ss.sentences_a`, etc. **Will crash** for the `GET /api/generation/sentence-sets/{name}` endpoint with v3 format sentence sets.

3. **`api/schemas.py` `SentenceSetDetailResponse` lines 284-291**: Response schema has `label_a`, `label_b`, `sentences_a`, `sentences_b`, `sentences_neutral` — matching the old format.

**Impact:** The generation API endpoints are broken for the current sentence set format. The `POST /api/probes/sentence-experiment` endpoint works because it uses `ss.groups` directly (probes.py line 228).

**Fix:** Either add backward-compatible properties to `SentenceSet` that derive A/B from groups, or update the generation router and schemas to use the N-group format.

---

### Issue #2: TemporalLagDataResponse Schema Drift

**Severity: LOW (data loss, not crash)**

The `TemporalLagDataResponse` Pydantic model (schemas.py line 412) only has 3 fields: `points`, `regime_boundary`, `processing_mode`.

But `temporal.py` line 485-491 constructs the response with 5 fields:
```python
return TemporalLagDataResponse(
    points=points,
    regime_boundary=...,
    processing_mode=...,
    temporal_run_id=...,     # not in schema
    basin_separation=...,    # not in schema
)
```

Pydantic v2 silently ignores extra fields by default. The `temporal_run_id` and `basin_separation` data never reaches the frontend.

**Fix:** Add `temporal_run_id: str = ""` and `basin_separation: float = 0.0` to `TemporalLagDataResponse`.

---

### Issue #3: Duplicate UMAP/PCA Fitting Logic

**Severity: LOW (maintainability)**

The same UMAP-with-PCA-fallback pattern appears in three places:
1. `cluster_route_analysis.py` `_perform_clustering()` (lines 294-309)
2. `temporal.py` `get_temporal_lag_data()` (lines 402-417)
3. `reduction_service.py` `_create_reducer()` + caller (lines 128-133, 158-173)

Each has slightly different n_neighbors logic and error handling. Should be a shared utility.

---

### Issue #4: SOURCE_CONFIG Duplication

**Severity: LOW (maintainability)**

`SOURCE_CONFIG` dict mapping source names to Parquet filenames is defined identically in:
1. `services/experiments/cluster_route_analysis.py` (lines 29-38)
2. `services/features/reduction_service.py` (lines 18-27)

Should be defined once and imported.

---

### Issue #5: Pydantic v1 vs v2 API

**Severity: LOW (future breakage)**

Several files use `.dict()` (Pydantic v1 API):
- `routes.py` line 61: `request.filter_config.dict(exclude_none=True)`
- `clustering.py` line 66: `request.clustering_config.dict(exclude_none=True)`

In Pydantic v2, `.dict()` is deprecated in favor of `.model_dump()`. Both currently work but will produce deprecation warnings.

---

### Issue #6: ~920 Lines of Dead Code

**Severity: MEDIUM (clarity)**

See [Dead Code Inventory](#12-dead-code-inventory). Nearly 1000 lines of never-imported code adds confusion for readers. Files:
- `core/data_lake.py`
- `schemas/clustering.py`
- `schemas/experiment_manifest.py`
- `services/experiments/category_axis_analyzer.py`
- `utils/errors.py`
- `utils/memory_utils.py`
- `utils/wordnet_mining.py`

Plus dead methods in `routing_capture.py` and `llm_insights_service.py`.

---

### Issue #7: Unused `time` Import in main.py

**Severity: TRIVIAL**

Line 8: `import time` — never used.

---

### Issue #8: Inconsistent Hardcoded Model Names in LLMInsightsService

**Severity: LOW**

`llm_insights_service.py` uses `"gpt-5"` on line 124 and `"gpt-5.4"` on line 195. The two code paths (analyze_routing_patterns vs run_scaffold_step) use different OpenAI models for no apparent reason.

---

### Issue #9: `n_neighbors` Bug in ReductionService

**Severity: LOW (functional but wrong)**

`reduction_service.py` line 169:
```python
n_neighbors=min(15, max(2, n - 1)),
```
Here `n` is `n_components` (number of dimensions), not `n_samples`. UMAP's `n_neighbors` should be based on sample count, not component count. This works accidentally because n_components is typically small (3) and the result (2) happens to be a valid n_neighbors value, but it's semantically wrong.

---

### Issue #10: SentenceEntry Naming Collision

**Severity: TRIVIAL (no runtime impact)**

`api/schemas.py` defines a Pydantic `SentenceEntry` class (line 39), and `services/generation/sentence_set.py` defines a dataclass `SentenceEntry` (line 16). They have the same fields but are different types. No file imports both, so no collision occurs, but it's confusing for readers.
