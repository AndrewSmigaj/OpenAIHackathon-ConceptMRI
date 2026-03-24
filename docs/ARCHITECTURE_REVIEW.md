# Architecture Review — Concept MRI

*Review date: 2026-03-24*

## Executive Summary

Concept MRI is well-engineered for a 7-day hackathon project with a single model and small datasets. The **data schema design and adapter pattern are exemplary** — proper contracts, immutable topologies, clean model abstraction. The **color system and visualization layer are thoughtful** — N-way categorical blending, traffic-based scaling, multi-window Sankey orchestration.

The main architectural concerns are: (1) **IntegratedCaptureService is overloaded** with session management, model inference, and I/O responsibilities; (2) **~40% code duplication** between ExpertRouteAnalysisService and ClusterRouteAnalysisService; (3) **ExperimentPage.tsx is a god component** managing 25+ state variables across unrelated concerns; and (4) **logging, configuration, and error handling are ad-hoc** rather than strategic.

The codebase is production-ready for the current feature set. For scaling to multiple models, larger datasets, or multiple users, the priority refactors are: decompose IntegratedCaptureService, factor shared analysis code, and extract ExperimentPage state into custom hooks.

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

**IntegratedCaptureService** (primary concern):
- Manages sessions (create, status, finalize)
- Orchestrates model inference (tokenize, forward pass, hook extraction)
- Coordinates batch writing to 4 Parquet files
- Handles KV cache threading for temporal experiments
- Too many responsibilities for one class

*If refactoring*: Split into SessionManager, ProbeInference, CaptureOrchestrator. Each testable in isolation.

**ExpertRouteAnalysisService vs ClusterRouteAnalysisService** (~500 lines each):
- ~40% duplicated code (estimated 200 lines)
- Shared methods: `_apply_filters`, `_build_sankey_data`, `_analyze_top_routes`, `_compute_available_axes`, `_get_label_breakdown`
- `_axis_label` helper was recently added to BOTH files independently

*If refactoring*: Extract `RouteAnalysisBase` with shared logic. Both services inherit or delegate.

**OutputCategoryNodes** + `_precompute_output_variants` in experiments.py:
- Output node construction logic split across two files with partial duplication
- Cross-product grouping logic is complex and fragile

*If refactoring*: Consolidate into an `OutputNodeService`.

### API Design

**Rating: Good**

- RESTful naming: `/api/probes/...`, `/api/experiments/...`, `/api/generation/...`
- Proper HTTP methods (GET for reads, POST for actions)
- Dependency injection via FastAPI `Depends()`
- Lazy initialization of analysis services (no startup cost)

**Concerns**:
- Some Pydantic models use `Dict[str, Any]` where typed fields would be better (LLMInsightsRequest `windows`, ScaffoldStepRequest `expert_windows`)
- Error handling is per-endpoint with no consistent middleware
- The temporal capture endpoint is 150+ lines of business logic inline in the route handler — should be extracted to a service

### Cross-Cutting: Logging

**Rating: Needs work**

- `main.py` uses `print()` for startup messages
- `integrated_capture_service.py` uses `print()` for errors
- `probes.py` has a logger but uses it sparingly
- No structured logging format
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

**Rating: Adequate for hackathon**

- Probe capture: `except Exception: continue` skips failed sentences (good for resilience, bad for debugging)
- Model loading: catches exception, prints error, starts in limited mode
- No session error tracking — failed probes are silently skipped without record
- No recovery mechanism for interrupted sessions

---

## Frontend

### Component Architecture

**ExperimentPage.tsx** (860 lines, 25+ state variables):

This is the main architectural concern. It manages:
- Session selection and loading
- Filter configuration
- Input axis controls (colorAxisId, gradient, etc.)
- Output axis controls (separate state tree)
- Clustering configuration
- Schema selection and report loading
- Card selection for the inspector panel
- Route data caching

**Strengths**: The data flow is unidirectional and callbacks are well-defined. No mutation of parent state from children.

**Concerns**: Too many unrelated concerns in one component. Axis auto-detection, schema loading, and clustering config should each be custom hooks. Color props are drilled through 3 levels of components (ExperimentPage → Section → MultiSankeyView → SankeyChart) with 12+ props each.

*If refactoring*:
1. `useAxisControls()` — manages colorAxisId, gradient, auto-detection from route data
2. `useClusteringConfig()` — manages clustering parameters
3. `ColorScheme` context — eliminates prop drilling for color/gradient state

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

**Rating: Good with gaps**

- Core types (SankeyNode, SankeyLink, RouteAnalysisResponse) are well-defined
- `SelectedCard` uses `data: any` — should be a discriminated union by card type
- `sessionData?: any` in LLMAnalysisPanel — should be typed
- `probe_assignments` structure (nested Record) is undocumented in TypeScript types

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

| Issue | Severity | Effort | Recommendation |
|-------|----------|--------|---------------|
| IntegratedCaptureService overloaded | High | 2-3 days | Fix later (before adding temporal capture) |
| Analysis service code duplication (~40%) | High | 1 day | Fix later (before adding new analysis types) |
| ExperimentPage god component | High | 2 days | Fix later (before adding new UI features) |
| Color prop drilling (12+ props × 3 levels) | Medium | 0.5 days | Fix later (extract to context) |
| Logging strategy (print → structured) | Medium | 1 day | Fix later |
| Configuration hardcoding | Medium | 0.5 days | Fix when adding second model |
| API schema loose typing (Dict[str, Any]) | Medium | 0.5 days | Fix incrementally |
| Temporal endpoint inline logic | Medium | 0.5 days | Fix when implementing temporal feature |
| Session state dual-source | Medium | 1 day | Fix later |
| Reduction service memory (dense matrices) | Low | 2 days | Fix when hitting OOM with larger datasets |
| Missing request caching in frontend | Low | 1 day | Fix when performance is noticeable |
| Type system gaps (any types) | Low | 0.5 days | Fix incrementally |
| No tests | Low | 2 days | Add targeted tests for adapters and schemas |
| No cross-session analysis | Low | 3+ days | Design when needed |

**Key insight**: Most "High" severity items should be fixed **before adding the next major feature** (temporal analysis tab), not as a standalone refactoring pass. The current code works well for the current feature set.

---

## What's Worth Preserving

1. **Schema layer** — don't touch it. The Parquet contracts are solid.
2. **Adapter pattern** — extend, don't restructure. Add adapters, don't change the interface.
3. **Color system** — best utility in the codebase. Keep pure functional approach.
4. **Skills architecture** — the runbook pattern works. Add skills, refine existing ones.
5. **Session isolation** — correct for research workflows. Don't over-engineer cross-session before there's a need.
6. **API endpoint structure** — RESTful, extensible. Just tighten the Pydantic models.
