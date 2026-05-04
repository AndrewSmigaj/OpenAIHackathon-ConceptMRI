---
name: analyze
description: Analyze a saved clustering schema — read data, reason about patterns, write reports
---

# Schema Analysis

Analyze cluster/route data from an Open LLMRI session. This is an LLM reasoning task — read actual sentences, distributions, and route patterns. NO keyword/regex hacks.

**Schemas are immutable artifacts on disk.** This skill reads them; it never
creates, modifies, or deletes them. Use `/cluster` for the schema lifecycle
(OP-1 build, OP-1B extend, OP-4 archive, OP-5 delete).

## Invocation

Can be invoked as `/analyze {session_id} schema {schema_name} transition {start}-{end}`, e.g.:
```
/analyze session_1434a9be schema polysemy_explore transition 22-23
```

When invoked with parameters, skip the identification step and go straight to loading the probe guide.
When `transition` is specified, only analyze that 2-layer pair — do NOT process other transitions.

**Terminology**: a *window* is a 6-layer range (one of `w0=[0,5]`, `w1=[5,11]`, `w2=[11,17]`, `w3=[17,23]`); a *transition* is a 2-layer pair within a window (e.g. `[22,23]`). Each schema covers all 4 windows × 6 transitions × {cluster + expert ranks 1/2/3}.

## Workflow

### 1. Identify Session & Schema

Ask the user which session and schema to analyze, or detect from context.

```bash
# List available schemas
curl http://localhost:8000/api/probes/sessions/{session_id}/clusterings
```

### 2. Load Probe Guide (ALWAYS DO THIS FIRST)

From session metadata, get `sentence_set_name`:
```bash
curl http://localhost:8000/api/probes/{session_id}
```

Then read the probe guide for experiment-specific analysis focus:
```
glob data/sentence_sets/**/{sentence_set_name}.md
```

**Read the guide carefully** — it explains what the probe is testing, what to look for in the data, and how to interpret routing patterns. This context is essential for meaningful labeling.

### 3. Analyze Transitions

If a `transition` parameter was given, analyze only that 2-layer pair. Otherwise start with the last-layer transition (e.g., [22,23]) and work backward.

For each transition, load cached data:
```bash
curl -X POST http://localhost:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_ids": ["..."],
    "schema_name": "SCHEMA_NAME",
    "transition_layers": [X, Y],
    "top_n_routes": 20
  }'
```

The right column buckets (output nodes) are baked at build time as
`ground_truth` (friend / foe / unknown). The frontend's color-axis dropdown
recolors these existing nodes locally — it never refetches.

Examine the response:

**Nodes** (clusters): Read `label_distribution`, `category_distributions`, and **ALL sentences** in `tokens`. The API now returns every sentence in each cluster (no cap). Read them all — don't skip or sample. Understanding the full distribution is critical for accurate labeling.

**Links** (transitions): Read `probability`, `label_distribution`, and **ALL link examples**. Identify pure vs mixed routes.

**Top Routes**: Read ALL `example_tokens`, `coverage`, `avg_confidence`. Understand what sentences follow each path.

**Output Nodes** (if present): Which clusters route to which output categories? Any input/output mismatches?

### 4. Deep-Dive on Interesting Routes

For routes with confusion or unexpected patterns:
```bash
curl "http://localhost:8000/api/experiments/route-details?session_id=...&signature=ROUTE_SIG&window_layers=X,Y"
```

Read ALL sentences. Identify structural patterns, semantic themes, reasons for misclassification.

### 5. Write Reports

Per-transition report (see docs/ANALYSIS.md for full template):

```markdown
# Transition L{start}→L{end} Analysis

## Cluster Summary
- **C0** (N probes): [name]. [label] ([purity]%). [description]

## Key Findings
1. [Most striking pattern]
2. [Anomalies]

## Routing Patterns
- [Top route interpretation]
- [Output category correlations]

## Sentence-Level Observations
- [Common patterns in key routes]
- [Why misrouted sentences confuse the model]
```

### 6. Save Reports

```bash
curl -X POST http://localhost:8000/api/probes/sessions/{id}/clusterings/{schema}/reports/w_{start}_{end} \
  -H "Content-Type: application/json" \
  -d '{"report": "..."}'
```

### 7. Generate Element Descriptions

After analyzing each transition, generate 1-2 sentence descriptions for every cluster node and top route visible in that transition. These populate the click-to-inspect cards in the frontend.

**Approach — comparative, not isolated:**
1. First read ALL sentences in ALL clusters for the transition layer pair
2. Identify what makes each cluster distinct from the others (not just what's in it, but what's NOT in it)
3. For each cluster: what input types does it capture? How is it different from neighboring clusters?
4. For each route: what distinguishes the sentences that take this path? If a cluster splits into multiple destinations, explain what causes the split.
5. For output links: which clusters route cleanly to one output vs split? What explains the confusion?
6. Reference findings from the probe guide — the guide tells you what semantic dimensions to look for

**Key format** matches frontend `descKey`:
- Clusters: `cluster-{id}-L{layer}` (e.g., `cluster-3-L22`)
- Routes: `route-{signature}` (e.g., `route-L22C3→L23C1`)

```bash
curl -X POST http://localhost:8000/api/probes/sessions/{id}/clusterings/{schema}/element-descriptions \
  -H "Content-Type: application/json" \
  -d '{"descriptions": {"cluster-3-L22": "Vehicle-dominant cluster...", "route-L22C3→L23C1": "Pure vehicle route..."}}'
```

Descriptions are merged with any existing ones (safe to call incrementally per transition).

**Fallback**: If the API endpoint returns 404 (WSL2 reload issue — see server TROUBLESHOOTING.md), write directly to disk:
```
data/lake/{session_id}/clusterings/{schema}/element_descriptions.json
```
The file is a flat JSON dict of `{descKey: description}`. Merge with existing content if the file already exists.

**IMPORTANT**: This step is NOT optional. Every `/analyze` run MUST produce element descriptions alongside the report. The descriptions populate the click-to-inspect cards in the frontend — without them, users see "No AI description" on every card.

### 8. Per-Window Synthesis (covers all 6 transitions in a window)

Every schema covers all 4 windows × 6 transitions per window. For each
window the user works in, produce a multi-lens synthesis that the frontend
surfaces preferentially over the last-transition report whenever the user
selects the full window's layer range.

**Filename convention.** Save the synthesis under the schema's `reports/`
directory as `w_<first>_<last>.md` (e.g. `reports/w_17_23.md` for window
`w3`). The frontend looks up reports by file stem via
`useSchemaManagement.schemaReports`; when `currentWindow.transitions.length > 1`
MUDApp prefers `w_<first>_<last>` over `w_<lastTransition>`. The "synthesis"
phrasing belongs in the report's H1, not in the filename.

**Six lenses** — each is a section the synthesis must cover:
1. **Layer-by-layer narrative** — basin sizes per layer table; one paragraph per
   layer summarising what changed since the previous layer.
2. **Basin topology evolution** — count of probes that change basin per
   transition (L→L+1). Identify the transition(s) where most topology change
   happens; everything else is stable refinement.
3. **Semantic stability** — for each canonical basin, list the dominant
   scenario types / subtypes; verify they match across layers (basin = stable
   semantic category, not drifting content).
4. **Correctness alignment** — which basins map cleanly to correct output,
   which leak. Use `probe_results.jsonl` for `correct` field.
5. **Leakage dynamics** — trace any pole-leak probes (probes whose basin pole
   disagrees with their ground-truth label) across all layers. Cite
   `reports/leakage_analysis.md` if it exists.
6. **Cross-layer basin identity** — map cluster IDs across layers via
   majority-overlap of probe membership; produce an identity-preservation
   table (basin × transition) showing the fraction of probes that remain in
   the canonical successor basin at the next layer.

**Synthesis section.** End with a 2–4 paragraph synthesis section that ties
the six lenses together — what's the headline finding, what's the story of
the model's representation as it flows through these layers.

**Cluster-ID stability across layers.** Hierarchical clustering renumbers
clusters per layer — basin "pure-foe" may be C0 at L17, C2 at L18, C5 at
L22, etc. Construct a canonical basin map by reading
`probe_assignments.json` and grouping cluster IDs across layers by
majority-overlap of their probe sets. Reference the canonical name (e.g.
"pure-foe") in the synthesis, not the renumbered cluster ID.

**Save** with the same `POST .../reports/w_<first>_<last>` endpoint as
per-transition reports.

## Key Principles

- **Read actual sentences** — never summarize by keywords alone
- **Reason about WHY** — don't just report distributions, explain what drives routing
- **Follow the probe guide** — each experiment has specific analysis focus areas
- **Start from output** — last-layer routes to output nodes show the model's final decision
- **Work backward** — trace interesting patterns to earlier layers
- **Never claim "collapse" or "loss of encoding" from cluster purities alone.** Fixed-k hierarchical clustering picks the k most-separable cuts in the dendrogram. If two design axes have shifting relative variance across layers, k can pick axis-A cuts at one layer and axis-B cuts at the next, even when both axes are equally encoded throughout. Before claiming a representation change, verify with at least one of:
  - **Within-cluster linear probe**: train logistic regression on residual streams of probes inside a single cluster, predicting the design axis. If accuracy is high inside the cluster, the axis is preserved — the algorithm just merged it.
  - **k-sweep**: rebuild the schema at k=8 or k=12. If finer partitions recover the supposedly-lost axis, the original "loss" was algorithmic.
  - **Layer-by-layer linear probe**: train at every layer separately. A flat-near-ceiling curve means information is preserved; clustering structure changes are visualization artifacts. A real drop means something genuinely changed.

  This is methodologically critical for composition / orthogonality / preservation claims. Cluster reorganization between layers ≠ representation reorganization.

## Data-contract notes

- **Cluster-ID renumbering is per-layer.** Always build a canonical basin
  map (Step 8 lens 6) before making cross-layer claims. Renaming
  C0→C2→C5 is a renumbering artefact, not migration.
- **Reports are keyed by file stem.** Save per-transition as `w_X_Y.md`
  (where X,Y is the 2-layer pair) and the per-window synthesis as
  `w_<first>_<last>.md` (covering all 6 transitions in that window). The
  frontend lookup is `schemaReports[stem]`.
