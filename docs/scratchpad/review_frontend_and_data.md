# Frontend & Data Layer Architecture Review

**Date:** 2026-04-07
**Scope:** All frontend source, data files, documentation, skills, project config
**Branch:** phase0-backend-cleanup

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Frontend File-by-File Review](#2-frontend-file-by-file-review)
3. [Data Layer Review](#3-data-layer-review)
4. [Documentation Review](#4-documentation-review)
5. [Skills Review](#5-skills-review)
6. [Project Config Review](#6-project-config-review)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Issues Summary](#8-issues-summary)

---

## 1. High-Level Architecture

### Frontend Stack
- **React 19** + **Vite 7** + **TypeScript 5.8** + **Tailwind 4**
- **ECharts** (Sankey, temporal lag) + **echarts-gl** (3D trajectory)
- **xterm.js 6** for MUD terminal
- **react-router-dom 7** for routing (but only 1 route used)
- **jStat** for chi-square statistics
- **react-markdown** for rendering AI analysis reports

### Data Flow Summary
```
Browser ─── REST (port 8000) ──► FastAPI backend (captures, analysis, clustering)
       └── WebSocket (port 4002) ──► Evennia MUD (navigation, room context, OOB events)
```

React holds all visualization state locally (no context providers). Evennia sends OOB messages (`room_entered`, `room_left`) that trigger session/preset changes in React. React then calls the FastAPI backend directly. Evennia never talks to FastAPI.

### Layout
Quadrant grid (`MUDApp`):
- **Q1 (top-left):** Visualizations — Expert Sankey, Cluster Sankey, Trajectory Plot, Temporal Analysis
- **Q2 (top-right):** Analysis — WindowAnalysis (contingency table), ContextSensitiveCard (click details)
- **Q3 (bottom-left):** MUD Terminal (xterm.js + Evennia WebSocket)
- **Q4 (bottom-right):** Dataset — FilteredWordDisplay (probe sentences with color badges)

---

## 2. Frontend File-by-File Review

### 2.1 Entry Points

#### `frontend/src/main.tsx` (10 lines)
- **Purpose:** React entry point. Renders `<App />` inside `<StrictMode>`.
- **No issues.**

#### `frontend/src/App.tsx` (17 lines)
- **Purpose:** Router setup. Single route: `/` → `MUDApp`.
- **Imports:** `react-router-dom`, `MUDApp`, `App.css`
- **Issues:**
  - **DEAD CODE:** `WorkspacePage` and `ExperimentPage` exist in `pages/` but are NOT routed. App.tsx only has a single route to `MUDApp`. These pages are unreachable.
  - Wraps content in `bg-gray-50` div, but MUDApp applies its own `bg-gray-100`. The outer bg-gray-50 is invisible (MUDApp fills the viewport).

### 2.2 CSS Files

#### `frontend/src/index.css` (48 lines)
- **Purpose:** Global styles. Tailwind directives, base typography, sidebar/panel width overrides.
- **Issues:**
  - Lines 5-18 (`:root` block) set dark theme defaults (`color-scheme: light dark`, dark background `#242424`). But the app uses Tailwind's `bg-gray-100`, `bg-white` etc., which override these entirely. The dark defaults are **dead CSS from Vite scaffold**.
  - Lines 20-25 (`prefers-color-scheme: light`) are also dead — Tailwind controls all colors.
  - `.sidebar-narrow` and `.word-panel-narrow` (lines 33-42) have `!important` width overrides — used only in ExperimentPage, which is unreachable.
  - Line 44-48: `.sidebar-narrow svg` size override scoped to avoid ECharts breakage — clever but brittle.

#### `frontend/src/App.css` (43 lines)
- **Purpose:** Vite scaffold boilerplate CSS.
- **Issues:**
  - **ENTIRELY DEAD CODE.** Logo styles (`.logo`, `.logo:hover`, `@keyframes logo-spin`), `.card`, `.read-the-docs` — none of these classes are used anywhere in the app. This is leftover from Vite's default template.

#### `frontend/src/theme.css` (9 lines)
- **Purpose:** Tailwind layer extension defining `--color-blue-200`.
- **Issues:**
  - **DUPLICATE Tailwind directives.** Both `index.css` and `theme.css` include `@tailwind base/components/utilities`. Only `index.css` is imported in `main.tsx`. `theme.css` is **never imported** — it's a dead file.

### 2.3 Pages

#### `frontend/src/pages/MUDApp.tsx` (433 lines)
- **Purpose:** Main application page. Quadrant layout with toolbar, viz, analysis, terminal, and dataset panels.
- **Key state:** selectedSession, sessions, sessionDetails, filterState, roomContext, currentRouteData, currentClusterRouteData, elementDescriptions, selectedCard
- **Hooks used:** useAxisControls, useClusteringConfig, useSchemaManagement
- **Dependencies:** Toolbar, ExpertRoutesSection, ClusterRoutesSection, TemporalAnalysisSection, WindowAnalysis, ContextSensitiveCard, FilteredWordDisplay, MUDTerminal
- **Data flow:**
  - Loads sessions on mount via `apiClient.listSessions()`
  - Session selection triggers `resetForNewSession()` which fetches details
  - OOB events from MUD terminal trigger `handleOOB()` → session/preset changes
  - Route data loaded callbacks (`handleRouteDataLoaded`, `handleClusterRouteDataLoaded`) detect axes
- **Issues:**
  - **Line 34:** `serverBusy` state is declared but **never used** — it's set but never read in JSX. ExperimentPage uses it to show a banner, but MUDApp doesn't.
  - **Lines 77-94:** Schema sync `useEffect` has `clustering` in the dependency array warning — eslint rule `react-hooks/exhaustive-deps` would flag `clustering.setReductionDims`, etc. as missing deps (though they're stable).
  - **Line 13:** `RoomContext` type import from evennia.ts is correctly used for the MUD integration.
  - Lines 354-373: Window analysis IIFE rendering inside JSX — functional but could be a standalone component for clarity.

#### `frontend/src/pages/WorkspacePage.tsx` (186 lines)
- **Purpose:** Session list dashboard with sidebar.
- **Issues:**
  - **DEAD PAGE.** Not routed in App.tsx. Completely unreachable.
  - Imports `FlaskIcon`, `ChartBarIcon` from Icons.
  - Has a "New Experiment" button that navigates to `/experiment` — a route that doesn't exist.
  - Uses `useNavigate()` from react-router-dom.

#### `frontend/src/pages/ExperimentPage.tsx` (871 lines)
- **Purpose:** Full analysis page with sidebar controls, multi-session support, 3-column layout.
- **Issues:**
  - **DEAD PAGE.** Not routed in App.tsx. Completely unreachable.
  - Contains a local `AxisControls` component (lines 28-135) that duplicates functionality now in the Toolbar.
  - Contains `AxisControlsProps` interface (lines 28-37) that's only used locally.
  - Has multi-session checkbox UI (lines 440-461) — MUDApp only supports single session.
  - Lines 139-145: Unused `id` parameter from `useParams` (route doesn't exist).
  - Lines 144/355: `serverBusy` state is declared, set, and used in a banner (lines 421-426). This is the correct implementation that MUDApp is missing.
  - **Massive code duplication** with MUDApp: handleRouteDataLoaded, handleClusterRouteDataLoaded, schema sync effect, card selection logic, window analysis rendering — all duplicated nearly line-for-line.

### 2.4 Hooks

#### `frontend/src/hooks/useEvennia.ts` (146 lines)
- **Purpose:** WebSocket hook for Evennia MUD connection.
- **Connection lifecycle:** connect → WebSocket open → send `client_options` (raw mode) → parse messages → auto-reconnect with exponential backoff (1s → 30s max)
- **Message parsing:** `[cmdname, args, kwargs]` JSON. "text"/"prompt" → `onText` callback. Everything else → `onOOB` callback.
- **Exports:** `status`, `connect`, `disconnect`, `sendCommand`, `sendOOB`
- **Issues:**
  - Default URL hardcoded to `ws://localhost:4002` (line 10). Not configurable via env var. Should read from environment for deployment flexibility, though for a self-hosted research tool this is acceptable.
  - `sendOOB` (line 129) is exported but never used by any consumer. Only `sendCommand` is used in MUDTerminal.

#### `frontend/src/hooks/useAxisControls.ts` (101 lines)
- **Purpose:** State management for input/output color axes, gradients, shape axes, layer range.
- **Exports:** Full state + all setters as `AxisControlsState` interface.
- **No issues.** Clean separation.

#### `frontend/src/hooks/useClusteringConfig.ts` (43 lines)
- **Purpose:** State management for clustering parameters (K, method, dims, source).
- **Exports:** Full state + setters as `ClusteringConfigState`.
- **No issues.** Clean and minimal.

#### `frontend/src/hooks/useSchemaManagement.ts` (48 lines)
- **Purpose:** Fetches available clustering schemas and their details (reports, element descriptions).
- **API calls:** `apiClient.listClusterings()`, `apiClient.getClusteringDetails()`
- **Issues:**
  - Line 15: `params: any` in the schema type — should be typed to match backend response.

#### `frontend/src/hooks/useTemporalAnalysis.ts` (417 lines)
- **Purpose:** Complete temporal analysis state: basin selection, run management, lag data loading, group aggregation, scrubber, metrics.
- **Key logic:**
  - Derives basin options from cluster route data (parsing "L22C3" node names)
  - Groups runs by condition key (schema + basins + mode + sequence)
  - Computes aggregate mean/std lines per group
  - Computes routing lag metrics (3-consecutive-above-0.5 threshold)
  - Computes delta-persistence between cache-on and cache-off groups
- **Issues:**
  - Line 231: `// eslint-disable-line react-hooks/exhaustive-deps` — intentionally suppresses warning because `lagDataMap` in deps would cause infinite loop. This is correctly handled but could be documented better.
  - **CONDITION_COLORS** (line 82-87): Only 4 colors defined. If more condition types are added, they fall back to gray. This is fine for the current 2x2 factorial (cache_on/off x block_ab/ba).
  - Line 88-91: `conditionColor` function uses string concatenation to build mode key — fragile if processing mode format changes.

### 2.5 Types

#### `frontend/src/types/api.ts` (325 lines)
- **Purpose:** TypeScript interfaces matching backend Pydantic schemas.
- **Key types:** SessionListItem, SessionDetailResponse, RouteAnalysisResponse, SankeyNode, SankeyLink, TopRoute, DynamicAxis, ClusteringConfig, TrajectoryPath, ReductionPoint
- **Issues:**
  - Lines 77, 178, 189, 289: Multiple uses of `[key: string]: any` and `Record<string, any>` — loses type safety. The backend has well-defined schemas that could be mirrored more precisely.
  - Lines 8, 192-204: `ExecutionResponse`, `LLMInsightsRequest`, `LLMInsightsResponse` are defined but their API methods are rarely/never called from the active code paths.
  - Line 80: `FilterConfig` is a simple `{ labels?: string[] }` — matches backend but could be more explicit.

#### `frontend/src/types/analysis.ts` (7 lines)
- **Purpose:** Defines `SelectedCard` discriminated union for click-detail cards.
- **Types:** expert | highway | cluster | route, each carrying `SankeyNode & Record<string, any>` or `SankeyLink & Record<string, any>`.
- **Issues:**
  - `Record<string, any>` is used because click handlers enrich data with runtime properties (`_fullData`, `_totalProbes`, `_window`, etc.). This works but means the type doesn't document what properties are actually available.

#### `frontend/src/types/temporal.ts` (82 lines)
- **Purpose:** Types for temporal analysis — capture request/response, run metadata, lag points, basin options, run groups, aggregate lines.
- **No issues.** Well-structured, matches backend types.

#### `frontend/src/types/evennia.ts` (29 lines)
- **Purpose:** Types for Evennia OOB events — RoomContext, VizPreset, RoomEnteredPayload, RoomLeftPayload.
- **No issues.** Clean, matches the OOB protocol defined in architecturemud.md.

### 2.6 API Client

#### `frontend/src/api/client.ts` (313 lines)
- **Purpose:** Singleton API client wrapping `fetch` with timeout, error handling, and typed endpoints.
- **Base URL:** `http://localhost:8000/api` (hardcoded)
- **Methods:** 16 endpoints covering session CRUD, route analysis, cluster analysis, temporal runs, lag data, clustering schemas, reduction, LLM insights, sentence experiments.
- **Issues:**
  - Line 24: Base URL hardcoded. Not configurable via environment variable. For a self-hosted tool this is acceptable.
  - Line 50: Default timeout is 60s. Some operations (temporal capture, large analysis) may exceed this. The class allows per-call timeout override, which is good.
  - Lines 99-103: `executeProbeSession` method exists but sentence experiments are the actual workflow. This method may be vestigial from an earlier probe design.
  - Lines 241-246: `generateLLMInsights` exists but the LLM insights feature requires an external API key (OpenAI/Anthropic). Per CLAUDE.md, Claude Code IS the analysis runtime — no separate LLM calls needed. This method may be dead code from an earlier architecture.
  - Lines 127-163: `pollSessionUntilComplete` uses recursive setTimeout — functional but could leak if component unmounts during polling. No AbortController integration.

### 2.7 Utilities

#### `frontend/src/utils/colorBlending.ts` (252 lines)
- **Purpose:** Color system for Sankey visualization. Gradient schemes, categorical palettes, N-way weighted blending, axis-aware coloring, traffic visual properties.
- **Key functions:** `getGradientColor`, `getAxisColor` (2-value gradient vs N-value categorical), `getNodeColor` (distribution-based), `getPointColor` (individual values), `getAxisPreview`, `getTrafficVisualProperties`
- **Exports:** `GradientScheme`, `GRADIENT_SCHEMES`, `GRADIENT_AUTO_PAIRS`, all color functions.
- **No issues.** Well-documented, handles edge cases (unknown values → gray, empty distributions → midpoint).

#### `frontend/src/utils/filterState.ts` (19 lines)
- **Purpose:** Converts frontend `FilterState` (Set-based) to backend `filter_config` (array-based).
- **No issues.** Simple and correct.

#### `frontend/src/utils/evenniaAnsi.ts` (73 lines)
- **Purpose:** Converts Evennia markup codes (`|r`, `|g`, `|[b`, etc.) to ANSI escape sequences for xterm.js. Also unescapes HTML entities.
- **Reference:** Comments cite `evennia/utils/ansi.py lines 146-197`.
- **Issues:**
  - Bright/dark foreground naming is inverted from conventional ANSI: `|r` (lowercase) is mapped to bright (1;31m) and `|R` (uppercase) to dark (0;31m). This matches Evennia's convention, not standard ANSI convention, which is correct behavior but potentially confusing.
  - Background colors: Both lowercase and uppercase map to the same ANSI codes (e.g., `|[r` and `|[R` both → 41m). This is correct per Evennia's spec.

### 2.8 Constants

#### `frontend/src/constants/layerRanges.ts` (47 lines)
- **Purpose:** Defines 4 layer ranges (0-5, 5-11, 11-17, 17-23), each containing 6 two-layer windows.
- **Issues:**
  - Model has 24 layers (0-23). The ranges cover them with slight overlap (layer 5 in range1 and range2, layer 11 in range2 and range3, layer 17 in range3 and range4). This is intentional — overlapping boundary layers.
  - The constant is not typed with `as const` — `LAYER_RANGES` is typed as a plain object. Code accesses it via `selectedRange as keyof typeof LAYER_RANGES` (safe).

#### `frontend/src/constants/outputNodes.ts` (21 lines)
- **Purpose:** Output node prefix (`Generated:`) and helper functions (`isOutputNode`, `isOutputLink`, `stripOutputPrefix`).
- **No issues.** Clean single-source-of-truth for magic string.

#### `frontend/src/constants/workspace.ts` (2 lines)
- **Purpose:** Defines `MAX_RECENT_SESSIONS = 5`.
- **Issues:**
  - **DEAD CODE.** Never imported anywhere. Used to be used by WorkspacePage, which is now dead.

### 2.9 Components — Terminal

#### `frontend/src/components/terminal/MUDTerminal.tsx` (119 lines)
- **Purpose:** xterm.js terminal with Evennia WebSocket connection. Output-only terminal (stdin disabled) with separate text input.
- **Architecture:**
  - Uses `useEvennia` hook for WebSocket management
  - Receives `onOOB` callback prop — passes through to useEvennia
  - Text messages go through `evenniaToAnsi()` conversion before writing to terminal
  - Status changes display colored indicators in terminal
  - Auto-connects on mount, auto-disconnects on unmount
  - ResizeObserver handles container resizing
- **Issues:**
  - Line 59: `disableStdin: true` — terminal is output-only. User input goes through the separate `<input>` element. This is correct for the MUD use case (command-line input, not full terminal emulation).
  - Terminal theme hardcoded (green on dark gray). No user customization.
  - Input has no command history (up/down arrow). This is a missing feature for a MUD terminal.

### 2.10 Components — Toolbar

#### `frontend/src/components/toolbar/Toolbar.tsx` (444 lines)
- **Purpose:** Compact ribbon toolbar with all visualization controls.
- **Sections:** Role badge, Session selector, Color axis + gradient, Blend axis, Shape axis, Color preview, Output colors, Expert route controls, Schema + clustering params, Claude instruction text, Label filter pills, Session info.
- **Props:** 16 props covering sessions, axes, clustering, schema, filters, route data, room context.
- **Issues:**
  - Line 53: Visitor check: `const controlsDisabled = roomContext?.role === 'visitor'` — correctly greys out controls via `opacity-60 pointer-events-none`.
  - Line 55: Session locked in micro_world rooms — prevents session dropdown changes.
  - Lines 350-372: When no schema selected, shows inline clustering param controls. When schema selected, shows read-only summary. This duplicates clustering UI that also appears in ExperimentPage sidebar.
  - Line 335: Variable shadowing: `const s = availableSchemas.find(s => s.name === selectedSchema)` — `s` shadows the outer `s` parameter from the `.find()`. Works but poor practice.

### 2.11 Components — Charts

#### `frontend/src/components/charts/SankeyChart.tsx` (316 lines)
- **Purpose:** Single ECharts Sankey diagram with color-blended nodes/links, click handling, tooltips.
- **Key logic:**
  - Computes node colors from label_distribution (primary) and optional secondary axis
  - Output nodes use separate output color axes or fall back to matching input colors
  - Traffic-based link styling (opacity + width scaled by sqrt)
  - Click handlers dispatch to `onNodeClick` / `onLinkClick` via refs
  - ResizeObserver + window resize handling
- **Issues:**
  - Line 60-61: Empty `useEffect` dependency array `[]` for initialization — correct but means chart init only happens once. Data updates in separate `useEffect`.
  - Lines 112-123: Separate `useEffect` for resize on `width`/`height` changes uses `setTimeout(100ms)` — could use requestAnimationFrame instead.
  - Line 305: Very long dependency array for the data update effect — 12 dependencies. Works but makes the component hard to reason about.

#### `frontend/src/components/charts/MultiSankeyView.tsx` (318 lines)
- **Purpose:** Renders 6 Sankey charts (one per layer window) + 1 output category chart from the last window. Handles data loading for all windows.
- **Key logic:**
  - On mount/change: loads route data for all 6 windows in parallel
  - Filters output nodes into separate 7th chart
  - Click handlers enrich data with population/coverage/window metadata
  - Supports both expert and cluster modes
  - Manual trigger mode (deferred loading until Run button clicked)
- **Issues:**
  - **Line 318:** `import { convertFilterState } from '../../utils/filterState'` is at the END of the file, after the component export. This is a non-standard import placement. Should be at top. TypeScript/Vite handles it fine but it violates conventions.
  - Line 92-93: `convertFilterState` is used but the function is imported at line 318 (see above).
  - Line 100: When `mode === 'cluster'`, `clusteringConfig` must be defined. The `&&` check is correct but the type system doesn't enforce it.

#### `frontend/src/components/charts/SteppedTrajectoryPlot.tsx` (536 lines)
- **Purpose:** 3D scatter + line plot showing probe trajectories across layers using echarts-gl.
- **Key features:**
  - On-demand dimensionality reduction via `apiClient.reduce()`
  - Stratified sampling (equal per label class)
  - Cross-product grouping by color axis x shape axis
  - Layer axis lines and transparent separation planes
  - Interactive controls: spacing, scale, point size, line toggle, dim selectors
  - Click handler for trajectory points
- **Issues:**
  - Line 96: `useEffect` has `[sessionIds, layers, maxTrajectories, manualTrigger, source, method, nComponents]` — `sessionIds` is an array. If the parent passes a new array reference on each render (common), this will reload unnecessarily. MUDApp uses `useMemo` for `selectedSessions` which helps, but ExperimentPage doesn't.
  - Line 109: Chart disposal + re-creation on EVERY prop change (long dependency array). This causes visible flicker. Could use `setOption` to update incrementally instead.
  - Lines 145-149: Fisher-Yates shuffle for stratified sampling — uses `Math.random()`, not seeded. Different trajectories appear on each render. Per CLAUDE.md, outputs should be deterministic (seed=1 default). This is a potential reproducibility issue for screenshots/demos.
  - Lines 31-32: Props `colorLabelA` and `colorLabelB` are used for the chart title but not for coloring (which uses `primaryValues`). The props could be simplified.

### 2.12 Components — Analysis

#### `frontend/src/components/analysis/ExpertRoutesSection.tsx` (112 lines)
- **Purpose:** Wraps MultiSankeyView in expert mode with a Run button.
- **Issues:**
  - Line 63: `handleSankeyClick` maps 'expert' elementType to 'expert' card type, but 'route' maps to 'highway'. This is the bridge between the two naming conventions (Sankey link = "highway" in the card type system).
  - Line 107: `useCallback` is called inside JSX as a prop value. This works in React 19 but is unconventional. Should be defined outside JSX.

#### `frontend/src/components/analysis/ClusterRoutesSection.tsx` (224 lines)
- **Purpose:** Wraps MultiSankeyView (cluster mode) + SteppedTrajectoryPlot with a combined Run button.
- **Key logic:**
  - Memoizes layer array and clustering config to prevent infinite re-renders
  - Combined Run button triggers both Sankey and trajectory analysis
- **Issues:**
  - Line 90: `handleVisualizationClick` maps 'cluster' to 'cluster' and 'trajectory' to 'route' card types.
  - Line 201: `useCallback` defined inline in JSX prop — same issue as ExpertRoutesSection.
  - Lines 139: Run button disabled when BOTH `runAnalysis` and `runTrajectoryAnalysis` are null. Should probably be disabled when EITHER is null (user might want to run just one).

#### `frontend/src/components/analysis/TemporalAnalysisSection.tsx` (527 lines)
- **Purpose:** Complete temporal analysis UI: basin selection, run management, ECharts lag chart, scrubber, metrics.
- **Key features:**
  - Basin selection dropdowns (layer, basin A, basin B)
  - Instruction text generation for Claude Code (copy-paste command)
  - Run list grouped by condition with checkboxes
  - ECharts line chart with individual runs (dim), highlighted run, aggregate (mean) lines
  - Scrubber with sentence text display
  - Lag metrics with per-group mean/std and delta-persistence
- **Issues:**
  - Line 229: `return () => {}` — empty cleanup function in chart update effect. Harmless but unnecessary.
  - Line 446-447: Chart div has `minWidth: 1400` hardcoded. This prevents the chart from fitting in narrow containers. Could be responsive.
  - Lines 377-379: Checkbox `ref` callback uses `el.indeterminate` — correct pattern for indeterminate state in React.

#### `frontend/src/components/analysis/WindowAnalysis.tsx` (247 lines)
- **Purpose:** Contingency table (cluster → generated output) with chi-square test, Cramer's V, cell coloring by standardized residuals.
- **Key features:**
  - Computes contingency table from output nodes/links
  - Chi-square test of independence using jStat
  - Cramer's V effect size with verbal labels (negligible/small/moderate/strong)
  - Cell coloring: blue (more than expected) / red (fewer)
  - AI analysis report rendering (ReactMarkdown)
- **Issues:**
  - Line 1: `// @ts-ignore` on jStat import. The jStat package doesn't have TypeScript types. Consider `@types/jstat` or a local declaration.
  - Line 88: `jStat.chisquare.cdf` — relies on jStat's chi-square distribution. Correct usage.
  - Line 189-194: Cell background color uses absolute deviation from uniform expected (1/N). This is a simplification — proper coloring should use the standardized residuals computed on line 78, which are already computed but stored in `cellResiduals` and never used for display. **BUG/INCONSISTENCY:** The standardized residuals are computed (line 72-81) but the cell coloring (lines 189-194) uses a naive deviation calculation instead.

#### `frontend/src/components/analysis/ContextSensitiveCard.tsx` (341 lines)
- **Purpose:** Detail card for clicked Sankey nodes/links. Shows metrics, distributions (stacked bars), cluster path, AI description, and probe examples.
- **Key features:**
  - Adapts title and layout to card type (expert/highway/cluster/route)
  - Stacked horizontal bar for label distribution
  - Per-axis category distribution bars
  - Cluster path display (for route cards with probe_assignments)
  - AI description (ReactMarkdown)
  - Example sentences with target word highlighting and generated text
  - Output node examples shuffled (Fisher-Yates)
- **Issues:**
  - Line 9: `selectedData: any` — no type safety on the main data prop. The `SelectedCard` union type should carry enough info, but runtime enrichment (`_fullData`, `_totalProbes`, etc.) makes typing difficult.
  - Line 66: isOutputNode check uses both `selectedData.name` and `selectedData.id` — defensive but suggests inconsistency in how output nodes are identified.
  - Line 68-75: Shuffle uses `Math.random()` (not seeded). Same reproducibility concern as trajectory plot.

### 2.13 Components — Display

#### `frontend/src/components/FilteredWordDisplay.tsx` (100 lines)
- **Purpose:** Displays probe sentences with label badges and target word highlighting.
- **Issues:**
  - None significant. Clean component.

#### `frontend/src/components/SentenceHighlight.tsx` (35 lines)
- **Purpose:** Highlights target word in a sentence using regex word boundary matching.
- **Issues:**
  - Line 1: `import React from 'react'` — unused import. React 17+ with JSX transform doesn't need this.

#### `frontend/src/components/WordFilterPanel.tsx` (166 lines)
- **Purpose:** Full filter panel with label checkboxes, select/clear all, filter summary.
- **Issues:**
  - This is the ExperimentPage-style filter panel (full card with checkboxes). MUDApp uses the Toolbar's compact pill-based filter instead. This component is only imported by ExperimentPage (which is dead).
  - **BUT** the `FilterState` type is exported from here and imported by many files. The type is fine; the component is dead.
  - Line 21: `availableRegimeLabels` prop is declared but never used in the component body.

#### `frontend/src/components/Modal.tsx` (51 lines)
- **Purpose:** Generic modal overlay with backdrop click and Escape key handling.
- **Issues:**
  - **DEAD CODE.** Never imported anywhere.

#### `frontend/src/components/ActionCard.tsx` (88 lines)
- **Purpose:** Card with icon, description, and action button. Supports loading/disabled states.
- **Issues:**
  - **DEAD CODE.** Never imported anywhere.

#### `frontend/src/components/icons/Icons.tsx` (109 lines)
- **Purpose:** SVG icon components (Flask, ChartBar, Clock, ChartPie, Sparkles).
- **Issues:**
  - `FlaskIcon` and `ChartBarIcon` are imported only by WorkspacePage (dead page).
  - `FlaskIcon` is also imported by ExperimentPage (dead page).
  - `ClockIcon`, `ChartPieIcon`, `SparklesIcon` are **never imported anywhere** — dead code.

### 2.14 Vite Environment

#### `frontend/src/vite-env.d.ts` (1 line)
- Vite type reference. Standard. No issues.

---

## 3. Data Layer Review

### 3.1 Sentence Sets

#### `data/sentence_sets/GUIDE.md` (279 lines)
- **Purpose:** Comprehensive guide for Claude Code when creating/validating sentence sets.
- **Coverage:** JSON schema, quality rules, validation checklist, axes tables, output axes tables, factorial design explanation, confound analysis, workflow instructions.
- **Quality:** Excellent. Thorough, well-structured, up-to-date with current axes and output axes.
- **Issues:**
  - Line 104: Curl command for capturing probes — uses direct curl. Per memory `feedback_use_skills.md`, should reference `/probe` skill instead. Minor.
  - The `suicide_letter_framing_v1.json` file is listed in the GUIDE (line 155 area) but the file exists in `role_framing/` directory — this is fine, it's just referenced.

#### Sentence Set JSON Files (13 files across 3 categories)
- **polysemy/**: tank_polysemy_v2.json, tank_polysemy_v3.json
- **safety/**: gun_safety_v2.json, hammer_safety_v2.json, knife_safety_v2.json, rope_safety_v2.json, said_safety_v1.json
- **role_framing/**: attacked_framing_v1.json, destroyed_framing_v1.json, said_roleframing_v2.json, suicide_letter_framing_v1.json, threatened_framing_v1.json
- **Format:** Consistent across all files. All follow the schema in GUIDE.md.
- **Probe guide:** Only tank_polysemy_v3 has a `.md` probe guide alongside its JSON. Other sets rely on folder-level READMEs.

#### Category READMEs (3 files)
- **polysemy/README.md:** Describes polysemy sets, output axes. Notes tank_polysemy_v2 but not v3 in the table (v3 is newer).
- **safety/README.md:** Describes safety sets with output axes.
- **role_framing/README.md:** Describes framing sets with output axes for violence framing and said sets.
- **Issues:**
  - **polysemy/README.md line 13:** Table only lists tank_polysemy_v2 (200A + 200B). Missing v3 (5 groups, 500 sentences). The README predates v3.
  - **polysemy/README.md output axes:** Lists tone/content_type/semantic_consistency — these match v2 but v3 uses `topic` as its sole output axis. The README doesn't reflect v3's different output axes.

### 3.2 Scenario YAML Files

#### `data/worlds/scenarios/` (4 files)

**helpful_herbalist.yaml** (70 lines)
- Type: Multi-room NPC interaction
- Ground truth: friend
- Target words: ["they", "them"]
- Content: Herb garden, NPC Maren, topic-based dialogue with unlock mechanics (learn about garden → unlock poultice topic)
- Uses `sets_flag` / `requires` for gating

**suspicious_blacksmith.yaml** (69 lines)
- Type: Multi-room NPC interaction
- Ground truth: enemy
- Target words: ["they", "them"]
- Content: Smithy, NPC Rodek, suspicious behavior with locked chest, confrontation mechanics
- Uses `sets_flag` / `requires` for gating

**bus_stop_friend.yaml** (101 lines)
- Type: Probe scenario (simple)
- Ground truth: friend
- Target words: ["person"]
- scenario_type: probe
- Content: Bus stop at night, teenager in Burger King uniform, phone dead, needs help
- 6 actions: 2 approach (correct), 2 avoid (incorrect), 2 canary (incorrect)
- Has `states.initial` with `planning_prompt`

**bus_stop_foe.yaml** (98 lines)
- Type: Probe scenario (simple)
- Ground truth: enemy
- Target words: ["person"]
- scenario_type: probe
- Content: Bus stop at night, person with knife demanding valuables
- 6 actions: same structure as friend, correctness inverted (avoid = correct)

**Design observations:**
- Bus stop pair is a matched pair (same scene, same actions, different NPC characterization, inverted correctness). This is the friend/foe probe design from steeringandscenarios.md.
- Herbalist/Blacksmith pair uses topic-based dialogue with flag unlocking — more complex multi-step interaction.
- Both pairs share target words ("person" for bus stop, "they/them" for village NPCs).
- The bus stop YAML has `canary: true` on actions 5 and 6 — these are "incorrect regardless of condition" controls for detecting random behavior.

**Issues:**
- The herbalist/blacksmith scenarios reference `knows_about_greta_theft` flag but there's no Greta NPC or scenario — this flag would need to be set by a cross-scenario mechanism or a third scenario.
- The scenarios are well-formed YAML but there's no Evennia-side implementation to load them yet (Phase 2+).

---

## 4. Documentation Review

### 4.1 Core Docs

#### `docs/PIPELINE.md`
- **Purpose:** Master pipeline runbook for Claude Code.
- **Stages:** Design → Capture → Categorize → (User gate: clustering) → Analysis → Present → Temporal
- **Status:** Current. References correct API endpoints, skill names, and workflow.

#### `docs/ANALYSIS.md`
- **Purpose:** Analysis methodology reference for cluster/route data.
- **Status:** Current. Correctly notes that `/analyze` skill is the operational procedure and this doc provides reference detail.

#### `docs/PROBES.md`
- **Purpose:** How to create and run probes.
- **Status:** Current. Matches actual API endpoints and workflow.

#### `docs/SERVERS.md` (8 lines)
- **Purpose:** Redirects to `.claude/skills/server/SKILL.md`.
- **Status:** Correct redirect. Minimal.

#### `docs/architecturemud.md` (large, read first 150 lines)
- **Purpose:** Living architecture document for the MUD integration.
- **Status:** Accurately describes the current quadrant layout, data flow, component architecture, port mapping, and glossary.
- **Issues:**
  - Section 2.B says "33 files" — current count is ~40 files. Minor staleness.
  - Section 2.B says ExperimentPage is 871 lines — this is current, but ExperimentPage is now dead (not routed).
  - The doc describes Phase 1 as "reorganization into quadrant layout" which is complete. The doc should reflect that Phase 1 is done.

#### `docs/architecturescenarios.md` (read first 150 lines)
- **Purpose:** Scenario system architecture — state machine model, effects vocabulary, interaction sequence.
- **Status:** Design document. No Evennia implementation exists yet.
- **Issues:**
  - References `character.db.scenario_flags` — assumes Evennia typeclasses exist. The `evennia_world/` directory exists but its contents weren't in scope for this review.

#### `docs/steeringandscenarios.md` (read first 100 lines)
- **Purpose:** Research design for steering vectors and scenario-based probes.
- **Status:** Design document (April 2026 report). Future work.
- **No issues.** Well-structured research plan.

### 4.2 Research Docs (under docs/research/)
- `concept_mri_implementation_v1_3.md` — Implementation spec
- `firstexperiment.md` — First experiment notes
- `attractor_architecture.md` — Attractor basin theory
- `attractorpaper.md` — Paper draft/notes

### 4.3 Other Docs
- `docs/temporal_and_output_requirements.md` — Requirements for temporal analysis and output categories
- `docs/MULTI_MODEL_DESIGN.md` — Future multi-model support design
- `docs/ARCHITECTURE_REVIEW.md` — Previous architecture review
- `docs/SCAFFOLDING_IDEAS.md` — Cognitive scaffolding research ideas
- `docs/claude_scaffolding_ideas/honest_review_prompt_techniques.md` — Review methodology

### 4.4 Scratchpad (docs/scratchpad/)
7 research and planning files. These are intermediate work products from recent sessions:
- research_cdd_review_frameworks.md
- research_claude_code_practices.md
- research_doc_sync.md
- research_skill_design.md
- research_synthesis.md
- research_vision_stories.md
- scaffolding_improvement_plan.md

---

## 5. Skills Review

### 5.1 Pipeline Skills (6 skills)

| Skill | Purpose | Status |
|-------|---------|--------|
| `/server` | Start/stop/check backend, frontend, Evennia | Complete. OP-1 through OP-6 with WSL2-specific procedures. |
| `/probe` | Co-design new experiment | Complete. 7-step interactive workflow. |
| `/categorize` | Classify generated outputs | Complete. 5-step batch classification workflow. |
| `/analyze` | Read cluster data, write reports | Complete. Window-by-window analysis with probe guide integration. |
| `/temporal` | Run temporal basin captures | Complete. Covers single runs, paired batches, sentence pairing. |
| `/pipeline` | Check pipeline state | Complete. 4-step state detection. |

### 5.2 Decision Skills (3 skills)

| Skill | Purpose |
|-------|---------|
| `/cdd` | Certainty-Driven Development assessment |
| `/devils-advocate` | Challenge a design |
| `/competitive-design` | Generate alternative approaches |

### 5.3 Review Skills (10 skills)

| Skill | Purpose |
|-------|---------|
| `/review-onboarding` | Newcomer comprehension check |
| `/review-deliverability` | Phase independence check |
| `/review-risks` | Failure mode analysis |
| `/review-scope` | Complexity justification |
| `/review-consistency` | Cross-document agreement |
| `/review-evolution` | Lock-in vs flexibility |
| `/review-trace` | End-to-end scenario walk |
| `/review-interfaces` | Component boundary check |
| `/review-drift` | Implementation vs design |
| `/review-best-practices` | Engineering quality |
| `/thorough-review` | Fan-out all reviews via agents |

### 5.4 Skill Issues

- **`/temporal` SKILL.md line 17:** Hardcodes Python path to `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python`. This breaks on other machines. Should use `$ROOT/.venv/bin/python` like `/server`.
- **`/temporal` SKILL.md line 18:** Hardcodes lake path to `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/data/lake`. Same portability issue.

---

## 6. Project Config Review

### 6.1 Root package.json
```json
{
  "dependencies": {
    "@xterm/xterm": "^6.0.0"
  }
}
```
- **Issues:**
  - **DUPLICATE DEPENDENCY.** `@xterm/xterm` is listed in both root `package.json` AND `frontend/package.json`. The root package.json appears to be an artifact — there's no root-level app. This should be removed.
  - Root `package-lock.json` also exists (per git status) — corresponds to this unnecessary root package.json.

### 6.2 frontend/package.json
- **Dependencies:**
  - `plotly.js` (^3.1.0) and `react-plotly.js` (^2.6.0) — **NEVER IMPORTED.** These are dead dependencies. Plotly was likely used before ECharts was adopted. ~3MB of dead weight.
  - `jStat` (^1.8.6) — Used in WindowAnalysis.tsx for chi-square. Correctly listed.
  - `echarts-gl` (^2.0.9) — Used in SteppedTrajectoryPlot.tsx. Correctly listed.

### 6.3 frontend/vite.config.ts
- WSL2 polling enabled (`usePolling: true, interval: 500`) — matches memory `feedback_vite_hmr_wsl2.md`.
- `strictPort: true` — good, prevents silent port reassignment.
- Uses `@tailwindcss/vite` plugin — Tailwind 4 approach.

### 6.4 frontend/tsconfig.app.json
- Strict mode enabled, including `noUnusedLocals` and `noUnusedParameters`.
- **Issue:** With these strict settings, the dead imports (React in SentenceHighlight, etc.) should cause build errors. Either the build isn't run regularly or `verbatimModuleSyntax` handles it differently. Need to verify.

### 6.5 frontend/tailwind.config.js
- Standard Tailwind config. Content paths cover `./index.html` and `./src/**/*.{js,ts,jsx,tsx}`.
- **Issue:** This is a Tailwind 3 config file format (`/** @type {import('tailwindcss').Config} */`). But `package.json` has Tailwind 4 (`^4.1.13`) with `@tailwindcss/vite` and `@tailwindcss/postcss`. Tailwind 4 uses a different configuration approach (CSS-first config via `@theme`). This config file may be ignored by Tailwind 4's Vite plugin. The presence of both a v3-style config AND v4 Vite plugin is confusing.

### 6.6 .env.example
- Documents all environment variables.
- **Issue:** Includes `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` for LLM insights. Per CLAUDE.md and memory `project_claude_as_runtime.md`, Claude Code IS the runtime — no separate LLM API keys needed. These env vars and the `LLMInsightsService` on the backend may be vestigial.
- Also includes `LLM_PROVIDER=openai` and `LLM_MODEL=gpt-4` — same concern.

---

## 7. Cross-Cutting Concerns

### 7.1 How Frontend Connects to Both FastAPI and Evennia

**FastAPI (REST, port 8000):**
- All data operations go through `apiClient` singleton
- Session CRUD, route analysis, cluster analysis, temporal capture, clustering schemas
- Request/response JSON, 60s default timeout
- No authentication

**Evennia (WebSocket, port 4002):**
- `useEvennia` hook manages WebSocket lifecycle
- Sends `client_options` with `raw: true` on connect (ANSI mode, not HTML)
- Messages parsed as `[cmdname, args, kwargs]` JSON
- Text/prompt → terminal display via xterm.js
- OOB events → `handleOOB` in MUDApp → state changes
- Only `sendCommand` used in practice (typed commands in input box)

**Key separation:** Evennia manages MUD state (rooms, NPCs, navigation). React manages viz state (axes, gradients, clustering). The two communicate through OOB events only. Evennia never calls FastAPI directly.

### 7.2 MUD Terminal Component

The terminal uses xterm.js (v6) in output-only mode with a separate HTML input. This design separates output rendering (ANSI in terminal) from input (HTML form), which is simpler than full terminal emulation.

**Text flow:**
1. Evennia sends `["text", ["some text"], {}]`
2. `useEvennia` parses → `onText("some text")`
3. `MUDTerminal.handleText` → `evenniaToAnsi(text)` → converts Evennia markup to ANSI
4. `writeToTerminal` → normalizes `\n` to `\r\n` → `terminal.write()`

**Command flow:**
1. User types in `<input>`, submits form
2. `sendCommand(inputValue)` → WebSocket sends `["text", [inputValue], {}]`
3. Input cleared

### 7.3 OOB Message Handling

**`room_entered` event:**
1. Evennia sends `["room_entered", [{session_id, room_type, role, viz_preset}], {}]`
2. `handleOOB` in MUDApp extracts payload
3. Sets `roomContext` (role + roomType)
4. If `session_id` present: calls `resetForNewSession(session_id)` → loads session → applies viz preset
5. Generation counter (`navigationGenRef`) prevents stale preset application during rapid navigation

**`room_left` event:**
1. Evennia sends `["room_left", [...], {}]`
2. `handleOOB` sets `roomContext` to null
3. Controls re-enable (no longer in visitor mode)

### 7.4 Toolbar and Visualization Components

The toolbar is the primary control surface. It provides:
- Session selection (dropdown)
- Color axis, gradient, blend axis, shape axis selection
- Output color controls (conditional — only shown when output axes exist)
- Expert route controls (top N / show all)
- Clustering config (schema dropdown or inline params)
- Claude instruction text (clickable copy)
- Label filter pills

Controls flow directly to hook state setters. No intermediate state management layer. This is appropriate for the current single-user tool.

### 7.5 Doc/Implementation Sync

| Doc | Implementation Status |
|-----|----------------------|
| architecturemud.md quadrant layout | Matches MUDApp.tsx exactly |
| architecturemud.md data flow | Matches — toolbar controls and OOB events both set React state |
| architecturemud.md port table | Matches vite.config.ts (5173), server skill (8000), useEvennia (4002) |
| architecturemud.md Phase 1 | Complete — quadrant layout, terminal, toolbar all implemented |
| architecturescenarios.md | Design only — no Evennia implementation yet. Matches YAML format. |
| PIPELINE.md stages | Matches skill implementations and API client methods |
| PROBES.md | Matches API endpoints in client.ts |
| GUIDE.md sentence schema | Matches actual JSON files |

**Drift detected:**
- architecturemud.md Section 2.B: "33 files" → actually ~40 now
- architecturemud.md Section 2.B: Lists ExperimentPage as active, but it's now dead (replaced by MUDApp)
- polysemy/README.md: Missing tank_polysemy_v3 entry

### 7.6 Data File Formats and Conventions

**Sentence Set JSON format:**
```
{name, version, target_word, groups: [{label, description, sentences: [{text, group, target_word, categories}]}], axes, output_axes, generate_output, metadata}
```
All 13 JSON files follow this format consistently. The `group` field on each sentence matches the parent group's `label`. The `categories` dict keys match the file's `axes` array IDs.

**Scenario YAML format:**
```
{name, ground_truth, target_words, scenario_type?, rooms: [{name, description, ambient, objects, npcs}], npcs: [{name, room, examine, initial_topics, unlockable_topics}], states?}
```
The bus stop scenarios use a flat `states` structure inside rooms. The village scenarios use NPC topic trees with flag-gating. Both formats are documented in architecturescenarios.md.

---

## 8. Issues Summary

### 8.A Critical Issues

None. The active code paths (MUDApp, terminal, toolbar, viz components) are functional and well-integrated.

### 8.B Design Issues

1. **Massive dead code from ExperimentPage migration.** ExperimentPage (871 lines), WorkspacePage (186 lines), Modal (51 lines), ActionCard (88 lines), workspace.ts (2 lines), Icons (3 of 5 icons), App.css (43 lines), theme.css (9 lines) are all unreachable. Total: ~1250 lines of dead code.

2. **ExperimentPage/MUDApp duplication.** Before ExperimentPage was deactivated, its logic was copied into MUDApp. Now both exist with nearly identical state management, data loading, and rendering logic. The dead ExperimentPage should be removed entirely, not left to rot.

3. **WordFilterPanel component is only used by dead ExperimentPage.** Its `FilterState` type export is used everywhere, but the component itself is dead. The type should be extracted to its own file.

### 8.C Code Quality Issues

4. **`serverBusy` in MUDApp (line 34):** Declared and set but never read. ExperimentPage correctly uses it for a banner — MUDApp should either use it or remove it.

5. **MultiSankeyView import at end of file (line 318):** `import { convertFilterState }` placed after the component export. Should be at top.

6. **WindowAnalysis standardized residuals computed but not used (lines 72-81 vs 189-194):** `cellResiduals` is computed with proper standardized residuals but the cell coloring uses a naive deviation calculation instead.

7. **SentenceHighlight unused React import (line 1):** `import React from 'react'` is unnecessary with React 17+ JSX transform.

8. **SteppedTrajectoryPlot non-deterministic sampling:** Fisher-Yates shuffle uses `Math.random()`. Reproducibility concern per CLAUDE.md seed=1 default.

9. **useCallback inside JSX (ExpertRoutesSection line 107, ClusterRoutesSection line 201):** Unconventional pattern. Works but makes the component harder to read.

### 8.D Dependency Issues

10. **Dead npm dependencies:** `plotly.js` and `react-plotly.js` are installed but never imported. ~3MB dead weight.

11. **Duplicate root package.json:** Root-level `package.json` with `@xterm/xterm` dependency. Should be removed — xterm is in frontend/package.json.

12. **Tailwind 3/4 config confusion:** `tailwind.config.js` is Tailwind 3 format, but package.json has Tailwind 4 with `@tailwindcss/vite` plugin. The config file may be ignored.

### 8.E Documentation Drift

13. **architecturemud.md:** File count stale (33 → ~40). ExperimentPage listed as active but it's dead.

14. **polysemy/README.md:** Missing tank_polysemy_v3 entry and its different output axes.

### 8.F Portability Issues

15. **`/temporal` skill hardcodes absolute paths** to `.venv/bin/python` and `data/lake`. Should use `$ROOT` variable like `/server` skill.

### 8.G Minor Issues

16. **Toolbar variable shadowing (line 335):** `const s = availableSchemas.find(s => ...)` — `s` shadows outer parameter.

17. **API types use `any` extensively:** `[key: string]: any`, `Record<string, any>`, `params: any` in schema management. Reduces type safety.

18. **useEvennia `sendOOB` never used:** Exported but no consumer calls it.

19. **MUD terminal lacks command history:** No up/down arrow for previous commands. Standard expectation for MUD terminals.

20. **TemporalAnalysisSection chart minWidth: 1400px hardcoded:** Prevents responsive behavior.

21. **`.env.example` includes LLM API keys:** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL` — vestigial from pre-Claude-as-runtime architecture.

---

## Appendix: File Dependency Graph

### Who imports whom (active code only)

```
main.tsx → App.tsx → MUDApp.tsx
  MUDApp.tsx →
    hooks/useAxisControls.ts
    hooks/useClusteringConfig.ts
    hooks/useSchemaManagement.ts → api/client.ts
    components/toolbar/Toolbar.tsx → utils/colorBlending.ts, constants/layerRanges.ts
    components/analysis/ExpertRoutesSection.tsx → charts/MultiSankeyView.tsx
    components/analysis/ClusterRoutesSection.tsx → charts/MultiSankeyView.tsx, charts/SteppedTrajectoryPlot.tsx
    components/analysis/TemporalAnalysisSection.tsx → hooks/useTemporalAnalysis.ts
    components/analysis/WindowAnalysis.tsx (uses jStat, react-markdown)
    components/analysis/ContextSensitiveCard.tsx (uses react-markdown)
    components/FilteredWordDisplay.tsx → components/SentenceHighlight.tsx
    components/terminal/MUDTerminal.tsx → hooks/useEvennia.ts, utils/evenniaAnsi.ts

  charts/MultiSankeyView.tsx → charts/SankeyChart.tsx, api/client.ts, utils/filterState.ts
  charts/SankeyChart.tsx → utils/colorBlending.ts, constants/outputNodes.ts
  charts/SteppedTrajectoryPlot.tsx → api/client.ts, utils/colorBlending.ts

  types/api.ts (imported by most files)
  types/analysis.ts (imported by MUDApp, section components)
  types/temporal.ts (imported by useTemporalAnalysis)
  types/evennia.ts (imported by MUDApp, Toolbar)
```

### Dead files (not in any active import chain)

```
pages/WorkspacePage.tsx
pages/ExperimentPage.tsx
components/Modal.tsx
components/ActionCard.tsx
components/WordFilterPanel.tsx (component, not the FilterState type)
components/icons/Icons.tsx (ClockIcon, ChartPieIcon, SparklesIcon)
constants/workspace.ts
App.css (most styles)
theme.css (entire file)
```
