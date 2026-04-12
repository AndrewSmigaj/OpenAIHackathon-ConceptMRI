Related: LLMud/VISION.md (research context), CLAUDE.md §Guide Index (if adding phases/skills), docs/PIPELINE.md (if changing backend pipeline)

# LLMud Institute — Architecture & Integration Plan

Living document. Tracks all design decisions, integration phases, and implementation items for the unified MUD-driven interpretability interface.

**Reading order:** Start with Section 1 (system overview) → Section 7 (component architecture) → Section 10 (phases) for implementation context. Sections 2-6 are reference material. Sections 8-9 are protocol specs for Phase 2+. Section 12 captures key design decisions and their rationale. → 15 (lens switching) → 16 (steering panel) → 17 (token knowledge graph) for the analysis layer architecture.

**Cross-document prereqs:** Read VISION.md first for the research concepts (scaffolds, attractor basins, the research question). The other 3 LLMud design docs are frozen reference for future phases — consult as-needed per the cross-reference table in Section 13.

---

## 1. System Overview

### 1.A Hybrid Interface

One interface for everyone. Toolbar (React controls) handles discoverable configuration — session, axes, clustering, run. MUD terminal handles navigation, power-user shortcuts, and Evennia integration. Researcher and visitors see the same layout; visitors have toolbar controls greyed out (room context controls permissions).

```
┌──────────────────────────────────────────────────────────────────┐
│ Toolbar: [Session▼] [Schema▼] [Axis▼] [Grad▼] [K:6]              │
├───────────────────────────────┬──────────────────────────────────┤
│                               │                                  │
│  Q1: Viz Panel                │  Q2: Analysis Panel              │
│  MultiSankeyView (6+output)   │  WindowAnalysis (contingency +   │
│  SteppedTrajectoryPlot        │   chi-square stats)              │
│  TemporalAnalysisSection      │  ContextSensitiveCard (click     │
│                               │   a node/link for details)       │
│                               │                                  │
├───────────────────────────────┼──────────────────────────────────┤
│                               │                                  │
│  Q3: MUD Terminal             │  Q4: Dataset / Agent Streams     │
│  xterm.js                     │  Phase 1: Probe sentences +      │
│  Navigation, power-user cmds  │   generated outputs + badges     │
│  Evennia connection (Phase 2) │  Phase 4+: Harmony channels      │
│                               │   (internal/external/output)     │
│                               │                                  │
└───────────────────────────────┴──────────────────────────────────┘
```

**Toolbar (top):** Compact ribbon (1-2 rows). Grouped sections: **Session** (session, schema), **Visual** (axis, gradient, blend, output axes), **Analysis** (K, method, source), **View** (range, routes, filters). Run stays in viz sections (ExpertRoutesSection, ClusterRoutesSection), not in toolbar.

**Quadrant grid:** 2x2 CSS grid, each panel independently scrollable. Desktop-only — no mobile/responsive.

**Q1 — Viz:** Sankey charts, trajectory plots, temporal analysis. Reused from current ExperimentPage.

**Q2 — Analysis:** Statistical analysis and click-detail cards. Reused. Also shows schema reports and element descriptions.

**Q3 — Terminal:** xterm.js for Evennia connection (Phase 2+). Phase 1: empty placeholder with welcome message.

**Q4 — Dataset / Agent Streams:** Phase 1: probe sentences + generated outputs (filterable by label, color-coded by primary axis). Phase 4+: agent harmony channels (internal/external/output text streams).

### 1.B Data Flow

Toolbar controls and terminal commands call the same React state setters. Evennia does NOT call the ConceptMRI API — React handles all API calls directly. Evennia manages the full MUD (world, combat, NPCs, objects, stats, permissions, rooms). Viz configuration stays React-local.

```
Researcher clicks [Axis ▼] → "label" in toolbar
  → React calls setColorAxisId("label") → panels re-render with new colors

Researcher types "run" in terminal (or clicks [Run] in toolbar)
  → React calls triggerAnalysis() → apiClient.analyzeRoutes() → REST to backend
  → Route data loads → Q1 panels render

User enters a room (Phase 2)
  → Evennia sends OOB: ["room_entered", [{session_id, schema, viz_preset, role, room_type}], {}]
  → React applies preset (sets session, axis, gradient, etc.) + sets role
  → React calls backend API directly → panels render
  → Toolbar controls greyed out if role is 'visitor'
```

**Config stays React-local in all phases.** Axis, gradient, range, clustering, and route config never go through Evennia — toolbar and terminal commands both call hooks directly. Evennia handles the full MUD; viz config is separate.

### 1.C Micro-worlds

A micro-world is any controlled experimental context. They form a spectrum:
- **Simple:** A probe (polysemy, suicide letter) — single stream of queries, one room
- **Complex:** A multi-room Evennia scenario with scaffolding for movement and interaction

Existing Concept MRI probes ARE micro-worlds. The institute has content from day one.

### 1.D View Modes

1. **Default view** (Phase 1): All sentences visible, full Sankey with all routes. Q4 shows complete dataset. Click a Sankey node → Q2 card shows details. This is basin identification — the current software's primary view, reorganized into the quadrant layout.
2. **Live view** (Phase 4+): Like trace stepping, but data comes from a running agent session. After each tick, the backend captures residual streams (using the same batch forward pass as default view), streams the results via WebSocket, and the UI updates: new point on LiveUMAP, new route on Sankey, new reasoning entry in Q4. Timeline scrubber lets observers step through tick history.

### 1.E Hosting

Self-hosted on WSL2 machine. All services on localhost.

| Service | Port |
|---------|------|
| ConceptMRI Backend (FastAPI) | 8000 |
| Frontend (Vite dev) | 5173 |
| Evennia (Telnet) | 4000 |
| Evennia (WebSocket) | 4002 |
| Evennia (Web, external) | 4001 |
| Evennia (Web, internal) | 4005 |

### 1.F Glossary

| Term | Definition |
|------|------------|
| Probe | A sentence fed to the model to observe its internal routing |
| Session | One capture run — a set of probes processed together, stored in `data/lake/{id}/` |
| Schema | A clustering configuration applied to a session's activations |
| Basin | A stable geometric region in activation space where similar probes cluster |
| Scaffold | A cognitive frame (persona, context, instructions) wrapped around a probe |
| MoE | Mixture of Experts — model architecture where each token routes to a subset of experts |
| Expert | One specialist sub-network in a MoE layer; top-1 routing means each token picks one |
| Route | The sequence of experts a token visits across layers (e.g., L22E3→L23E1) |
| Sankey | Flow diagram showing how probes route through experts/clusters across layers |
| OOB | Out-of-Band — Evennia's protocol for structured data alongside terminal text |
| VizConfig | Visual encoding state (color axes, gradients) — held in `useAxisControls` hook, not a React context |
| Micro-world | A controlled experimental context — from a simple probe set to a multi-room scenario |
| Attractor basin | Region of activation space that "pulls" nearby representations toward it |
| Residual stream | The running sum of all layer outputs — the model's "working memory" |
| UMAP | Dimensionality reduction (6D) applied to residual streams for clustering |

---

## 2. Current System Audit

### 2.A Backend (~7000 lines, 59 files)

| Router | Lines | Endpoints |
|--------|-------|-----------|
| `probes.py` | 380 | Session CRUD, sentence experiments, clustering schemas, reports |
| `temporal.py` | 497 | Temporal capture, lag data, scrubber state (extracted from old `experiments.py`) |
| `routes.py` | 163 | Expert + cluster route analysis (extracted from old `experiments.py`) |
| `route_utils.py` | 106 | Shared helpers between expert/cluster route paths |
| `clustering.py` | 183 | Clustering schemas, dimensionality reduction, schema CRUD |
| `insights.py` | 70 | LLM insights / scaffold-step (extracted from old `experiments.py`) |
| `generation.py` | 98 | Sentence set management |
| `prompts.py` | 38 | Scaffold templates |
| `agent.py` | 299 | Agent session start/stop/generate (Phase 4) |

The 980-line `experiments.py` is gone — split into `routes.py`, `temporal.py`, `clustering.py`, `insights.py` plus shared `route_utils.py`. Module-level lock `_temporal_capture_busy` lives in `temporal.py:21`.

**Services:**
- `services/probes/` — `SessionManager`, `ProbeProcessor`, `CaptureOrchestrator`, `IntegratedCaptureService` (facade), `RoutingCapture`, `ProbeIDs`, `ScenarioActions` (74L — Phase 4 helper that resolves YAML scenario actions)
- `services/agent/` — `AgentLoop` (408L), `EvenniaClient` (154L), `HarmonyParser` (50L). Agent loop runs **inside** the backend Python process as an asyncio task; there is no separate agent process.
- `services/experiments/` — `ExpertRouteAnalysis`, `ClusterRouteAnalysis`
- `services/features/` — `ReductionService` (UMAP wrapper)
- `services/insights/` — `LLMInsightsService`

**Data:** Pydantic schemas → Parquet files in `data/lake/{session_id}/`. Clean adapter pattern for model abstraction (gpt-oss-20b).

**MUD additions shipped:** WebSocket endpoints for Evennia (Phase 2), agent loop with per-tick capture (Phase 4.0/4.1), scenario action resolver (Phase 4.H). New endpoints: `POST /api/agent/start`, `POST /api/agent/stop`, `POST /api/agent/generate`.

### 2.B Frontend (~6500 lines, 38 files)

| Page | Lines | State |
|------|-------|-------|
| WorkspacePage | 185 | Session list, loading, error |
| ExperimentPage | 870 | Legacy at `/legacy/:id` — kept untouched |
| MUDApp | 433 | Phase 1 layout — toolbar + 2x2 quadrant grid, single route at `/` |

**Extracted hooks:** `useAxisControls` (101L), `useClusteringConfig` (43L), `useSchemaManagement` (48L), `useTemporalAnalysis` (417L), `useEvennia` (145L — Phase 2, WebSocket connection + OOB handling).

**Viz components:** SankeyChart, MultiSankeyView, WindowAnalysis, ContextSensitiveCard, SteppedTrajectoryPlot — all reused unchanged from ExperimentPage.

**Existing infrastructure:** react-router-dom v7 (BrowserRouter, routes for `/`, `/legacy/:id`), ECharts, Tailwind, jStat, xterm.js (Q3 terminal), WebSocket (Evennia connection).

### 2.C Data Layer

- **134 sessions** in `data/lake/` (Parquet: tokens, routing, embeddings, residual_streams, manifest)
- **12 sentence sets** across polysemy, safety, role_framing categories
- **Clustering schemas** per session: `meta.json`, `probe_assignments`, `centroids.json`, `element_descriptions`, `reports/`
- **Agent session artifacts** (Phase 4.0/4.1): `tick_log.jsonl`, `probe_results.jsonl`, `session_analysis.md`
- **Scenario YAMLs**: `data/worlds/scenarios/` — 52 active bus_stop probe scenarios (26 matched friend/foe pairs from v3/v4/v5), 2 legacy single-room files (`bus_stop_friend.yaml`, `bus_stop_foe.yaml`), 2 placeholder Phase 4.1 scenarios (`helpful_herbalist`, `suspicious_blacksmith`), and `GUIDE.md` cataloging the design rules

### 2.D Design Documents

4 files in `/LLMud/`. VISION.md is active reference; the other 3 are frozen for future phases:

| Document | Covers | Phase |
|----------|--------|-------|
| VISION.md | Research motivation, scaffold concept | Active |
| AI_SYSTEM_DESIGN.md | Cognitive loop, scaffolds, memory, tools | Phase 4+ (frozen) |
| WORLD_DESIGN.md | Evennia world, micro-worlds, tick system | Phase 2-4 (frozen) |
| INSTITUTION_DESIGN.md | Public institute, AI scientists | Phase 5-6 (frozen) |

In `docs/`:

| Document | Covers | Status |
|----------|--------|--------|
| `steeringandscenarios.md` | Discriminating neurons, lens registry, steering experiments, scenario design (matched friend/foe pairs, cross-probe matrix) | Active reference for Pending Work C–F |

---

## 3. MUD Command Vocabulary

Phase 2 ships two command vocabularies on top of Evennia's defaults:

1. **Researcher commands** — concrete physical verbs the scenario layer exposes:
   - `evennia_world/commands/mud_commands.py`: `approach`, `withdraw`, `hide`, `sit <x>`, `lean`, `wait`, `flee`, `shout <x>`, `refuse`, `leave`, `assist <x>`, `snatch <x>`, `shove <x>`, `search <x>`, `inquire <x>`, `pass`, `give <x> to <y>`, `buy <x> from <y>`, `goto <room>`, `call <x>`, `actions` (meta-command that prints available scenario actions).
   - `evennia_world/commands/scenario_commands.py`: `ask <npc> <topic>`, `tell <npc> <topic>`, `knowledge`, `examine` (scenario-specific override of Evennia's built-in), `agent start <name> <scenario>` (Builder-only), `agent stop` (Builder-only).
   - Evennia built-ins also available: `look`, `inventory`, `get`, `drop`, movement (`north`, `south`, etc.), `say`, `who`.
2. **Scenario actions**, declared per-scenario in YAML, that map a verb above onto an outcome via `effects:` blocks. Each action is typed `friend`/`enemy` and labeled `correct: true|false`. The agent loop tracks the first scenario-action selection per session as the probe result (`bus_stop_*` results in `probe_results.jsonl`).

Terminal config commands (axis, schema, run) remain deferred — the toolbar handles all viz configuration in Phase 1.

---

## 4. Room System

### 4.A Researcher's Lab

Private room, all toolbar controls enabled, all terminal commands available: `load`, `schema`, `axis`, `cluster`, `run`, `routes`, `range`, `output-axis`. Session selector is open — researcher can load ANY dataset. This is the personal workspace for running experiments and exploring data.

### 4.B Micro-world Rooms

Enter a room → auto-load that world's session data via OOB `room_entered` event. Pre-configured viz presets from YAML config. **Session is locked** to the room's configured dataset — the session selector in toolbar is disabled. Researchers set this up so scientists and visitors can study that specific dataset.

- **Researcher role:** Can change viz settings (axis, gradient, range, clustering) but cannot switch sessions. Full observation + analysis commands.
- **Visitor role:** Toolbar controls greyed out. Observation commands only: `look`, `inspect`, `dataset`, `help`, `say`. Visitors see the curated view and can chat with others in the room.

### 4.C Room → Trace Mapping

- Hub connects to micro-worlds. Each micro-world = certain traces + multiple rooms.
- Normal rooms (hallways, commons) send `room_entered` with `session_id: null` and `room_type: "social"`. React shows a welcome message with navigation hints instead of viz panels.
- Entering a micro-world room loads that world's trace data.
- Mode is selected within a micro-world, not by which room you're in.

### 4.D Relationship to WORLD_DESIGN.md

The room types above (Researcher's Lab, Micro-world rooms) are the Phase 2 implementation. WORLD_DESIGN.md describes a richer room model with Observer Spaces (invisible to agents), hidden exits, TurnRoom typeclasses with tick-based turns, and ambient visualization-as-environment. These mechanics come in Phase 4+ when agent sessions exist and there's actual gameplay to observe. Don't over-design rooms that don't have content yet.

---

## 5. Dataset Viewer (Q4 Panel)

The dataset viewer lives in Q4 (bottom-right quadrant), not a drawer overlay. It's a permanent panel that shares the quadrant with agent streams in Phase 4+.

### 5.A Default View (all sentences)

Two columns per row:
1. **Input** — the probe sentence
2. **Generated Output** — model's continuation + output category badge

Filterable by label. Color-coded by primary axis. Scrollable within the grid cell.

**Data source:** `apiClient.getSessionDetails()` already returns sentences with `generated_text` and `output_category` fields. DatasetPanel populates from this on session load. Shows "No generated outputs" placeholder if the session has no categorized outputs.

### 5.B Stepping & Trace Highlighting

The scrubber (existing in TemporalAnalysisSection) steps through traces. Stepping forward/back updates which trace is highlighted on Sankeys and trajectory plot. Two use cases for the same UI pattern:

1. **Temporal expanding window analysis** (existing) — steps through traces as context window builds. Used in researcher's lab for temporal experiments.
2. **Scenario tick stepping** (Phase 4+) — steps through an agent's ticks in a scenario. Used for observing agent behavior.

Implementation details and specific controls to be designed when each use case is implemented.

### 5.D Agent Streams (Phase 4+)

Q4 gains a tab system: **Dataset** (sentences/outputs) and **Agent Streams** (harmony channels — internal reasoning, external actions, final output). Toggle between them via a tab header in Q4. Live view (§1.D) shows the latest trajectory from a running simulation with real-time updates.

**Future additions:** Scaffold context column (requires storing scaffold text in ProbeRecord).

---

## 6. Sharing Model

There is no publish/snapshot workflow. Researchers share data by configuring micro-world rooms directly:

1. Researcher runs experiments and analyzes data in their personal lab
2. Researcher creates a micro-world YAML config (§9) pointing to the session, schema, and viz preset
3. Visitors enter the micro-world room → OOB `room_entered` applies the preset automatically
4. The room IS the publication — visitors see exactly what the researcher configured

This means sharing is a configuration task (edit YAML), not a runtime operation. No state sync, no snapshot mechanism, no live mirroring needed.

---

## 7. Component Architecture

### 7.A Design Philosophy

MUDApp is simpler than ExperimentPage because it separates concerns into a clean layout:
- **Toolbar** handles configuration (React controls — discoverable, frequent actions)
- **Terminal** handles Evennia connection (Phase 2+, additive, not required)
- **Hooks** hold state (same `useAxisControls`, `useClusteringConfig`, `useSchemaManagement` pattern)
- **Quadrant panels** handle output (reused viz components in a 2x2 grid)
- **Props** for everything — no React contexts needed

No VizConfigContext. The current hooks (`useAxisControls`, `useClusteringConfig`, `useSchemaManagement`) work unchanged. All components receiving viz state accept hook return objects as typed props — 3 objects (`AxisControlsState`, `ClusteringConfigState`, schema state), not 30+ individual props. This applies to Toolbar, MultiSankeyView, SteppedTrajectoryPlot, and any other viz consumer. Each component destructures what it needs internally. SankeyChart is the exception — it's a pure rendering component that receives individual values from MultiSankeyView, not hook objects.

Components render directly in CSS grid cells — prop depth is MUDApp → component → child (2-3 levels, down from 4+ in ExperimentPage).

ExpertRoutesSection and ClusterRoutesSection are kept as-is. They manage their own Run state internally and wrap the viz components. `convertFilterState()` is deduplicated to `utils/filterState.ts` (currently duplicated in ClusterRoutesSection and MultiSankeyView).

### 7.B Component Tree

```
MUDApp (single page, single route: /)
├── Toolbar                          ← compact ribbon, always visible
│   ├── SessionSelector              ← dropdown with session names
│   ├── SchemaSelector               ← dropdown + clustering param controls
│   ├── AxisControls                 ← color/blend/shape/output + gradient pickers (currently inline in ExperimentPage lines 27-135, extract to own file)
│   ├── FilterToggles                ← label filter chips
│   ├── RangeSelector                ← layer range picker
│   └── (reserved)                   ← future: live view toggle (Phase 4+)
├── QuadrantGrid                     ← 2x2 CSS grid
│   ├── Q1 (CSS grid cell)
│   │   ├── ExpertRoutesSection      ← reused as-is (manages own Run state)
│   │   ├── ClusterRoutesSection     ← reused as-is (manages own Run state)
│   │   └── TemporalAnalysisSection  ← reused
│   ├── Q2 (CSS grid cell)
│   │   ├── WindowAnalysis            ← reused (fix: import SankeyNode/SankeyLink from types/api.ts)
│   │   └── ContextSensitiveCard      ← reused
│   ├── Q3 (CSS grid cell)
│   │   └── MUDTerminal               ← xterm.js, empty in Phase 1
│   └── Q4 (CSS grid cell)
│       └── FilteredWordDisplay        ← reused (sentences, color-coded, filterable)
│           └── (Phase 4+: AgentStreams tab)
```

**No wrapper components.** QuadrantGrid is layout-only CSS. Viz components render directly in MUDApp's JSX inside grid cells. This keeps the component tree shallow and prop paths explicit.

### 7.C Command Dispatch

Toolbar controls and terminal commands both call the same setState functions on MUDApp's hooks. Toolbar controls call setters directly (e.g., `onChange={setColorAxisId}`). Terminal commands go through `useCommandDispatch` which parses text and calls the same setters.

```
Toolbar: user clicks [Axis ▼] → "label"
  → onChange calls setColorAxisId("label") directly

Terminal: user types "axis label red-blue"
  → useCommandDispatch parses → calls setColorAxisId("label"), setGradient("red-blue")
```

Config stays React-local in all phases. Evennia (Phase 2+) handles the full MUD — config never routes through Evennia.

**Terminal commands:** See §3 for the shipped command vocabulary. Phase 1 terminal is empty; Phase 2+ connects to Evennia.

#### 7.C.1 Run Trigger Mechanism

Run stays in the viz sections (ExpertRoutesSection and ClusterRoutesSection), not in the toolbar. Each section manages its own Run state internally via `manualTrigger={true}` on MultiSankeyView. This is the existing pattern — no changes needed.

**Session list:** MUDApp calls `apiClient.listSessions()` on mount to populate SessionSelector (same pattern as WorkspacePage).

**Session change invariant:** The toolbar session selector calls `resetForNewSession(sessionId)`:

1. Set session ID
2. Reset axes to defaults (colorAxisId='label', gradient='red-blue', range='range1')
3. Clear route data, selected card, filter state
4. Clear schema selection (new session may not have the same schemas)
5. Fetch session metadata via `apiClient.getSessionDetails()` → populate available schemas, Q4 sentences (axes populate after first `run` via handleRouteDataLoaded)

This is **new behavior** that fixes a current bug: ExperimentPage lines 291-301 only call `loadAndMergeSessions()` on session change — no axis reset, no filter reset, no schema reset, no card clear. Switching sessions leaves stale controls from the previous session.

**Axis auto-detection:** Axes are NOT available from session metadata — they come from `RouteAnalysisResponse.available_axes` after running analysis. MUDApp's `handleRouteDataLoaded` callback (same pattern as ExperimentPage lines 226-265) merges axes from all windows and populates `setAllAxes`. Toolbar axis dropdowns start empty and populate after the first `run`.

**Schema → clustering sync:** When a schema is selected via toolbar, a useEffect syncs the schema's saved params into clustering config state (same pattern as ExperimentPage lines 186-202).

**Error handling:** API errors during analysis show in the viz panels (same as current ExperimentPage behavior). API errors do NOT clear previous successful data.

### 7.D State Management

No React contexts. The existing hooks are the state layer:

- `useAxisControls()` — visual encoding (axes, gradients, range). 10 values + 10 setters + derived. Passed as `AxisControlsState`.
- `useClusteringConfig()` — clustering params (method, K, source, reduction). 9 values + 9 setters. Passed as `ClusteringConfigState`.
- `useSchemaManagement(sessionIds, onDescLoaded)` — schema list + selection. Fetches schema details on change.
- `useTemporalAnalysis(sessionId, clusterRouteData, clusteringSchema)` — basin selection, run management, grouping/aggregation, scrubber, lag metrics. 27 return values. Passed as `TemporalAnalysisState`.

All four hooks live in MUDApp. Toolbar receives the hook return objects as props. Viz components receive values as props (2-3 levels).

Additional MUDApp-level state (not in hooks):
- `filterState: FilterState` — label filter. Passed to viz sections and Q4 sentence display. Currently defined in `WordFilterPanel.tsx`.

### 7.E What Changes from Current Architecture

| Item | Current | MUDApp |
|------|---------|--------|
| Researcher interface | `/experiment/:id` with sidebar controls | Toolbar + terminal in lab room |
| Visitor interface | (none) | Same layout, toolbar greyed out (room context) |
| React controls | Sidebar (220px, always visible) | **Toolbar** (compact ribbon, grouped sections) |
| ExperimentPage | 871-line monolith | **Replaced** by MUDApp (keep as `/legacy` during dev) |
| WorkspacePage | Session list page | **Replaced** — SessionSelector in toolbar |
| Sentence list | Always-visible left panel | Q4 DatasetPanel (permanent quadrant) |
| State management | useAxisControls + useClusteringConfig + useSchemaManagement + useTemporalAnalysis + 30 individual props through 4+ levels | Same 4 hooks, hook objects as typed props through 2-3 levels (4 objects, not 30+ individual values) |
| Tab sections | ExpertRoutesSection + ClusterRoutesSection tabs | **Kept** — both visible in Q1, manage own Run state |
| Layout | Header + sidebar + 3-column main area | Toolbar + 2x2 quadrant grid |
| Terminal | (none) | Q3: xterm.js (empty in Phase 1, Evennia in Phase 2+) |
| Number of React routes | 3 (`/`, `/experiment`, `/experiment/:id`) | 1 (`/` — the MUD interface) |

### 7.F Code Structure

```
ConceptMRI/
├── backend/src/
│   ├── adapters/                # Model adapter pattern (gpt-oss-20b)
│   ├── algorithms/              # Clustering, routing algorithms
│   ├── api/
│   │   ├── config.py            # DATA_LAKE_PATH, env var config
│   │   ├── dependencies.py      # FastAPI dependency injection (service factories)
│   │   ├── main.py              # App + router registration
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routers/
│   │       ├── agent.py         # Agent session start/stop/generate (Phase 4)
│   │       ├── clustering.py    # Schema CRUD, reduction, cluster route analysis
│   │       ├── generation.py    # Sentence sets
│   │       ├── insights.py      # LLM insights
│   │       ├── probes.py        # Session CRUD, sentence experiments
│   │       ├── prompts.py       # Scaffold templates
│   │       ├── route_utils.py   # Shared helpers for route analysis
│   │       ├── routes.py        # Expert + cluster route analysis
│   │       └── temporal.py      # Temporal capture, lag data, _temporal_capture_busy lock
│   ├── cli/                     # CLI utilities
│   ├── core/                    # Parquet reader/writer, data lake helpers
│   ├── schemas/                 # Parquet schema definitions (tokens, routing, embedding, residual_stream)
│   ├── services/
│   │   ├── agent/               # AgentLoop (408L), EvenniaClient (154L), HarmonyParser (50L)
│   │   ├── experiments/         # ExpertRouteAnalysis, ClusterRouteAnalysis, LLMInsightsService
│   │   ├── features/            # ReductionService (UMAP/PCA wrapper)
│   │   ├── generation/          # Text generation service
│   │   └── probes/              # SessionManager, ProbeProcessor, CaptureOrchestrator, ScenarioActions
│   └── utils/                   # Shared utilities
├── frontend/src/
│   ├── pages/
│   │   ├── MUDApp.tsx           # Unified interface at / (Phase 1)
│   │   ├── ExperimentPage.tsx   # Legacy (retained as file, not currently routed)
│   │   └── WorkspacePage.tsx    # Session list (unused since Phase 1)
│   ├── hooks/
│   │   ├── useAxisControls.ts   # Visual encoding state
│   │   ├── useClusteringConfig.ts
│   │   ├── useSchemaManagement.ts
│   │   ├── useTemporalAnalysis.ts
│   │   └── useEvennia.ts        # WebSocket connection (Phase 2)
│   └── components/
│       ├── toolbar/             # Toolbar, SessionSelector, AxisControls
│       ├── charts/              # SankeyChart, MultiSankeyView
│       ├── analysis/            # WindowAnalysis, ContextSensitiveCard
│       ├── terminal/            # MUDTerminal (xterm.js)
│       └── icons/               # SVG icon components
├── evennia_world/               # Evennia game directory
│   ├── typeclasses/rooms.py     # ScenarioRoom, MicroWorldRoom
│   ├── commands/
│   │   ├── mud_commands.py      # Scenario verb vocabulary (21 commands) + CmdActions
│   │   ├── scenario_commands.py # examine, ask, tell, knowledge, agent start/stop
│   │   └── navigation.py       # Movement overrides
│   └── server/conf/settings.py  # Evennia config (GUEST_ENABLED, ports)
├── data/
│   ├── lake/                    # 134 sessions (Parquet + agent artifacts)
│   ├── worlds/scenarios/        # 52 active probe YAMLs + GUIDE.md
│   └── sentence_sets/           # 12 probe sentence set JSONs
├── LLMud/                       # Frozen design docs (VISION.md active)
└── docs/
    ├── architecturemud.md       # This document
    └── steeringandscenarios.md  # Neuron analysis, steering, scenario design
```

---

## 8. OOB Event Protocol

Config commands (axis, gradient, range, clustering, routes, filters) stay React-local in all phases — toolbar controls call hooks directly. Evennia handles the full MUD; viz config is separate. OOB events are limited to room context changes.

### 8.A Evennia → React Events

All OOB events follow Evennia's protocol: `["funcname", [args], {kwargs}]`

| Event | Trigger | Payload |
|-------|---------|---------|
| `room_entered` | Room navigation | `{session_id, schema, viz_preset, role, room_type}` |
| `room_left` | Leaving a room | `{}` — React clears Q1-Q4 panels and shows "Navigating..." placeholder until next `room_entered` |

The `viz_preset` in `room_entered` carries the full initial config using YAML field names. React's `applyPreset()` maps these to hook setters and triggers analysis:

| YAML field | Hook setter |
|------------|-------------|
| `primary_axis` | `setColorAxisId` |
| `gradient` | `setGradient` |
| `layer_range` | `setSelectedRange` |
| `mode` | `setAnalysisMode` |
| `clustering_schema` | `setSelectedSchema` |
| `top_routes` | `setTopRoutes` |
| `show_output` | `setShowOutput` |

The `role` field (`"researcher"` or `"visitor"`) determines whether toolbar controls are enabled or greyed out.

### 8.B React → Evennia (navigation only)

React sends navigation commands to Evennia via WebSocket. Config commands are handled locally — they never reach Evennia.

```
["text", ["north"], {}]
["text", ["enter polysemy_observatory"], {}]
["text", ["leave"], {}]
```

### 8.C Protocol Notes

Evennia's WebSocket webclient protocol uses JSON arrays. The React MUDTerminal component:
1. Sends navigation keystrokes as `["text", [input], {}]`
2. Receives `["text", [output], {}]` → renders in xterm.js (room descriptions, narrative)
3. Receives OOB `room_entered` → applies preset, sets room context
4. Config commands (`axis`, `run`, `schema`, etc.) are parsed locally, never sent to Evennia

**Phase 1→2 transition:** Config commands work identically — local parser calls hook setters. Phase 2 adds the Evennia WebSocket for navigation and room events. The local command dispatch layer persists unchanged.

**Reconnection (Phase 2):** If the Evennia WebSocket drops, the MUDTerminal shows a disconnected indicator and attempts reconnect with exponential backoff (1s, 2s, 4s, max 30s). During disconnection, viz panels and toolbar remain functional (config is React-local). Only navigation commands are disabled. On reconnect, Evennia re-sends the current room's state via OOB.

---

## 9. Micro-World Config

### 9.A YAML Format

```yaml
# data/worlds/polysemy_tank.yaml
name: "Tank Polysemy"
description: "Five meanings of 'tank' route to distinct geometric regions"
rooms:
  observatory:
    name: "Polysemy Observatory"
    description: "Residual stream traces from 400 tank sentences flow through the Sankey diagram on the wall."
    session_id: "session_1434a9be"
    schema: "polysemy_explore"
    viz_preset:
      layer_range: "range4"
      primary_axis: "label"
      gradient: "red-blue"
      top_routes: 20
      show_output: true
      mode: "cluster"
      clustering_schema: "polysemy_explore"
```

The `viz_preset` is a PRESET — a serialization of initial state applied when entering a room. It maps to MUDApp hook state via an `applyPreset()` function (see §8.A for the field-to-setter mapping). The YAML shape is the canonical shape — `applyPreset()` translates YAML keys to hook setter calls.

### 9.B Room Typeclass

```python
# evennia_world/typeclasses/rooms.py
class MicroWorldRoom(DefaultRoom):
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        config = self.db.world_config or {}
        role = "visitor" if self.db.public else "researcher"
        moved_obj.msg(room_entered=[{
            "session_id": config.get("session_id"),
            "schema": config.get("schema"),
            "viz_preset": config.get("viz_preset", {}),
            "role": role,
            "room_type": self.db.room_type or "micro_world"
        }])
```

---

## 10. Implementation Phases

### Phase 0 — Backend Cleanup ✅ shipped

Fix genuine tech debt that exists regardless of MUD. Backend-only + one trivial frontend fix. No changes to ExperimentPage — it stays working untouched as `/legacy` during Phase 1.

**Design constraint:** This is a single-researcher tool on a single machine. No backward compatibility, no data migration scripts, no API versioning. Component interfaces can change freely — we update all callers. No compatibility shims, adapters, or deprecation paths.

| Item | Task | Files |
|------|------|-------|
| 0.1 | ~~Delete superseded LLMud docs (ARCHITECTURE.md, DEV_PROCESS.md, CLAUDE_CODE_GUIDE.md, INDEX.md). Add freeze headers to remaining 3 (AI_SYSTEM_DESIGN.md, WORLD_DESIGN.md, INSTITUTION_DESIGN.md).~~ **Done.** | `LLMud/` |
| 0.2 | WindowAnalysis.tsx re-declares SankeyNode/SankeyLink interfaces locally (lines 6-18). Import from `types/api.ts` instead. (SankeyChart.tsx already imports correctly.) | `WindowAnalysis.tsx`, `types/api.ts` |
| 0.3 | Data lake path is hardcoded 7+ times across routers and `dependencies.py`. Extract to `api/config.py` with `DATA_LAKE_PATH` read from env var (default: `data/lake`). Update `experiments.py`, `probes.py`, and `dependencies.py` (4 service factories) to import from config. | `experiments.py`, `probes.py`, `dependencies.py`, new `config.py` |
| 0.4 | Split `experiments.py` (980 lines, 11 endpoints) into 4 routers: routes (4 endpoints), temporal (3), reduction (1), insights (1). `scaffold-step` and `health` go in insights or a shared router. Extract `_temporal_capture_busy` to `api/shared.py`. | `backend/src/api/routers/` |
| 0.5 | Fix silent exception swallowing: `probes.py` line 104 `except Exception: continue` silently skips bad session files. Add `logger.warning()`. | `probes.py` |
| 0.6 | Replace `print()` with `logger.error()` in BatchWriter (`parquet_writer.py` line 89). | `core/parquet_writer.py` |
| 0.7 | Type `SelectedCard.data` — currently `any` in `types/analysis.ts`. Change to discriminated union: `{ type: 'expert', data: SankeyNode } | { type: 'cluster', data: SankeyNode } | { type: 'route', data: SankeyLink } | { type: 'highway', data: SankeyLink }`. | `types/analysis.ts` |

**Execution order:** 0.1, 0.2, 0.5, 0.6 can run in any order. 0.3 must precede 0.4 (config enables clean router split).

**0.4 warning:** `_temporal_capture_busy` is a module-level lock in experiments.py preventing concurrent temporal captures. When splitting, extract this to `api/shared.py` that all split routers import. Don't duplicate it.

**Why no frontend refactoring here:** MUDApp reuses the existing hooks (`useAxisControls`, `useClusteringConfig`, `useSchemaManagement`, `useTemporalAnalysis`) unchanged. The toolbar is extracted from ExperimentPage's sidebar controls (including AxisControls, currently inline at ExperimentPage lines 27-135). No new abstractions are created in Phase 0. The viz components (SankeyChart, MultiSankeyView, etc.) are already reusable via props.

**Verification checklist:**
- 0.1: Superseded docs deleted (4 files). Freeze headers present on remaining 3. No broken cross-references in architecturemud.md.
- 0.2: WindowAnalysis renders same at `/experiment/:id` with imported types
- 0.3: All endpoints respond. `DATA_LAKE_PATH` env var overrides default. No `parents[4]` path computation in any router or dependency file.
- 0.4: All 11 backend endpoints respond (route analysis, cluster analysis, temporal capture, lag data, reduction, insights). `_temporal_capture_busy` imports from `api/shared.py` in temporal router. Frontend unchanged — ExperimentPage works identically.
- 0.5: Load sessions with a corrupted session dir → warning logged (not silently skipped)
- 0.6: Trigger a batch write failure → error appears in log output (not just stdout)

### Phase 1 — Layout Reorganization (no Evennia) ✅ shipped

Reorganize the existing UI from sidebar+columns into toolbar+quadrant layout. Everything works exactly as it does now — same controls, same viz, same analysis workflow. The only change is where things are on screen. **Status:** MUDApp.tsx (433L) replaces ExperimentPage as the primary `/` route. ExperimentPage.tsx (870L) retained as a file but not currently routed in App.tsx. All four hooks survived the move unchanged.

| Item | Task |
|------|------|
| 1.A | `MUDApp` page component — single route at `/`. 2x2 quadrant CSS grid + toolbar. ExperimentPage stays at `/legacy/:id` untouched. All 4 hooks instantiated. |
| 1.B | `Toolbar` component — extracted from ExperimentPage sidebar. SessionSelector (single dropdown), AxisControls, SchemaSelector, ClusteringControls, FilterToggles, RangeSelector. Receives hook return objects as props. `resetForNewSession()` fixes session change bug. |
| 1.C | Q1: ExpertRoutesSection + ClusterRoutesSection + TemporalAnalysisSection (reused as-is). Q2: WindowAnalysis + ContextSensitiveCard (reused as-is). Same props as ExperimentPage. |
| 1.D | Q4: FilteredWordDisplay (reused) — probe sentences, color-coded by primary axis, filterable via toolbar label controls. |
| 1.E | Q3: MUDTerminal — xterm.js widget, empty. Displays welcome message. No command parsing. Ready for Evennia in Phase 2. |
| 1.F | Code prep: Add `TemporalAnalysisState` interface to useTemporalAnalysis.ts. Deduplicate `convertFilterState` to `utils/filterState.ts`. |

**Initial state:** At startup before any session load: toolbar shows empty SessionSelector; Q1-Q2 show "No session loaded" placeholders; Q3 terminal shows welcome message; Q4 shows empty sentence list.

**Verification checklist** (test at `/` using session_1434a9be):
- Open `/` — toolbar renders, quadrant grid visible, terminal shows welcome
- Select session from toolbar dropdown → Q4 populates with sentences
- Select schema → clustering params update
- Set axis/gradient via toolbar → colors update
- Click Run in expert section → Q1 Sankeys render
- Click Run in cluster section → Q1 cluster Sankeys + trajectory render
- Change range → re-render
- Click Sankey node → Q2 card appears
- Toggle filter labels in toolbar → Sankeys + Q4 sentence list filter
- Select different session → axes reset, data clears
- `/legacy/:id` still works unchanged

### Phase 2 — Evennia Integration ✅ shipped (commit `dd86fa6`)

Add Evennia for the full MUD experience (rooms, NPCs, combat, objects, stats). Config commands stay React-local — Evennia handles the game world, viz config is separate. **Status:** Evennia runs in the same `.venv`, MUDTerminal connects via WebSocket on port 4002, OOB `room_entered` flows wired up, `ScenarioRoom` typeclass enforces the per-state action graph for probe scenarios, and `mud_commands.py` ships the researcher command vocabulary (§3).

**Prerequisite:** Verify Evennia's dependencies (Django, Twisted) are compatible with ConceptMRI's venv (FastAPI, transformers, torch). If they conflict, Evennia must run in a separate venv with IPC between services. Resolve before starting 2.A.

| Item | Task |
|------|------|
| 2.A | Evennia project setup — settings, typeclasses, basic room structure |
| 2.B | WebSocket connection — MUDTerminal connects to Evennia for navigation text |
| 2.C | OOB handler — React receives `room_entered` events, applies presets, sets room context |
| 2.D | Evennia navigation commands — north, south, enter, leave, hub |
| 2.E | Room system — Researcher Lab, micro-world rooms with presets |
| 2.F | Room context → toolbar — `roomContext.role` controls toolbar enabled/disabled state |
| 2.G | Micro-world YAML configs and batch build script |

**Verification checklist:**
- Evennia starts on port 4000, frontend connects via WebSocket
- Terminal shows Evennia welcome text and room description
- All Phase 1 toolbar controls + terminal commands still work (config is React-local)
- `look` → terminal prints room description (from Evennia)
- Room navigation (`enter polysemy_observatory`) → OOB `room_entered` fires → toolbar updates with preset session/schema/axis, Q1 renders Sankeys
- Enter researcher's lab → toolbar controls enabled
- Enter public micro-world → toolbar controls greyed out, can only use `look`, `inspect`, `help`, `say`, navigation
- Disconnect WiFi → terminal shows disconnected indicator, toolbar + viz still functional (config is local)
- Reconnect → Evennia re-sends room state via OOB

### Phase 3 — Multi-User & Chat ✅ shipped (commit `4a4b250`)

| Item | Task |
|------|------|
| 3.A | Auth/permissions — researcher vs visitor role distinction (Evennia auth). Designated researchers get full lab access; visitors get observation-only in micro-worlds. |
| 3.B | Visitor chat — `say`, `whisper`, channel commands via Evennia's built-in chat system. Visitors can chat with each other and researchers in the same room. (Evennia default — testing, not implementation.) |
| 3.C | Multiple concurrent viewers — multiple visitors in the same micro-world room see the same dataset and preset config. (Evennia default — testing, not implementation.) |
| 3.D | Guest access — anonymous visitors can land in social/observer rooms without an Evennia account. |

**Verification checklist:**
- Researcher logs in with credentials; visitor connects as guest
- Visitor enters micro-world room → sees locked dataset with preset config (correct session, schema, colors)
- Visitor types `say hello` → message appears in terminal for all users in room
- Researcher in same room sees visitor's chat message
- Two visitor tabs viewing same room → both render correctly, neither interferes
- Visitor cannot `load`, `schema`, `axis`, `cluster`, or `run` (toolbar greyed out)
- Visitor CAN use `look`, `inspect`, `dataset`, `help`, `say`, navigation

### Phase 4 — Live Agent Sessions & Streaming ⚙️ partially shipped

Agent plays scenarios in Evennia. ConceptMRI captures residual streams using the existing batch capture pipeline — no hook modifications needed. Observers watch live via streaming.

**Status (April 2026):**
- 4.A–4.C, 4.H **shipped** in commits `174f41e`, `e73e786`, `f847d7a`. Per-tick agent loop runs inside the backend Python process as an asyncio task. Capture pipeline uses the existing `CaptureOrchestrator`. Session lifecycle endpoints `POST /api/agent/start` and `POST /api/agent/stop` work.
- **Reality check — divergence from original Phase 4 framing:** Phase 4 was originally written assuming a long-running agent in the researcher's lab playing a multi-room Evennia scenario with rich combat and NPCs. What actually got built is the **probe scenario** variant: matched friend/foe pairs declared in YAML (`data/worlds/scenarios/*.yaml`), a `ScenarioRoom` typeclass enforcing the per-state action graph, and `probe_results.jsonl` recording the agent's first scenario-action selection plus the YAML ground-truth label. This is the right shape for Pending Work C–E (per-cluster discriminating neurons need labeled probe data) but it is narrower than the original Phase 4 vision. The richer agent-in-world framing is deferred until Phase 5+.
- 4.D **not done** — no WebSocket streaming yet. Observers monitor via the backend log and the on-disk `tick_log.jsonl`.
- 4.F **not done** — no live mode panels in the frontend.
- 4.G **not done** — no timeline scrubber for agent sessions.

#### 4.A Per-Tick Loop

v1: one inference call per tick. The agent prompt combines assess, plan, and act into a single generation call. The scaffold assembles context; the model does the reasoning.

```
Each tick:
1. Agent receives game output from Evennia (room descriptions, NPC responses, combat results)
2. Scaffold assembles prompt: system + game state + goals + loaded scaffolds + memories
3. Agent calls backend POST /api/agent/generate
   → Backend runs model.generate() with hooks OFF → raw response text
   → Backend parses harmony channels from response
   → Backend runs forward pass on full text (prompt + response) with hooks ON
     (identical to current capture_probe() — same CaptureOrchestrator, same hooks)
   → Captures at all target token positions in prompt + response
   → Optionally runs knowledge probe ("What do you think of [NPC]?") with hooks ON
   → Returns: {analysis, action, capture_id, knowledge_capture_id?}
4. Agent sends action to Evennia as game command
5. Agent logs: full prompt, all harmony channels, scaffold versions, capture IDs
6. Tick resolves → next tick opens → repeat
```

**Why one call works:** The scaffold determines what information to include (ASSESS — what's relevant from game state) and what framing to apply (PLAN — which scaffolds to load). The model receives all of this and produces reasoning (analysis channel) and a decision (action channel) in one generation. Future: multi-call chaining for richer reasoning, but the per-tick interface stays the same.

**Why existing capture works:** Causal attention means the residual stream at token position K depends only on tokens 1..K, regardless of what comes after. A post-generation forward pass on the complete text (prompt + response) produces identical activations at each position as capturing during generation would. No hook modifications needed — `capture_probe()` handles this exactly as it handles current batch probes.

#### 4.B Agent ↔ Evennia Connection

The agent connects to Evennia as a standard client via Evennia's WebSocket protocol — same protocol the React frontend uses. This keeps one protocol for all clients.

```
Agent → Evennia:  ["text", ["ask rodek about his work"], {}]
Evennia → Agent:  ["text", ["Rodek's hammer pauses. \"Repairs,\" he says flatly..."], {}]
```

The agent strips any ANSI/HTML markup from received text before including it in the prompt. OOB events (`room_entered`, `room_left`) are ignored by the agent — it doesn't need viz presets or room context metadata.

**Authentication:** Agent logs in as an Evennia account (created during setup). Standard Evennia auth — no special mechanism.

**Game state assembly:** The agent issues `look` on first connect and after each tick resolution to get current room state. It parses the text response for: room name, description, visible NPCs, exits, objects, status (HP in combat). This is standard MUD parsing — the text IS the interface.

#### 4.C Capture Pipeline

Two capture modes, both using the existing `CaptureOrchestrator` and `EnhancedRoutingCapture` unchanged:

**Reasoning capture (every tick):**
1. Backend generates response (hooks OFF — same as current `generate_continuation()`)
2. Backend runs batch forward pass on full text (prompt + response) with hooks ON
3. Hooks capture residual streams, routing, embeddings at all 24 layers
4. `ProbeProcessor` extracts data at target token positions
5. Data written to Parquet via `SessionBatchWriters`

**Knowledge queries (configurable, between ticks):**
1. Backend runs a probe sentence through forward pass with hooks ON
2. Identical to current `capture_probe()` — no changes at all
3. Example: "What do you think of Rodek?" → capture "Rodek"

**Target tokens:** Configured per-session as a word list (e.g., `["they", "them", "tank"]`). The capture step finds all positions of target words in the tokenized text and extracts at each. Extends current single-position extraction: `ProbeProcessor.convert_to_schemas()` signature changes from `target_token_position: int` to `target_token_positions: list[int]` — the internal `positions_to_extract` loop pattern already exists (used for target + context), just needs to accept an arbitrary-length list.

**New endpoint:**

```
POST /api/agent/generate
Body: {
  prompt: string,           # assembled by agent scaffold
  session_id: string,       # active capture session
  target_words: string[],   # from session config
  knowledge_probe?: string, # optional knowledge query
  max_new_tokens: int       # generation limit
}
Response: {
  analysis: string,         # parsed from harmony tags
  action: string,           # parsed from harmony tags
  capture_id: string,       # links to Parquet records
  knowledge_capture_id?: string,
  generated_text: string    # full raw output
}
```

This endpoint lives on the existing FastAPI backend (port 8000). Same process, same model — no separate server. The model is already loaded for batch capture; this endpoint reuses it.

**Parquet schema extension:** Existing schemas (ProbeRecord, RoutingRecord, EmbeddingRecord, ResidualStreamState) gain these optional fields:

| Field | Type | Purpose |
|-------|------|---------|
| `turn_id` | int | Which tick in the agent run (0-indexed) |
| `scenario_id` | string | Which scenario YAML is active |
| `capture_type` | string | `"reasoning"`, `"knowledge_query"`, or `"batch"` (legacy) |

Existing fields remain unchanged. Batch captures (current probes) have `capture_type = "batch"` with `turn_id` and `scenario_id` null. Backward compatible.

#### 4.D Streaming to Observers

After each tick, the backend pushes capture data to subscribed frontends via WebSocket.

```
WebSocket endpoint: /ws/agent-stream
Message format (server → client):
{
  type: "tick_update",
  turn_id: int,
  scenario_id: string,
  capture_id: string,
  analysis: string,          # reasoning channel text
  action: string,            # game command
  game_output: string,       # what Evennia returned
  target_captures: [{        # one per target token found
    word: string,
    position: int,
    residual_umap: [6],      # projected into fitted UMAP manifold
    top1_route: string       # e.g. "L22E3→L23E1"
  }]
}
```

Frontend subscribes when entering an agent observation room. Disconnecting from the room unsubscribes.

**UMAP projection:** Each new capture is projected into a fitted UMAP manifold via `transform()` — fast enough for real-time updates.

**Bootstrap requirement:** UMAP `fit()` requires a dataset — you can't fit on a single point. Agent sessions must specify a bootstrap source when created: a prior batch session whose fitted manifold is reused for projection. Example: run 40 batch probes with the same target words first, fit UMAP, then agent session captures project into that manifold. The bootstrap session ID is stored in agent session metadata. LiveUMAP is unavailable until a bootstrap source is specified.

#### 4.E Harmony Channel Format

The system prompt instructs the model to output in tagged format:

```
<analysis>
[Internal reasoning — raw chain of thought. This is the interpretability signal.
Contains explicit social stance assessment, conflict recognition, decision reasoning.
Rich with pronoun references to NPCs ("they seem suspicious", "I should help them").]
</analysis>
<action>
[Single game command — what the agent does this tick.
Examples: "ask rodek about his work", "attack goblin", "north", "chop tree with axe"]
</action>
```

**Parsing:** Backend extracts content between tags using simple string matching (not regex — tags are exact). If tags are missing or malformed, the entire output is treated as the action channel and logged as a parse warning.

**Commentary channel:** AI_SYSTEM_DESIGN.md describes a third channel for tool calls. In v1, scaffold operations (memory retrieval, scaffold search) are handled by the agent client before the inference call, not by the model via tool use. Commentary channel is reserved for future multi-call mode. Not used in v1.

**Analysis channel as research data:** The analysis text is the primary interpretability signal. It's logged to disk per tick and stored alongside capture data. ConceptMRI labels for clustering can be derived from analysis content (e.g., presence of social stance language) or from scenario ground-truth YAML.

#### 4.F Live Mode Panels

When observing an active agent session, Q4 switches from DatasetPanel to agent stream panels:

**ReasoningStream (Q4, top):** Scrolling display of analysis channel text, one entry per tick. Each entry shows: turn number, the analysis text, the action taken, and Evennia's response. New entries auto-scroll. Click an entry to select it for Q1 highlighting (same bidirectional sync as DatasetPanel).

**AgentStatusBar (toolbar area):** Current room, turn count, scenario name, active target words, session state (running/stopped). Compact — fits in toolbar row.

**LiveUMAP (Q1, alongside Sankey):** Single point on the bootstrap session's fitted UMAP manifold (see §4.D bootstrap requirement), updated after each tick's capture. Trail showing the last N points. Color-coded by primary axis (label, capture_type, etc.). When the agent's social stance shifts (e.g., "uncertain" → "suspicious" → "confirmed enemy"), the point moves through the basin landscape in real time. Panel is disabled if no bootstrap source is configured.

**Sankey refresh:** After each capture, the route data for the current session updates. Sankey re-renders to include the new probe. The latest capture's route is highlighted.

#### 4.G Timeline Scrubber

Same step controls as DatasetPanel (§5.B), but data source is the agent session's tick history instead of a static dataset. Forward/back steps through ticks. Auto-play replays the session. Each step updates: Q1 highlighting (which route is active), Q4 highlighting (which reasoning entry is selected), and LiveUMAP (which point is highlighted).

#### 4.H Session Lifecycle

**Session creation:** `agent start <agent_name> <scenario>` → REST call to `POST /api/agent/start`:
1. Creates a new capture session via `SessionManager` (extended: `target_words: list[str]` replaces singular `target_word`, `total_pairs: Optional[int] = None` for open-ended sessions, `bootstrap_session_id: str` for UMAP projection)
2. Session metadata includes: `scenario_id`, `target_words[]`, `capture_type_config` (which modes to run), `agent_name`, `bootstrap_session_id`
3. Agent connects to Evennia, navigates to scenario start room
4. Tick loop begins

**Session↔scenario:** One session per scenario run. Running the same scenario again creates a new session. The `scenario_id` field links captures to the scenario YAML (ground-truth labels, room structure).

**Session end — three triggers:**
1. `agent stop` — manual halt. Session finalized immediately.
2. Scenario outcome flag — YAML defines terminal flags (e.g., `rodek_confronted`, `dandelion_seeded`). When a terminal flag is set, the session auto-finalizes after logging the final tick.
3. Agent navigates out of the scenario area — session finalized, agent returns to hub.

**Finalization:** Same as current batch sessions — manifest written, state set to "completed", Parquet files flushed. Session appears in the session list alongside batch sessions. Researcher can load it in the Phase 1 UI for analysis.

#### 4.I Tick Speed

Per-room attribute in scenario YAML:

```yaml
rooms:
  the_smithy:
    tick_speed: instant    # instant | fast (5s) | medium (20s) | slow (60s) | contemplative (unlimited)
```

Admin command for runtime changes: `@tick_speed <speed>` — changes the current room's tick speed.

**Instant mode:** Tick resolves immediately after the agent submits its action. No waiting. The loop runs as fast as inference allows (~2-4 seconds per tick depending on generation length). Used for batch capture runs.

**Speed as research variable:** Different speeds create different conditions. Instant mode maximizes throughput. Slow/contemplative modes allow observers to watch in real time and create time pressure for the agent (if the scaffold includes time awareness).

**Verification checklist:**
- `agent start em suspicious_blacksmith` → session created, agent connects to Evennia, enters smithy room
- Agent issues `look` → receives room description → assembles prompt → calls `/api/agent/generate`
- Response parsed: analysis channel shows reasoning about Rodek, action channel shows game command
- Capture written to Parquet with `turn_id=0`, `scenario_id=suspicious_blacksmith`, `capture_type=reasoning`
- Knowledge probe fires: "What do you think of Rodek?" → capture with `capture_type=knowledge_query`
- Agent sends action to Evennia → Rodek responds → next tick
- `/ws/agent-stream` delivers tick update to observer's browser
- Q4 shows analysis text; Q1 highlights capture route; LiveUMAP point appears
- Multiple ticks complete → timeline scrubber shows full history, step forward/back works
- Scenario outcome flag `rodek_confronted` set → session auto-finalizes
- Session appears in session list → researcher loads it → Sankey/UMAP renders all captures
- `@tick_speed instant` → ticks resolve immediately (batch speed)
- `@tick_speed slow` → 60-second tick window, observers can watch in real time
- `agent stop` → loop halts, session finalized, all data persisted
- Legacy batch capture (`POST /api/probes/sentence-experiment`) still works unchanged

### Phase 5 — Middleware Consolidation & Agent Intelligence

**5.A-5.B: Middleware consolidation** (nice-to-have, non-blocking — 5.C-5.D do not depend on this)

| Item | Task |
|------|------|
| 5.A | ConceptMRI backend proxies Evennia (single WS endpoint for frontend) |
| 5.B | Normalized message format for all event types |

**5.C-5.D: Agent intelligence** (depends on Phase 4 agent sessions)

| Item | Task |
|------|------|
| 5.C | Offline reflection (REM) — Claude Code reads session logs, proposes scaffold refinements |
| 5.D | Scaffold persistence and version tracking |

**Verification checklist:**

Middleware (5.A-5.B):
- Single WebSocket endpoint (`/ws`) serves both Evennia events and ConceptMRI stream data
- Frontend connects to one endpoint instead of two separate WebSockets
- Normalized message format: all events parse through a single handler

Agent intelligence (5.C-5.D):
- REM reflection: Claude Code reads session logs, produces scaffold refinement suggestions
- Scaffold versions tracked: can diff scaffold v1 vs v2 and see what changed

### Phase 6+ — Multi-Agent, IFS/Swarm

Per AI_SYSTEM_DESIGN.md. Pending research results from earlier phases.

- Multi-perspective prompting (narrator, analyst, strategist, critic)
- Swarm coordination — multiple agents in same Evennia world
- ConceptMRI captures all agents' residual streams simultaneously

---

## 11. Progressive Connection Model

```
Phase 1: Local command parsing only                     (1 connection: REST)
Phase 2: Evennia WS + ConceptMRI REST                   (2 connections)
Phase 4: Evennia WS + ConceptMRI WS + REST              (3 connections)
Phase 5: ConceptMRI WS (proxies Evennia) + REST         (2 connections)
```

---

## 12. Architecture Decisions

### 12.A Agent Management Surface

| Action | Where | Why |
|--------|-------|-----|
| Choose scaffolds | Claude Code | Nuanced, benefits from Claude reasoning |
| Configure capture | Claude Code | Technical, same as current probe setup |
| Start agent session | Claude Code via `/agent` skill OP-1 (primary), or MUD `agent start` (Builder-only) | `POST /api/agent/start` with `auto_start: true`. The MUD commands `agent start`/`agent stop` exist in `scenario_commands.py` (Builder-locked) and call the same API, but the `/agent` skill is the primary workflow. |
| Stop agent session | Claude Code via `/agent` skill OP-2, or MUD `agent stop` (Builder-only) | `POST /api/agent/stop` finalizes the session. |
| Monitor live traces | Backend log + on-disk artifacts | Phase 4.D streaming not yet shipped. Researchers tail `tick_log.jsonl` and the backend log. |
| Run interactive viz | Viz section Run buttons | Click Run in ExpertRoutesSection or ClusterRoutesSection |
| Deep analysis + reports | Claude Code | `/analyze` — reads sentences, writes reports and element descriptions |
| Review proposals | Claude Code | Approve/reject scaffold changes |

### 12.B Viz Presets in Room Config

Researcher configures clustering schema, color axes, gradients, layer range via toolbar controls. Viz presets are saved to micro-world YAML; visitors entering rooms get that curated view automatically. Preset saving is a Phase 2+ feature. For Phase 1, presets are hand-configured in YAML.

### 12.C Data Model

```
Micro-world (YAML config file)
├── Session A (basin identification capture, capture_type=batch)
│   ├── Clustering schema 1
│   └── Clustering schema 2
├── Session B (temporal capture, capture_type=batch)
│   ├── Run 1, Run 2, ...
│   └── All streams saved for review
└── Session C (agent run, capture_type=reasoning + knowledge_query)
    ├── Per-tick: reasoning captures (post-generation forward pass)
    ├── Per-tick: knowledge query captures (optional probes)
    ├── Logs: full prompts, harmony channels, scaffold versions
    └── Metadata: scenario_id, turn_id per capture
```

Sessions stay primary in `data/lake/`. All three session types produce standard Parquet files with the same schema — agent sessions add `turn_id`, `scenario_id`, and `capture_type` fields. Micro-world config is a lens over them.

### 12.D Scope Split: MUD vs Claude Code

The hybrid interface (toolbar + terminal) replaces ExperimentPage's visualization controls and exploration workflow. The interface layout is identical for everyone; researcher power comes from toolbar controls being enabled (visitor rooms grey them out) and having more terminal commands available (Evennia auth in Phase 2+).

Probe design, output categorization, and deep analysis (reading sentences, writing reports, generating element descriptions) remain Claude Code workflows. The hybrid interface is the exploration and visualization surface; Claude Code is the analysis runtime. Together they cover the full pipeline. `run cluster` / toolbar [Run] and `/analyze` (Claude Code) are complementary tools at different depths, not competing interfaces.

### 12.E Why Evennia?

Python + asyncio (same stack as ConceptMRI backend). Mature MUD framework with built-in auth, permissions, room/exit system, and command parsing. WebSocket client protocol that works from browser (xterm.js). Active maintenance. The alternative — a custom WebSocket server — would mean reimplementing room management, permission layers, and text formatting that Evennia provides out of the box. Phase 1 works without Evennia (local parsing), so there's zero lock-in risk: if Evennia proves wrong, only Phase 2+ changes.

---

## 13. Design Document Reference

| Topic | This Document | LLMud Design Docs |
|-------|--------------|-------------------|
| Research motivation | Section 1 | VISION.md (goals, ethics, connection to other research) |
| Agent cognitive loop | Phase 4 (§4.A per-tick loop) | AI_SYSTEM_DESIGN.md (full spec, multi-call future) — frozen |
| Scaffold system | Referenced | AI_SYSTEM_DESIGN.md (5 levels) — frozen |
| World building | Rooms/config in section 9 | WORLD_DESIGN.md (scenarios, tick system) — frozen |
| Observer spaces & institute | Section 4.E (deferred) | INSTITUTION_DESIGN.md (full vision) — frozen |

---

## 14. Open Items

| Item | Status | Blocking? |
|------|--------|-----------|
| Temporal capture timeout | Frontend API client has 60s timeout (AbortController); temporal captures can take longer. Need per-request timeout override or longer default for temporal endpoints. | Phase 1 |
| Guest identity persistence | Evennia guest accounts work but identities aren't persistent across reconnects. | No |
| External MUD connectivity | Client should eventually support connecting to external MUDs for trace capture. Architectural principle: capture pipeline stays at model layer (PyTorch hooks), connection layer is just a text source. Don't hardcode Evennia assumptions into capture/analysis. May be a separate fork. | Future |
| All-token residual capture in agent runs | Currently the agent loop captures residuals only at configured target token positions. The Token Knowledge Graph (§17) is constrained to target tokens for v1; expanding to all-token capture is a separate decision. | Pending Work E |
| bitsandbytes NF4 forward-hook compatibility | Pending Work F (steered generation) needs `register_forward_hook` writes to the residual stream to propagate through quantized layers. Verification spike not yet done. | Pending Work F |
| Cache-on vs cache-off steering | `steeringandscenarios.md §5` lists three approaches for sustained steering; Pending Work F v1 picks one and documents the choice. | Pending Work F |
| Live mode panels (4.D, 4.F, 4.G) | WebSocket streaming, ReasoningStream/AgentStatusBar/LiveUMAP, and the timeline scrubber for agent sessions are not yet built. Researchers monitor agent runs via the backend log and on-disk `tick_log.jsonl`. | No |
| Scaffold text in ProbeRecord | Not currently stored. Dataset viewer shows input text only until schema change. | Phase 4+ |

### 14.A Resolved Items

- **xterm.js ANSI handling** — Phase 2 confirmed Evennia's webclient protocol; ANSI handled by xterm.js directly.
- **Evennia in same venv** — runs in the same `.venv` as the backend; no IPC needed.
- **LLMud doc cleanup** — superseded docs removed, remaining 3 frozen.
- **ExperimentPage removal** — kept as `/legacy/:id`. Will not be deleted.
- **Dataset API in client** — `getSessionDetails()` already returns sentences with `generated_text` and `output_category`.
- **Desktop-only scope** — decided.
- **World file reader** — Evennia reads YAML scenario files directly via `ScenarioRoom` typeclass. No backend `/worlds` API.
- **Lens registry storage location** — resolved in plan `cozy-herding-reddy`: in-place alongside existing schema files (no migration of existing data).

---

## 15. Lens Switching

**Background.** A schema is a clustering configuration computed from one session and applied to that session's residual streams. Until April 2026, schemas were trapped inside the source session.

**The lens model.** A *lens* is the fitted UMAP reducer plus cluster centroids in **original residual stream space**, derived from one session but applicable to any session whose residual streams have the same hidden size. Schemas are how lenses are *computed*; lenses are how clusterings are *applied across sessions*.

**Persistence.** Per lens, alongside the existing schema files in `data/lake/<sid>/clusterings/<schema>/`:

| File | Purpose |
|------|---------|
| `lens.joblib` | `{layer_int: fitted_umap_reducer}` |
| `centroids_original.parquet` | Cluster centroids in residual stream space, n_clusters × hidden_size per layer. **Steering-only** — used for discriminating-neuron correlation (§16), not for lens application or cluster assignment. |
| `centroids_umap.json` | Cluster centroids in 6D UMAP space (mirrors existing `centroids.json`) |
| `lens_meta.json` | name, source_session_id, source_schema_name, layers, n_clusters, hidden_size, target_words, first_separation_layer |

**Application.** When a non-native lens is active, the cluster route analysis pipeline projects the active session's residual streams through `lens.umap.transform()` and assigns each projected point to its nearest UMAP-space centroid (from `centroids_umap.json`). The Sankey/trajectory output is identical in shape — only the cluster identities change.

**First-separation layer.** Each lens has a `first_separation_layer`: the smallest layer index where the average inter-cluster centroid distance in UMAP space exceeds the average within-cluster spread (mean L2 of cluster members from their UMAP centroid). Falls back to the lens's deepest fitted layer if no layer separates by this rule. This layer is the target for eventual steering generation (Pending Work F, §14) — steering at the separation point lets all downstream layers carry the perturbation through.

**Lens registry.** A new endpoint `GET /api/lenses` enumerates all `lens_meta.json` files across all sessions. The registry service caches the scan at startup and invalidates on write (walking 134+ session dirs on NTFS/WSL2 per request would be slow). See Pending Work C in plan `cozy-herding-reddy` for implementation details.

**Frontend.** A new top-toolbar LensSelector introduces a single global state value `activeLensId`. Q1 viz, Q2 cluster cards, Q2 trajectory cards, and Q4 dataset panel all consume `activeLensId` as their lens source. When `activeLensId` matches the current session's native schema, behavior is unchanged. Lens switching only applies to MUDApp; `/legacy` gets nothing new.

---

## 16. Steering Panel (visualization scaffold)

**Goal.** Provide a per-cluster surface that exposes the top discriminating neurons for that cluster and a comparison view of steering experiments that have been run against it. The actual model intervention is out of scope for this section — the panel reads from precomputed neuron analyses and from saved steering experiment results. Pending Work F lands the intervention later.

**Discriminating neurons.** For each lens cluster, compute the top-K neurons that distinguish it from the other clusters in the lens, in the original residual stream space at the cluster's own layer (cluster IDs encode their layer, e.g. `L12C2` is layer 12, cluster 2). Methods: point-biserial correlation (binary lenses), one-vs-rest correlation (multi-class). Output cached at `clusterings/<schema>/discriminating_neurons_<layer>_<method>.parquet`.

**Steering experiments.** Each steering experiment is a JSON file at `clusterings/<schema>/steerings/<experiment_name>.json`, containing:

```json
{
  "name": "positive_1x",
  "cluster_id": "L12C2",
  "layer": 12,
  "neurons": [{"neuron_idx": 1442, "activation": 0.74}],
  "created_at": "2026-04-12T..."
}
```

The "baseline" experiment per cluster is auto-generated from probe data: it captures the actual mean activation of the top-K neurons across all probes assigned to that cluster, with no perturbation. Other experiments (`positive_1x`, `negative_1x`, etc.) are written by the future steering pipeline (Pending Work F) or hand-authored by Claude when running steering scripts directly in Claude Code.

**Frontend.** `SteeringPanel.tsx` mounts inside `ContextSensitiveCard` when a cluster node is selected. The layer is fixed by the clicked cluster — no slider (clusters are layer-bound). Shows:

- Cluster header (existing card info: ID, label, size, purity)
- **Top-K slider** (defaults to 20)
- **Correlation chart** — vertical bars of the top-K discriminating neurons' coefficients (point-biserial or one-vs-rest), scaled -1 to +1, sorted by absolute value
- **Steering comparison chart** — stacked rows of vertical bars, one row per saved steering experiment. Each row is a horizontal lineup of vertical bars representing each top-K neuron's activation under that experiment, -1 to +1. Same neuron order as the correlation chart so the rows align column-wise. Default state: only the "baseline" row.
- Copyable Claude command snippet: `/steer lens=<lens_id> cluster=<cluster_id> direction=positive magnitude=1.0` — a hint to the researcher to run the experiment in Claude Code. When Pending Work F lands, this command becomes invokable; until then it's a copy-paste reference.

---

## 17. Token Knowledge Graph

**Goal.** Surface the model's "current understanding" of any single token by showing which lens cluster it falls into across every available lens.

**Demo case.** In the `polysemy_400` session, expand a trajectory for a sentence containing "tank". Click the word *tank*. The trajectory card's knowledge graph subsection shows: "polysemy_explore lens → vehicle cluster (L12C2)". This is the bootstrap demo for v1 — the polysemy lens applied to its own source word.

**General case.** Click any captured token in any displayed sentence. The backend looks up the token's residual stream position, projects it through every applicable lens, and returns the assigned cluster per lens. "Applicable" for v1 means: lens `hidden_size` matches AND `target_words` includes the token. Future: a `global` flag in `lens_meta.json` could mark lenses applicable to any token regardless of target_words.

**Constraint.** Token-level capture must exist for the clicked position. Currently the probe pipeline captures residuals only at configured target token positions, so for v1 the demo works only at target tokens. Non-target tokens are rendered greyed-out with a tooltip explaining the constraint. Expanding capture to all tokens is a separate decision tracked in §14.

**Frontend.** Trajectory card extension only — no new top-level panels. Click handler on token spans → `GET /api/sessions/<sid>/trajectories/<traj_id>/tokens/<position>/lenses` → renders a list of `{lens_name: cluster_label}` rows, target-matched lenses pinned to the top. Only applies to MUDApp; `/legacy` gets nothing new.
