# Architecture Review — Concept MRI

*Review date: 2026-03-24*

## Executive Summary

Concept MRI is well-engineered with a single model and small datasets. The **data schema design and adapter pattern are exemplary** — proper contracts, immutable topologies, clean model abstraction. The **color system and visualization layer are thoughtful** — N-way categorical blending, traffic-based scaling, multi-window Sankey orchestration.

Recent refactoring addressed the three highest-severity issues: IntegratedCaptureService was decomposed into SessionManager, ProbeProcessor, and CaptureOrchestrator; shared analysis code was extracted into `route_analysis_common.py`; and ExperimentPage state was reorganized into three custom hooks. Logging was standardized across all services.

The codebase is production-ready for the current feature set. Remaining work centers on configuration centralization, request caching, and test coverage.

---

## Backend

### Data Architecture

**Current Design**: Parquet-based data lake with session-level isolation (`data/lake/{session_id}/`). Each session stores tokens.parquet, routing.parquet, embeddings.parquet, residual_streams.parquet, and capture_manifest.parquet. Session metadata lives in `_sessions/*.json`. Clustering schemas are nested under sessions (`clusterings/{schema_name}/`).

**Strengths**:
- 5-schema separation (tokens, routing, embeddings, residual streams, manifest) is clean and purpose-built
- Explicit `to_parquet_dict` / `from_parquet_dict` methods on all schemas ensure serialization correctness
- Session-level isolation prevents cross-contamination
- Self-describing files (no external database needed)

**Concerns**:
- Clustering schemas nested under sessions creates coupling — cross-session analysis would need to read from multiple directories
- `_sessions/*.json` is a second source of truth alongside in-memory `active_sessions` dict. If a capture crashes mid-session, the JSON metadata can become stale
- No schema versioning on Parquet files — adding a field to ProbeRecord would silently break reads of older sessions
- No cross-session aggregation infrastructure (can't ask "across 50 sessions, which experts co-activate?")

**Recommendation**: Accept for now. The session isolation is correct for single-user research workflows. If cross-session analysis becomes important, extract clustering schemas to a top-level directory.

### Schema Layer

**Rating: Excellent**

The Pydantic schema design is the strongest part of the backend:
- `ModelTopology` is a frozen dataclass with all model-specific constants (`num_layers`, `num_experts`, `top_k`, `hidden_size`, `router_style`)
- `ProbeRecord`, `RoutingRecord`, `EmbeddingRecord`, `ResidualStreamState` are well-typed with explicit field documentation
- Routing signatures (`"L0E18→L1E11→L2E14"`) are unambiguous and parseable
- `CaptureManifest` provides provenance (session name, model, creation time, layer list)

No changes recommended. This is a foundation worth preserving.

### Adapter Pattern

**Rating: Excellent**

The `ModelAdapter` abstraction is textbook:
- ABC base class (`BaseModelAdapter`) with `load_model()`, `layers_range()`, `compute_routing_weights()`, `get_residual_stream()`
- Two implementations (`GptOssAdapter`, `OLMoEAdapter`) handle different router styles (TOPK_THEN_SOFTMAX vs SOFTMAX_THEN_TOPK)
- Registry pattern enables runtime model selection: `get_adapter("gpt-oss-20b")` or `get_adapter("openai/gpt-oss-20b")`
- Topology immutability (`frozen=True`) prevents runtime mutations
- No model-specific knowledge leaks outside the adapter

Sufficient for a second model with minimal changes. The main gap: `dependencies.py` hardcodes `"gpt-oss-20b"` rather than reading from config.

### Service Layer

**Rating: Good with significant debt**

**IntegratedCaptureService** (resolved):
Decomposed into three focused components:
- `SessionManager`: session lifecycle (create, track, restore, finalize, abort) — testable without GPU
- `ProbeProcessor`: tokenization and schema conversion — testable without GPU
- `CaptureOrchestrator`: model inference, hook lifecycle, GPU memory
- `IntegratedCaptureService` is now a thin facade preserving the original public API

**ExpertRouteAnalysisService vs ClusterRouteAnalysisService** (resolved):
Shared logic (~360 lines) extracted into `route_analysis_common.py` as free functions:
- `axis_label`, `generate_specialization`, `analyze_top_routes`, `compute_available_axes`, `build_sankey_links`
- Free functions chosen over base class because the services don't share lifecycle or state

**OutputCategoryNodes**:
- `_axis_label` duplication removed (imports from common module)
- `_generate_output_specialization` renamed to distinguish from common version

### API Design

**Rating: Good**

- RESTful naming: `/api/probes/...`, `/api/experiments/...`, `/api/generation/...`
- Proper HTTP methods (GET for reads, POST for actions)
- Dependency injection via FastAPI `Depends()`
- Lazy initialization of analysis services (no startup cost)

**Concerns**:
- Error handling is per-endpoint with no consistent middleware
- The temporal capture endpoint is 150+ lines of business logic inline in the route handler — should be extracted to a service
- A few intentionally untyped `Dict[str, Any]` remain (LLM pass-through data, extensible metadata)

### Cross-Cutting: Logging

**Rating: Good** (recently improved)

- All service files now use `logging.getLogger(__name__)` with appropriate levels
- `main.py` retains `print()` for startup banner (conventional for FastAPI)
- No request/response logging middleware
- No performance metrics

### Cross-Cutting: Configuration

**Rating: Needs work**

- `.env.example` exists with good structure but many values are hardcoded in code:
  - Model name (`"gpt-oss-20b"`) in dependencies.py
  - Batch size (1000) in SessionBatchWriters
  - Reduction defaults (PCA128, n_neighbors=15) in reduction_service
  - Sentence sets dir computed via Path manipulation
- No centralized `Config` class or settings module

### Cross-Cutting: Error Recovery

**Rating: Adequate**

- Probe capture: `except Exception: continue` skips failed sentences (resilient, with proper error logging)
- Model loading: catches exception, logs error, starts in limited mode
- SessionManager tracks failed probe counts and error messages
- Session restoration from disk allows recovery of interrupted sessions

---

## Frontend

### Component Architecture

**ExperimentPage.tsx** (resolved):

State was reorganized from 34 useState declarations into three custom hooks:
- `useAxisControls()` — 11 state vars + 6 useMemo derivations for color/shape encoding
- `useClusteringConfig()` — 9 state vars for clustering parameters
- `useSchemaManagement()` — 3 state vars + 2 effects for schema lifecycle

The page component retains ~12 state vars for session management, route data, and card selection. Child component interfaces are unchanged.

**Remaining concern**: Color props are still drilled through 3 levels. A React context could eliminate this, but the tree is shallow enough that the current approach works.

**Other components are well-designed**:
- `SankeyChart`: Pure visualization, no business logic
- `MultiSankeyView`: Orchestrates window loading + renders chart array
- `WindowAnalysis`: Self-contained statistical panel with chi-square table
- `ContextSensitiveCard`: Handles 4 card types (expert, highway, cluster, route)
- `SteppedTrajectoryPlot`: Isolated 3D visualization with stratified sampling

### Color System

**Rating: Excellent**

`colorBlending.ts` is the best-factored utility in the codebase:
- Pure functions, no hidden state
- Binary gradients for 2-value axes, distinct categorical palette for N>2
- 5 gradient schemes with auto-pairing table
- Traffic-based visual properties (opacity, width) scale by square root
- `getAxisColor()`, `getNodeColor()`, `getPointColor()` cover all use cases

### API Client

**Rating: Good**

- Methods map 1:1 to backend routes
- Response types explicitly imported
- `ApiError` class includes status code and response body
- Polling helper for long-running operations
- No hardcoded credentials

**Concern**: No request caching — axis changes trigger re-fetches for all 6 windows even if only colors changed (not data).

### Type System

**Rating: Good**

- Core types (SankeyNode, SankeyLink, RouteAnalysisResponse) are well-defined
- Backend API schemas now use typed Pydantic models (ProgressInfo, RouteStatistics, DynamicAxis, etc.) instead of Dict[str, Any]
- Frontend types match backend: SankeyNode.probe_ids and SankeyLink.tokens declared
- `SelectedCard` uses `data: any` — could be improved to a discriminated union

### Performance

No critical issues for current dataset sizes. Potential concerns at scale:
- SankeyChart re-renders on every color change (no React.memo)
- SteppedTrajectoryPlot re-samples trajectories on parameter change (no cache)
- All 6 windows re-fetch on axis change (should only re-render with new colors)

---

## Claude Code Integration

### Skills Scaffolding

**Rating: Good**

5 skills cover the full pipeline: `/probe`, `/pipeline`, `/categorize`, `/analyze`, `/server`. Each is a focused runbook for one stage.

**Strengths**:
- Skills are prescriptive without being rigid — they guide Claude's reasoning, not just its commands
- `/analyze` explicitly says "read actual sentences" and "reason about WHY" — using LLMs for what they're good at
- `/probe` covers confound analysis and factorial design — domain expertise encoded
- Pipeline doc has USER GATES — human stays in control

**Concerns**:
- Skills reference PIPELINE.md (now docs/PIPELINE.md) — paths may drift (just updated in this session)
- `/pipeline` stage 5 says "analysis protocol TBD" — still partially incomplete
- No skill dependency tracking — `/analyze` assumes `/categorize` was already run but doesn't verify
- No skill versioning — changes to a skill silently affect all future invocations

### PIPELINE.md as Orchestration

**Rating: Good**

Clear 6-stage state machine with concrete API calls and explicit user gates. Claude can determine what stage an experiment is at by running 5 checks in sequence.

**Concern**: As the pipeline grows (temporal analysis, multi-model), PIPELINE.md will become long. May need to split into per-stage docs that the pipeline doc indexes.

---

## Priority Matrix

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| IntegratedCaptureService overloaded | High | **Resolved** | Decomposed into SessionManager, ProbeProcessor, CaptureOrchestrator |
| Analysis service code duplication (~40%) | High | **Resolved** | Extracted to route_analysis_common.py |
| ExperimentPage god component | High | **Resolved** | State extracted into 3 custom hooks |
| Logging strategy (print → structured) | Medium | **Resolved** | All services use logging module |
| API schema loose typing (Dict[str, Any]) | Medium | **Resolved** | Typed Pydantic models added |
| Frontend type mismatches | Medium | **Resolved** | SankeyNode.probe_ids, SankeyLink.tokens declared |
| Color prop drilling (12+ props × 3 levels) | Medium | Open | Extract to context when tree deepens |
| Configuration hardcoding | Medium | Open | Fix when adding second model |
| Temporal endpoint inline logic | Medium | Open | Fix when expanding temporal feature |
| Session state dual-source | Medium | Open | SessionManager mitigates but doesn't eliminate |
| Reduction service memory (dense matrices) | Low | Open | Fix when hitting OOM |
| Missing request caching in frontend | Low | Open | Fix when performance is noticeable |
| No tests | Low | Open | Add targeted tests for adapters and schemas |
| No cross-session analysis | Low | Open | Design when needed |

---

## What's Worth Preserving

1. **Schema layer** — don't touch it. The Parquet contracts are solid.
2. **Adapter pattern** — extend, don't restructure. Add adapters, don't change the interface.
3. **Color system** — best utility in the codebase. Keep pure functional approach.
4. **Skills architecture** — the runbook pattern works. Add skills, refine existing ones.
5. **Session isolation** — correct for research workflows. Don't over-engineer cross-session before there's a need.
6. **API endpoint structure** — RESTful, extensible. Just tighten the Pydantic models.
