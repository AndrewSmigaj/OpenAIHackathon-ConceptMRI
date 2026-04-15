# UI Improvements — Iteration Document

## Overview

Three targeted improvements to the experiment page. Each is independent except that Task 3A (ProbeExample.step) must land before Task 1's step selector.

---

## 1. Sequence Step Filter for Trajectories

**Problem:** Multi-step sessions produce overlapping trajectories. Agent sessions have ~12 ticks per scenario, temporal captures have up to 40 expanding-context steps. No way to filter by step.

**Design:** Unified `step` field on both `ReductionPoint` and `ProbeExample`, populated from `turn_id` (agents) or `sentence_index` (temporal). Filter works for all session types. Basic sentence sets (1 step) hide the selector.

**Backend:**
- `ReductionPoint` gets `step: Optional[int] = None`
- `reduction_service.py` extracts: `turn_id if turn_id is not None else sentence_index`
- `ProbeExample` gets `step` (via Task 3A)

**Frontend:**
- `Trajectory` interface gets `step?: number`
- `SteppedTrajectoryPlot` gets `selectedSteps` prop for filtering
- `ClusterRoutesSection` gets step selector chips between Sankey and trajectory plot

---

## 2. Top Bar Controls Reorganization

**Problem:** Controls cramped in 220px sidebar. Source label buried. Color and clustering controls mixed.

**Design:** Horizontal top bar above content with two panels (Analysis | Appearance). Sidebar keeps session selector + word filter panel (absorbed from middle column). Middle `word-panel-narrow` column eliminated.

**Layout:**
```
+------------------------------------------------------------------+
| ANALYSIS                         | APPEARANCE                    |
| Source: [residual stream v]      | Color: [label v] [red-blue v] |
| Reduction: [PCA v] [6]D         | Blend: [none v]               |
| Clustering: [hierarchical v]    | Shape: [none v]               |
| K: [6]  Schema: [select v]      | [color preview swatches]      |
| Show all routes  Top: [10]      | Output color (if exists)      |
+------------------------------------------------------------------+
```

---

## 3. Detail Panel — Agent Reasoning & Action

**Problem:** Clicking a trajectory point shows raw input_text (full decoded chat template blob). Agent reasoning and action not surfaced.

**Design:** Enrich `ProbeExample` with `game_text`, `analysis`, `action` from `tick_log.jsonl` at query time. Detect agent data via `game_text !== undefined` (not `turn_id`, since temporal captures also have steps).

**Card layout:**
```
+--------------------------------+
| [friend] Step 2                |
|                                |
| "You are standing at a bus..." |
| (game_text with SentenceHigh)  |
|                                |
| -- Internal Reasoning -------- |
| "We must examine the person    |
|  first because..."             |
| (teal-50 bg, text-sm)          |
|                                |
| > Action: examine person       |
| (amber-600, font-bold)         |
+--------------------------------+
```

**Right panel width:** DEFERRED at 384px (`w-96`). Shrinking would penalize other card types.

---

## Key Files

| File | What changes |
|------|-------------|
| `backend/src/api/schemas.py` | `ReductionPoint.step`, `ProbeExample.step/game_text/analysis/action` |
| `backend/src/services/features/reduction_service.py` | Extract unified `step` into token_meta |
| `backend/src/api/routers/probes.py` | ProbeExample construction: add step + tick_log enrichment |
| `backend/src/services/probes/tick_log_enrichment.py` | NEW: load tick_log.jsonl → lookup dict |
| `frontend/src/types/api.ts` | `ReductionPoint.step`, `ProbeExample.step/game_text/analysis/action` |
| `frontend/src/pages/ExperimentPage.tsx` | Top bar layout, word panel absorbed into sidebar |
| `frontend/src/index.css` | Remove `word-panel-narrow` class |
| `frontend/src/components/charts/SteppedTrajectoryPlot.tsx` | `Trajectory.step`, `selectedSteps` filter |
| `frontend/src/components/analysis/ClusterRoutesSection.tsx` | Step selector chips |
| `frontend/src/components/analysis/ContextSensitiveCard.tsx` | Agent data rendering |

---

## Iteration Log

- 2026-04-12: Initial design with `turn_id` on ReductionPoint
- 2026-04-12: Unified to `step` field after design review (works for agents, temporal, future multi-step)
- 2026-04-12: Fixed Python `0 or None` truthiness bug in extraction code
- 2026-04-12: Deferred right panel width change (384px stays)
- 2026-04-12: Absorbed word filter panel into sidebar instead of leaving sidebar empty
- 2026-04-12: Agent detection changed from `turn_id !== undefined` to `game_text !== undefined`
- 2026-04-12: 7 review skills completed, certainty assessment done, plan approved
