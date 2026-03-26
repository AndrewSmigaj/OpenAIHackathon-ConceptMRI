# Concept MRI Analysis Pipeline

This document is the master orchestration runbook for Claude Code. Read it at the start of any analysis session.

## How to Use

1. Read this document to understand the pipeline stages
2. Check pipeline state (below) to determine where we are
3. Execute the next incomplete stage
4. **Stop at USER GATES** — wait for user direction before proceeding

## Checking Pipeline State

Run these checks to determine the current stage for a given experiment:

```
1. GET /api/probes
   → Find session by sentence_set_name or session_name
   → If no session found → Stage 1 (design experiment)

2. Check session state field
   → If not 'completed' → Stage 2 (still capturing)

3. GET /api/probes/sessions/{id}/generated-outputs
   → Check output_category field on first few entries
   → If null/empty → Stage 3 (categorize outputs)

4. GET /api/probes/sessions/{id}/clusterings
   → If empty → USER GATE (clustering exploration)

5. For each schema: check if reports exist
   → Load schema → check reports dict
   → If no reports → Stage 5 (analysis)
   → If reports exist → Stage 6 (present) or temporal gate
```

### Finding the probe guide

From session metadata, read `sentence_set_name`. Then:
```
glob data/sentence_sets/**/{sentence_set_name}.md
```
The probe guide contains experiment-specific classification rules, hypotheses, and analysis focus.

---

## Stage 1: Experiment Design (Interactive)

Use `/probe` skill or freeform conversation. This is the creative phase — user and Claude co-design the experiment.

**Inputs**: User brings a concept to probe (word + semantic question)
**Outputs**:
- Probe guide: `data/sentence_sets/{category}/{name}.md`
- Sentence set: `data/sentence_sets/{category}/{name}.json`

See `data/sentence_sets/GUIDE.md` for quality rules and schema format.

---

## Stage 2: Probe Capture

**Prerequisites**: Backend server running (see SERVERS.md)

```bash
curl -X POST http://0.0.0.0:8000/api/probes/sentence-experiment \
  -H "Content-Type: application/json" \
  -d '{"sentence_set_name": "EXPERIMENT_NAME"}'
```

Returns `session_id`. Monitor progress:
```bash
curl http://0.0.0.0:8000/api/probes/{session_id}/status
```

**Timing**: ~0.5s per sentence. First run adds ~30-60s for model loading.
**Completion**: `state = 'completed'` in status response.

---

## Stage 3: Output Categorization

**Prerequisites**: Session completed with `generate_output=true`

### Step 1: Read generated outputs
```bash
curl http://0.0.0.0:8000/api/probes/sessions/{session_id}/generated-outputs
```
Returns list of `{probe_id, input_text, label, generated_text, output_category}`.

### Step 2: Read classification rules
Read the probe guide (`data/sentence_sets/**/{name}.md`) for output axes and classification rules.

### Step 3: Classify each output
For each `generated_text`, determine:
- `output_category`: Primary classification label
- `output_category_json`: JSON string with per-axis classifications

### Step 4: POST categories
```bash
curl -X POST http://0.0.0.0:8000/api/probes/sessions/{session_id}/output-categories \
  -H "Content-Type: application/json" \
  -d '{
    "probe_id_1": {
      "output_category": "aquarium",
      "output_category_json": "{\"topic\": \"aquarium\"}"
    },
    "probe_id_2": {
      "output_category": "vehicle",
      "output_category_json": "{\"topic\": \"vehicle\"}"
    }
  }'
```

**Note**: `output_category_json` must be a JSON **string** (not a dict). Keys match `output_axes[].id`, values from `output_axes[].values`.

**Resumability**: If interrupted, re-read generated-outputs and skip probes that already have `output_category` set.

**Completion**: All probes have `output_category` populated.

---

## USER GATE: Clustering Exploration

**Stop here.** Tell the user:

> "Outputs categorized. Open the UI at http://localhost:5173, select this session, and explore clustering parameters in the Latent Space tab. When you find a clustering you like, tell me:
> 1. The schema name to save it as
> 2. The clustering parameters (or just 'use current UI settings')"

Wait for user to return with their preferred clustering.

---

## Stage 4: Schema Registration

User provides a schema name and clustering config. Save it:

```bash
# Cluster routes — first call uses save_as to create/register the schema
curl -X POST http://0.0.0.0:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "window_layers": [0, 1],
    "clustering_config": {
      "reduction_dimensions": 5,
      "clustering_method": "hierarchical",
      "embedding_source": "residual_stream",
      "reduction_method": "umap",
      "layer_cluster_counts": {"0": 6, "1": 6}
    },
    "save_as": "SCHEMA_NAME",
    "top_n_routes": 20
  }'

# Subsequent calls on the same schema use clustering_schema to load saved params
# Add output_grouping_axes to include output category nodes in the Sankey
curl -X POST http://0.0.0.0:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "window_layers": [0, 1],
    "clustering_schema": "SCHEMA_NAME",
    "output_grouping_axes": ["topic"],
    "top_n_routes": 20
  }'

# Expert routes (same window)
curl -X POST http://0.0.0.0:8000/api/experiments/analyze-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "window_layers": [0, 1],
    "save_as": "SCHEMA_NAME",
    "top_n_routes": 20
  }'
```

### Key parameters

| Parameter | Purpose |
|-----------|---------|
| `save_as` | Create/register a new schema — stores clustering_config for reuse |
| `clustering_schema` | Load a previously saved schema's config (no need to include `clustering_config` — the API loads it from the saved schema's `meta.json`) |
| `output_grouping_axes` | Add output category nodes to the Sankey; values are axis IDs from the sentence set's `output_axes` (e.g., `["topic"]`) |
| `top_n_routes` | Number of top routes to include in the response |

Repeat for each window the user wants analyzed.

**Completion**: Schema appears in `GET /api/probes/sessions/{id}/clusterings`.

---

## Stage 5: Analysis & Reports

**Prerequisites**: Schema registered (Stage 4 complete). Use `/analyze` skill or follow steps below.

This is the LLM reasoning stage — Claude reads actual sentences, distributions, and route patterns, then writes analytical reports. NO keyword/regex hacks. Claude must read and reason about the data as an LLM.

### Step 5.1: Load Schema & Probe Guide

```bash
# Load schema metadata
curl http://0.0.0.0:8000/api/probes/sessions/{session_id}/clusterings/{schema_name}

# Read probe guide for experiment-specific analysis focus
# glob data/sentence_sets/**/{sentence_set_name}.md
```

Start from **last-layer windows** (where routing decisions finalize before output) and work backward. The probe guide's "Analysis Focus" section directs what to look for.

### Step 5.2: Analyze Each Window

For each window, load cached cluster data:
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

Claude examines the response JSON and writes analysis:

**A. Cluster Summary** — For each node:
- `label_distribution` → which input labels dominate?
- `category_distributions` → do additional axes correlate?
- `tokens` (up to 10 examples) → read the actual sentences
- Name the cluster based on what it captures

**B. Route Analysis** — For each top route:
- `example_tokens` → read the sentences that follow this path
- `label_distribution` on links → is this route label-pure or mixed?
- `coverage` → how much traffic uses this route?
- Output node connections → what output categories do these sentences produce?

**C. Output Category Analysis** (when output nodes present):
- Which routes lead to which output categories?
- Mismatches (input label ≠ output category) → read the mismatched sentences and explain WHY

### Step 5.3: Deep-Dive on Interesting Routes

For routes showing confusion, divergence, or high purity:
```bash
curl "http://0.0.0.0:8000/api/experiments/route-details?session_id=...&signature=L22C3→L23C1&window_layers=22,23"
```

Read ALL sentences in the route and identify: structural patterns, semantic themes, why misclassified sentences confuse the model.

### Step 5.4: Write Window Report

```markdown
# Window L{start}-L{end} Analysis

## Cluster Summary
- **C0** (N probes): [name]. [dominant label] ([purity]%). [description]

## Key Findings
1. [Most striking pattern]
2. [Anomalies or unexpected groupings]

## Routing Patterns
- [Top route interpretation]
- [Output category correlations]

## Sentence-Level Observations
- [What sentences in key routes have in common]
- [Why certain sentences get misrouted]
```

### Step 5.5: Save Reports

```bash
curl -X POST http://0.0.0.0:8000/api/probes/sessions/{id}/clusterings/{schema}/reports/w_{start}_{end} \
  -H "Content-Type: application/json" \
  -d '{"report": "# Window L{start}-L{end} Analysis\n\n..."}'
```

### Step 5.6: Cross-Window Synthesis

After multiple windows analyzed, write a synthesis report covering:
- How routing evolves across layers
- At which layer the model "decides" the sense
- Persistent clusters across layers

Save as: `POST .../reports/synthesis`

See ANALYSIS.md for the full report template and methodology.

---

## Stage 6: Report Presentation

List available schemas and their reports:
```bash
curl http://0.0.0.0:8000/api/probes/sessions/{id}/clusterings
```

For each schema, load full details including reports:
```bash
curl http://0.0.0.0:8000/api/probes/sessions/{id}/clusterings/{schema_name}
```

Present summary to user. User selects which reports to review in detail.

---

## USER GATE: Temporal Analysis

User specifies:
1. Which schema to use
2. Two basin clusters (cluster IDs at a specific layer)

```bash
curl -X POST http://0.0.0.0:8000/api/experiments/temporal-capture \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "basin_a_cluster_id": 0,
    "basin_b_cluster_id": 3,
    "basin_layer": 2,
    "clustering_schema": "SCHEMA_NAME",
    "sentences_per_block": 20,
    "processing_mode": "expanding_cache_on",
    "sequence_config": "block_ab",
    "generate_output": true
  }'
```

Returns `new_session_id`. Re-enter pipeline at Stage 2 for the temporal session.

---

## Schema Naming Convention

`{purpose}_{reduction}_{clustering_initial}{n_clusters}`

Examples:
- `default_umap_h6` — default analysis, UMAP, hierarchical, 6 clusters
- `fine_umap_h12` — finer analysis, 12 clusters
- `expert_pca_k4` — expert output source, PCA, kmeans, 4 clusters

## Default Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| clustering_method | hierarchical | Better for non-spherical clusters |
| reduction_method | umap | Better separation than PCA |
| reduction_dimensions | 5 | 5D for clustering |
| n_clusters | 6 | Adjust per experiment |
| embedding_source | residual_stream | Primary; expert_output is alternative |
