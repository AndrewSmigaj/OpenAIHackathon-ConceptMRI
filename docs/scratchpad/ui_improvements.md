# UI Improvements — Iteration Document

## Overview

Three targeted improvements to the experiment page. Each is independent.

---

## 1. Tick/Turn Filter for Trajectories

**Problem:** Agent sessions produce ~12 ticks per scenario following nearly identical routes. This adds visual noise.

**Current state:**
- `tokens.parquet` has `turn_id` (0, 1, 2, ...)
- `ReductionPoint` schema does NOT include `turn_id`
- Frontend `Trajectory` interface has no `turn_id`
- No tick filtering UI exists

**Proposed approach:**

Backend:
- Add `turn_id` to `ReductionPoint` (`schemas.py:55`)
- Extract it in `reduction_service.py:85-90`
- Add `turn_ids` filter param to the reduce request

Frontend:
- Add `turn_id` to Trajectory interface (`SteppedTrajectoryPlot.tsx:9`)
- Add tick selector UI in `ClusterRoutesSection.tsx` (multi-select chips)
- Filter trajectories by selected ticks before rendering

**Open questions:**
- Should clustering also filter by tick? Or just the trajectory viz?
- Better UX: chips, checkboxes, or a range slider?

---

## 2. Top Bar Controls Reorganization

**Problem:** Controls cramped in 220px sidebar. Source label buried. Color and clustering controls mixed.

**Current state:**
- All controls stacked vertically in sidebar (`ExperimentPage.tsx:463-684`)
- `AxisControls` is an inline function (lines 39-135)
- Clustering controls at lines 579-684
- Separated by thin border-t dividers

**Proposed layout:** Horizontal top bar, two panels:

```
┌─────────────────────────────┬──────────────────────────────┐
│ ANALYSIS                    │ APPEARANCE                   │
│ Source: [residual stream ▾] │ Color: [label ▾] [red-blue▾] │
│ Reduction: [PCA▾] [6]D     │ Blend: [none ▾]              │
│ Clustering: [hierarchical▾] │ Shape: [none ▾]              │
│ K: [6] Schema: [select ▾]  │ [color preview swatches]     │
└─────────────────────────────┴──────────────────────────────┘
```

- Left panel: Source, Reduction, Clustering, K, Schema
- Right panel: Color axis, Gradient, Blend, Shape, Preview
- Top bar: auto height, `border-b bg-white shadow-sm`
- Source label: clear, readable, not tiny

**Open questions:**
- Keep sidebar for session list only, or remove sidebar entirely?
- Expert routes checkbox — left panel or its own section?

---

## 3. Detail Panel — Agent Reasoning & Action

**Problem:** Clicking a trajectory point shows raw input_text (full prompt). Agent reasoning and action not surfaced clearly.

**Current state:**
- `ContextSensitiveCard.tsx:288-317` renders input_text + generated_text
- Agent `input_text` contains full conversation (system prompt + game text + analysis + action)
- No parsing of analysis/action into distinct sections
- Right panel: 384px wide (`w-96`)

**Proposed design:**

```
┌────────────────────────────────┐
│ [friend] bus_stop_foo_friend   │
│                                │
│ "You are standing at a bus..." │
│ (game text with highlighted    │
│  target word)                  │
│                                │
│ ── Internal Reasoning ──────── │
│ "We must examine the person    │
│  first because..."             │
│ (teal/green background)        │
│                                │
│ ► Action: examine person       │
│ (amber, bold, own line)        │
└────────────────────────────────┘
```

Implementation:
- Detect agent data via `turn_id !== undefined` or `capture_type`
- Parse `input_text` to extract game text, analysis channel, final channel
- Render three sections: game text, "Internal Reasoning" (teal bg), action (amber)
- Reduce right panel from `w-96` (384px) to `w-80` (320px)

**Open questions:**
- Parse using channel markers (`analysis`, `final`) or role markers (`user`, `assistant`)?
- Should non-agent sessions render differently or stay as-is?

---

## Key Files

| File | What changes |
|------|-------------|
| `backend/src/api/schemas.py` | `ReductionPoint` + reduce request: add `turn_id` |
| `backend/src/services/features/reduction_service.py` | Extract `turn_id`, filter by it |
| `frontend/src/pages/ExperimentPage.tsx` | Top bar layout, right panel width |
| `frontend/src/components/charts/SteppedTrajectoryPlot.tsx` | Trajectory interface, tick filtering |
| `frontend/src/components/analysis/ClusterRoutesSection.tsx` | Tick selector UI |
| `frontend/src/components/analysis/ContextSensitiveCard.tsx` | Agent data parsing + rendering |

---

## Iteration Log

*(Notes from design discussion go here)*
