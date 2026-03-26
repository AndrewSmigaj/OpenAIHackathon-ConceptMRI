---
name: analyze
description: Analyze a saved clustering schema — read data, reason about patterns, write reports
---

# Schema Analysis

Analyze cluster/route data from a Concept MRI session. This is an LLM reasoning task — read actual sentences, distributions, and route patterns. NO keyword/regex hacks.

## Invocation

Can be invoked as `/analyze {session_id} schema {schema_name} window {start}-{end}`, e.g.:
```
/analyze session_1434a9be schema polysemy_explore window 22-23
```

When invoked with parameters, skip the identification step and go straight to loading the probe guide.
When `window` is specified, only analyze that window's layers — do NOT process other windows.

## Workflow

### 1. Identify Session & Schema

Ask the user which session and schema to analyze, or detect from context.

```bash
# List available schemas
curl http://0.0.0.0:8000/api/probes/sessions/{session_id}/clusterings
```

### 2. Load Probe Guide (ALWAYS DO THIS FIRST)

From session metadata, get `sentence_set_name`:
```bash
curl http://0.0.0.0:8000/api/probes/{session_id}
```

Then read the probe guide for experiment-specific analysis focus:
```
glob data/sentence_sets/**/{sentence_set_name}.md
```

**Read the guide carefully** — it explains what the probe is testing, what to look for in the data, and how to interpret routing patterns. This context is essential for meaningful labeling.

### 3. Analyze Windows

If a `window` parameter was given, analyze only that window. Otherwise start with the last-layer window (e.g., [22,23]) and work backward.

For each window, load cached data:
```bash
curl -X POST http://0.0.0.0:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "window_layers": [X, Y],
    "clustering_schema": "SCHEMA_NAME",
    "output_grouping_axes": ["topic"]
  }'
```

Examine the response:

**Nodes** (clusters): Read `label_distribution`, `category_distributions`, and **ALL sentences** in `tokens`. The API now returns every sentence in each cluster (no cap). Read them all — don't skip or sample. Understanding the full distribution is critical for accurate labeling.

**Links** (transitions): Read `probability`, `label_distribution`, and **ALL link examples**. Identify pure vs mixed routes.

**Top Routes**: Read ALL `example_tokens`, `coverage`, `avg_confidence`. Understand what sentences follow each path.

**Output Nodes** (if present): Which clusters route to which output categories? Any input/output mismatches?

### 4. Deep-Dive on Interesting Routes

For routes with confusion or unexpected patterns:
```bash
curl "http://0.0.0.0:8000/api/experiments/route-details?session_id=...&signature=ROUTE_SIG&window_layers=X,Y"
```

Read ALL sentences. Identify structural patterns, semantic themes, reasons for misclassification.

### 5. Write Reports

Per-window report (see docs/ANALYSIS.md for full template):

```markdown
# Window L{start}-L{end} Analysis

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
curl -X POST http://0.0.0.0:8000/api/probes/sessions/{id}/clusterings/{schema}/reports/w_{start}_{end} \
  -H "Content-Type: application/json" \
  -d '{"report": "..."}'
```

### 7. Generate Element Descriptions

After analyzing each window, generate 1-2 sentence descriptions for every cluster node and top route visible in that window. These populate the click-to-inspect cards in the frontend.

**Approach — comparative, not isolated:**
1. First read ALL sentences in ALL clusters for the window layer pair
2. Identify what makes each cluster distinct from the others (not just what's in it, but what's NOT in it)
3. For each cluster: what input types does it capture? How is it different from neighboring clusters?
4. For each route: what distinguishes the sentences that take this path? If a cluster splits into multiple destinations, explain what causes the split.
5. For output links: which clusters route cleanly to one output vs split? What explains the confusion?
6. Reference findings from the probe guide — the guide tells you what semantic dimensions to look for

**Key format** matches frontend `descKey`:
- Clusters: `cluster-{id}-L{layer}` (e.g., `cluster-3-L22`)
- Routes: `route-{signature}` (e.g., `route-L22C3→L23C1`)

```bash
curl -X POST http://0.0.0.0:8000/api/probes/sessions/{id}/clusterings/{schema}/element-descriptions \
  -H "Content-Type: application/json" \
  -d '{"descriptions": {"cluster-3-L22": "Vehicle-dominant cluster...", "route-L22C3→L23C1": "Pure vehicle route..."}}'
```

Descriptions are merged with any existing ones (safe to call incrementally per window).

**Fallback**: If the API endpoint returns 404 (WSL2 reload issue — see server TROUBLESHOOTING.md), write directly to disk:
```
data/lake/{session_id}/clusterings/{schema}/element_descriptions.json
```
The file is a flat JSON dict of `{descKey: description}`. Merge with existing content if the file already exists.

**IMPORTANT**: This step is NOT optional. Every `/analyze` run MUST produce element descriptions alongside the report. The descriptions populate the click-to-inspect cards in the frontend — without them, users see "No AI description" on every card.

### 8. Cross-Window Synthesis

After multiple windows, write a synthesis covering:
- Routing evolution across layers
- At which layer the model decides the sense
- Persistent clusters

Save as `POST .../reports/synthesis`.

## Key Principles

- **Read actual sentences** — never summarize by keywords alone
- **Reason about WHY** — don't just report distributions, explain what drives routing
- **Follow the probe guide** — each experiment has specific analysis focus areas
- **Start from output** — last-layer routes to output nodes show the model's final decision
- **Work backward** — trace interesting patterns to earlier layers
