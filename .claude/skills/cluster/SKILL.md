---
name: cluster
description: Build, list, archive, and delete clustering schemas — the canonical schema lifecycle owner for sessions
---

# Clustering Schema Lifecycle

A clustering schema is an **immutable artifact on disk** containing both cluster
routes and expert routes for a session. Filters (`steps`, `last_occurrence_only`,
`max_probes`), the UMAP/HDBSCAN params, and the window list are baked in at
compute time and recorded in `meta.json`. Schemas live at:

```
$ROOT/data/lake/<session_id>/clusterings/<schema_name>/
├── meta.json
├── cluster_windows/
│   ├── w_<a>_<b>.json                    # default output-axis variant
│   └── w_<a>_<b>__out_<axis>.json        # pre-computed output variants
├── expert_windows/
│   ├── w_<a>_<b>__rank{1,2,3}.json       # all three ranks
│   └── w_<a>_<b>__rank{1,2,3}__out_*.json
├── centroids.json
├── probe_assignments.json
├── trajectory_points.json                # 3D UMAP for the trajectory plot
├── reports/                               # markdown reports (Claude-authored)
├── element_descriptions.json              # cluster/route labels
└── _archive/<schema>_<ts>/                # archived schemas
```

**Schemas are immutable.** Re-computing against an existing `save_as` with
different filter/clustering params returns 409. The legal evolutions are:

- Extend with new windows (same params, new `window_layers`) — see OP-1B
- Archive and start over with a new name — see OP-4

The frontend has zero schema-management UI. Everything is curl from this skill.

## Prerequisites

1. `/server` OP-1 to confirm the backend is up and the model is loaded.
2. The session's probe captures must already be on disk (`tokens.parquet`,
   `residual_stream/*.parquet`).

## Constants

| Constant | Value |
|----------|-------|
| Backend URL | `http://localhost:8000` |
| Cluster compute/load endpoint | `POST /api/experiments/analyze-cluster-routes` |
| Expert compute/load endpoint | `POST /api/experiments/analyze-routes` |
| List schemas | `GET /api/probes/sessions/{sid}/clusterings` |
| Load schema | `GET /api/probes/sessions/{sid}/clusterings/{name}` |
| Trajectory points | `GET /api/probes/sessions/{sid}/clusterings/{name}/trajectory` |
| Archive schema | `POST /api/probes/sessions/{sid}/clusterings/{name}/archive` |
| Delete schema | `DELETE /api/probes/sessions/{sid}/clusterings/{name}[?force=true]` |
| Schema dir | `$ROOT/data/lake/<sid>/clusterings/<name>/` |

All commands resolve `$ROOT` and `$PY` at the top:

```bash
ROOT=$(git rev-parse --show-toplevel)
PY="$ROOT/.venv/bin/python"
```

## Default clustering config (single source of truth)

```yaml
session_kind:
  agent:             { step: 1 }            # post-examine tick
  sentence:          { step: 0 }            # only tick for single-sentence probes
  sentence_two_part: { step: [0, 1] }       # both ticks; user may override

clustering_config:
  source: residual_stream
  reduction:
    method: umap
    n_components: 6
    n_neighbors: 15
    min_dist: 0.1
    metric: euclidean
  clustering:
    method: hierarchical
    k: 6

filter_defaults:
  last_occurrence_only: true
  max_probes: null

window_default: [22, 23]   # caller picks; this is the "paper window"

schema_name_convention:
  # User's preferred concise pattern (per existing bus_stop_friend_foe_k6_n15):
  #   <study-and-axes>_k<k>_n<n>[_<sweep-suffix>]
  # OP-1 requires explicit save_as. OP-2 sweeps append a short suffix per axis:
  #   max_probes  → _max<N>     (e.g. _max25)
  #   steps       → _step<vals> (e.g. _step01)
  #   n_components→ _d<N>       (e.g. _d3)
  #   n_neighbors → _n<N>       (e.g. _n5)
  example_base: bus_stop_friend_foe
  example_full: bus_stop_friend_foe_k6_n15
```

This block is the only place to update defaults. The other skills (`/probe`,
`/agent`) call into the OPs below and pass the session-kind step default.

---

## Operations

### OP-1: Build one schema (compute cluster + expert routes)

Creates a new schema directory. Calls cluster compute first (writes
`meta.json`, `cluster_windows/`, `centroids.json`, `probe_assignments.json`,
`trajectory_points.json`, `sample_size`), then expert compute (writes all
three rank variants under `expert_windows/`, merges `expert_routes_params`
into `meta.json`).

**`save_as` is required and must NOT already exist.** If it does, the
endpoint returns 409 with a hint pointing at OP-1B (extend) or OP-4 (archive).

Replace `SESSION_ID`, `SAVE_AS`, `WINDOW_LAYERS` (e.g. `[22,23]`), and any
overrides. Defaults match the YAML block above.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SAVE_AS && WIN='[22,23]' && \
echo "=== Cluster compute ===" && curl -s -X POST http://localhost:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "mode":"compute",
    "session_id":"'"$SID"'",
    "save_as":"'"$SAVE"'",
    "window_layers":'"$WIN"',
    "clustering_config":{
      "source":"residual_stream",
      "reduction":{"method":"umap","n_components":6,"n_neighbors":15,"min_dist":0.1,"metric":"euclidean"},
      "clustering":{"method":"hierarchical","k":6}
    },
    "steps":[1],
    "last_occurrence_only":true,
    "top_n_routes":20
  }' | $PY -c "import json,sys; d=json.load(sys.stdin); print(json.dumps({'total_probes':d.get('statistics',{}).get('total_probes'), 'total_routes':d.get('statistics',{}).get('total_routes'), 'detail':d.get('detail')}, indent=2))" && \
echo "=== Expert compute (rank 1/2/3) ===" && curl -s -X POST http://localhost:8000/api/experiments/analyze-routes \
  -H "Content-Type: application/json" \
  -d '{
    "mode":"compute",
    "session_id":"'"$SID"'",
    "save_as":"'"$SAVE"'",
    "window_layers":'"$WIN"',
    "steps":[1],
    "last_occurrence_only":true,
    "top_n_routes":20
  }' | $PY -c "import json,sys; d=json.load(sys.stdin); print(json.dumps({'total_routes':d.get('statistics',{}).get('total_routes'), 'detail':d.get('detail')}, indent=2))"
```

**Verification block (run after OP-1 returns):**

```bash
ROOT=$(git rev-parse --show-toplevel) && SID=SESSION_ID && SAVE=SAVE_AS && \
echo "=== Files on disk ===" && ls -1 "$ROOT/data/lake/$SID/clusterings/$SAVE/" && \
echo "=== Cluster windows ===" && ls -1 "$ROOT/data/lake/$SID/clusterings/$SAVE/cluster_windows/" && \
echo "=== Expert windows ===" && ls -1 "$ROOT/data/lake/$SID/clusterings/$SAVE/expert_windows/" && \
echo "=== meta.json ===" && cat "$ROOT/data/lake/$SID/clusterings/$SAVE/meta.json"
```

Expected: `meta.json`, `centroids.json`, `probe_assignments.json`,
`trajectory_points.json`, `cluster_windows/w_<a>_<b>.json` (+ output
variants), `expert_windows/w_<a>_<b>__rank{1,2,3}.json` (+ output variants).
`meta.json` should contain both top-level cluster params and an
`expert_routes_params` block.

### OP-1B: Extend an existing schema with new windows

Same `save_as`, new `window_layers`. The compute endpoint validates that all
filter/clustering params match the existing `meta.json` (immutability check).
Errors with 409 if the requested window already exists, or if any param has
drifted from the original.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SAVE_AS && WIN='[20,21]' && \
echo "=== Cluster extend ===" && curl -s -X POST http://localhost:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "mode":"compute",
    "session_id":"'"$SID"'",
    "save_as":"'"$SAVE"'",
    "window_layers":'"$WIN"',
    "clustering_config":{
      "source":"residual_stream",
      "reduction":{"method":"umap","n_components":6,"n_neighbors":15,"min_dist":0.1,"metric":"euclidean"},
      "clustering":{"method":"hierarchical","k":6}
    },
    "steps":[1],
    "last_occurrence_only":true,
    "top_n_routes":20
  }' | $PY -m json.tool && \
echo "=== Expert extend ===" && curl -s -X POST http://localhost:8000/api/experiments/analyze-routes \
  -H "Content-Type: application/json" \
  -d '{
    "mode":"compute",
    "session_id":"'"$SID"'",
    "save_as":"'"$SAVE"'",
    "window_layers":'"$WIN"',
    "steps":[1],
    "last_occurrence_only":true,
    "top_n_routes":20
  }' | $PY -m json.tool
```

If params drift, the response is 409 with a `diff` field showing
existing-vs-request for each mismatched key.

### OP-2: Sweep — build a schema per cartesian-product combination

Sweep across one or more axes. Each combination becomes its own schema with a
suffixed name. **Halt-and-report on first failure** (the loop stops and
reports which schemas succeeded/failed).

Hard cap: **50 schemas** without `--force`. The sweep prints all schema names
and the size before running and asks for confirmation.

Inputs:
- `BASE_NAME` — common prefix (e.g. `bus_stop_friend_foe_k4_n15`)
- `SWEEP_AXES` — one or more axes from `{max_probes, steps, n_components, n_neighbors, k}`

Example sweep over `max_probes ∈ {25, 50, 100}`:

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && BASE=BASE_NAME && \
for N in 25 50 100; do \
  SAVE="${BASE}_max${N}" && \
  echo "=== ${SAVE} ===" && \
  curl -s -X POST http://localhost:8000/api/experiments/analyze-cluster-routes \
    -H "Content-Type: application/json" \
    -d '{
      "mode":"compute",
      "session_id":"'"$SID"'",
      "save_as":"'"$SAVE"'",
      "window_layers":[22,23],
      "clustering_config":{
        "source":"residual_stream",
        "reduction":{"method":"umap","n_components":6,"n_neighbors":15,"min_dist":0.1,"metric":"euclidean"},
        "clustering":{"method":"hierarchical","k":4}
      },
      "steps":[1],
      "last_occurrence_only":true,
      "max_probes":'"$N"',
      "top_n_routes":20
    }' | $PY -c "import json,sys; d=json.load(sys.stdin); print('  cluster:', d.get('statistics',{}).get('total_probes','?'),'probes,', d.get('statistics',{}).get('total_routes','?'),'routes; detail:', d.get('detail'))" && \
  curl -s -X POST http://localhost:8000/api/experiments/analyze-routes \
    -H "Content-Type: application/json" \
    -d '{
      "mode":"compute",
      "session_id":"'"$SID"'",
      "save_as":"'"$SAVE"'",
      "window_layers":[22,23],
      "steps":[1],
      "last_occurrence_only":true,
      "max_probes":'"$N"',
      "top_n_routes":20
    }' | $PY -c "import json,sys; d=json.load(sys.stdin); print('  expert :', d.get('statistics',{}).get('total_routes','?'),'routes; detail:', d.get('detail'))" || { echo "FAILED at ${SAVE} — halting sweep"; break; } \
done
```

For multi-axis sweeps, nest loops; the suffix concatenates per axis (e.g.
`_max25_step01`). Use the suffix table in the YAML defaults.

**Sweep wall-time:** roughly `30s × N` for clustering compute, plus
`~3 × baseline` for expert ranks. A 7-element subsample sweep ≈ 6 minutes.

### OP-3: List schemas for a session

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && \
curl -s http://localhost:8000/api/probes/sessions/$SID/clusterings | $PY -m json.tool
```

Returns a `clusterings` array of `meta.json` blobs (name, created_at, params,
filters, sample_size, expert_routes_params).

### OP-4: Archive a schema

Moves the schema directory to `clusterings/_archive/<name>_<ts>/`. The schema
disappears from the UI's list but is recoverable by `mv`-ing back manually.
Restore is intentionally not an API surface — one-line filesystem op.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SCHEMA_NAME && \
curl -s -X POST http://localhost:8000/api/probes/sessions/$SID/clusterings/$SAVE/archive | $PY -m json.tool
```

Manual restore:

```bash
ROOT=$(git rev-parse --show-toplevel) && SID=SESSION_ID && \
mv "$ROOT/data/lake/$SID/clusterings/_archive/<archived_name>" "$ROOT/data/lake/$SID/clusterings/<original_name>"
```

### OP-5: Delete a schema

Permanent. Returns 409 if `reports/` or `element_descriptions.json` exist
(those represent invested analysis time). Override with `?force=true`.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SCHEMA_NAME && \
curl -s -X DELETE "http://localhost:8000/api/probes/sessions/$SID/clusterings/$SAVE" | $PY -m json.tool
```

Force delete (only when you're certain):

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SCHEMA_NAME && \
curl -s -X DELETE "http://localhost:8000/api/probes/sessions/$SID/clusterings/$SAVE?force=true" | $PY -m json.tool
```

### OP-6: Show defaults

The `Default clustering config` block at the top of this file is the
authoritative source. To inspect what was actually used by a built schema:

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && \
SID=SESSION_ID && SAVE=SCHEMA_NAME && \
$PY -m json.tool < "$ROOT/data/lake/$SID/clusterings/$SAVE/meta.json"
```

---

## Common workflows

### Build the default schema after a session completes

1. `/server` OP-1 to confirm backend ready.
2. OP-1 here with `save_as=<study>_k6_n15`, `window_layers=[22,23]`,
   defaults for the rest. Wait ~30s for cluster, ~90s for expert (3 ranks).
3. Verification block above to confirm files on disk.
4. Open MUDApp, pick the session, pick the new schema in the Toolbar — Sankey,
   trajectory, and expert routes should all render without recomputing.

### Subsample sweep for paper

Run OP-2 with `max_probes ∈ {25, 50, 100, 150, 200, 300, 400}`, `k=4`, single
window `[22,23]`. ~6 minutes wall time. After the sweep, OP-3 lists all 7
schemas; each one can be analyzed separately via `/analyze`.

### Recover from a misconfigured build

OP-4 (archive) preserves the bad schema for forensic inspection. Then OP-1 with
the corrected params using a fresh `save_as`. If you're sure the bad one is
worthless, OP-5 (delete) skips the archive step.

---

## Troubleshooting

### 409 — `schema_params_mismatch` or `schema_filter_mismatch`

You're trying to extend (OP-1B) or re-build a schema with different params
than what `meta.json` records. The response includes a `diff` field showing
the offending keys. Either fix the request to match, archive the old schema
and start fresh, or pick a new `save_as`.

### 409 — Window `w_X_Y` already exists

OP-1B can't overwrite. To replace, archive the schema and rebuild with the
union of windows.

### 409 on delete — `schema_has_invested_data`

The schema has reports or element_descriptions. Default refuses delete to
prevent accidental loss of analysis work. Pass `?force=true` to override.

### 404 — Schema not found

Check `OP-3` to see what schemas exist. The `_archive/` directory is excluded
from the listing.

### 404 on trajectory endpoint

The schema was built before `trajectory_points.json` existed. Per the
no-migration policy: archive (OP-4) and rebuild (OP-1) — don't try to patch
the missing file.

---

## Important rules

- **`save_as` is required for compute mode.** No auto-generated names.
- **Schemas are immutable.** Re-compute with same `save_as` only to extend
  with new windows; for any other change, archive + rebuild.
- **Expert routes are part of the schema.** A schema without rank{1,2,3}
  files is half-formed; OP-1 always builds both endpoints.
- **Halt-on-failure for sweeps.** Don't continue past a failed schema —
  diagnose and restart.
- **Never delete without checking for reports.** The 409 guard catches the
  common mistake; only force-delete when you're sure nothing of value lives
  in the schema.
- **Frontend is a pure viewer.** Schema lifecycle lives here, not in the UI.
