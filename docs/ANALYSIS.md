Related: docs/PIPELINE.md (orchestration context), docs/PROBES.md (probe creation), data/sentence_sets/GUIDE.md (sentence set design)

# Analysis Guide — Claude Code Cluster & Route Analysis

**Primary workflow:** The `/analyze` skill (`.claude/skills/analyze/SKILL.md`) is the operational procedure. This document provides reference detail on methodology, data structures, and report formats.

This guide teaches Claude Code how to analyze cluster/route data from Open LLMRI sessions and write reports.

## Prerequisites

- A completed probe session (run via `POST /api/probes/sentence-experiment`)
- Cluster analysis results (run via `POST /api/experiments/analyze-cluster-routes`)

## Pipeline Overview

After capturing probes:

1. **Generate outputs** — already captured with `generate_output=True`
2. **Read outputs** — `GET /api/probes/sessions/{id}/generated-outputs`
3. **Categorize outputs** — read each generated text, classify, POST categories back
4. **Run cluster analysis** for each window with `save_as` parameter
5. **Analyze each window** — read the data, identify patterns, write report
6. **Save reports** — `POST /api/probes/sessions/{id}/clusterings/{schema}/reports/{window_key}`

## Step 2-3: Output Categorization

Read generated texts:
```
GET /api/probes/sessions/{session_id}/generated-outputs
```

Returns list of `{probe_id, input_text, label, generated_text, output_category}`.

Read each `generated_text`. Classify along the **output axes** defined in the sentence set JSON (see `output_axes` array in the file). Each set type has different output axes — read them from the JSON, not hardcoded.

For each generated text, choose:
1. **Multi-axis classifications** (`output_category_json`) — classify along EVERY axis in the sentence set's `output_axes` array
2. A **primary output category** (`output_category`) — the cross-cell label from the axes

### Finding classification rules

Classification rules are **per-experiment**, stored in the probe guide alongside the sentence set JSON:
```
# From session metadata, get sentence_set_name
# Find probe guide: data/sentence_sets/**/{sentence_set_name}.md
# Read the "Output Classification Rules" section
```

Do NOT hardcode classification rules here — always read them from the probe guide.

### POST format

```
POST /api/probes/sessions/{session_id}/output-categories
Body: {
  "probe_id_1": {
    "output_category": "category_value",
    "output_category_json": "{\"axis_id\": \"value\"}"
  },
  "probe_id_2": {
    "output_category": "other_value",
    "output_category_json": "{\"axis_id\": \"other_value\"}"
  }
}
```

The `output_category_json` must be a **JSON string** (not a dict) — the backend stores it as a string column in Parquet. The keys must match `output_axes[].id` and values must be from `output_axes[].values`.

Both fields are written to existing columns on ProbeRecord in tokens.parquet. The output category nodes in Sankey diagrams group by `output_category` and use `output_category_json` for color blending.

For multi-axis output designs (e.g., 2×2 factorial), the `output_category` is typically a composite: `{axis1_value}_{axis2_value}` (e.g., `fictional_physical`). For single-axis designs, `output_category` is just the axis value directly (e.g., `aquarium`).

## Step 4: Running Cluster Analysis

For each window in the session's layer range, call:

```
POST /api/experiments/analyze-cluster-routes
{
  "session_id": "...",
  "window_layers": [0, 1],
  "clustering_config": {
    "reduction_dimensions": 5,
    "clustering_method": "hierarchical",
    "embedding_source": "residual_stream",
    "reduction_method": "umap",
    "layer_cluster_counts": {"0": 6, "1": 6}
  },
  "save_as": "default_umap_h6"
}
```

Repeat for each window: `[0,1]`, `[1,2]`, `[2,3]`, etc.

To load from a previously saved schema (no need to re-specify clustering config):
```
POST /api/experiments/analyze-cluster-routes
{
  "session_id": "...",
  "window_layers": [22, 23],
  "clustering_schema": "default_umap_h6",
  "output_grouping_axes": ["topic"],
  "top_n_routes": 20
}
```

- `clustering_schema` loads the saved config from the schema's `meta.json`
- `output_grouping_axes` adds output category nodes to the response; values are axis IDs from the sentence set's `output_axes` (e.g., `["topic"]`)

Also run expert routes:
```
POST /api/experiments/analyze-routes
{
  "session_id": "...",
  "window_layers": [0, 1],
  "top_n_routes": 20
}
```

## Step 5: Analyzing a Window

Each window's response contains:

### Nodes (clusters)
```json
{
  "name": "L0C3",
  "layer": 0,
  "expert_id": 3,
  "token_count": 15,
  "label_distribution": {"roleplay": 12, "factual": 3},
  "category_distributions": {"voice": {"first_person": 8, "third_person": 7}},
  "specialization": "roleplay (80%) / factual (20%)",
  "tokens": [{"target_word": "threatened", "label": "roleplay", "input_text": "...", "probe_id": "..."}]
}
```

### Links (transitions between clusters across layers)
```json
{
  "source": "L0C3",
  "target": "L1C5",
  "value": 10,
  "probability": 0.67,
  "label_distribution": {"roleplay": 9, "factual": 1}
}
```

### Top Routes (most common paths)
```json
{
  "signature": "L0C3→L1C5",
  "count": 10,
  "coverage": 0.25,
  "avg_confidence": 0.85,
  "example_tokens": [...]
}
```

### What to Look For

1. **Cluster purity**: Does a cluster specialize in one label? High purity = the model's representation space separates semantic categories.
   - >80% one label = strong specialization
   - 50/50 = shared processing (interesting!)

2. **Cross-layer consistency**: Do probes stay in "the same kind" of cluster across layers, or do they diverge? Consistent routing = stable representation.

3. **Label-specific routes**: Do all roleplay probes follow the same path? Or multiple paths? Multiple paths suggest sub-categories within a label.

4. **Category interactions**: When `category_distributions` shows additional axes (voice, specificity, etc.), check if these correlate with routing differently than the primary label.

5. **Transition probabilities**: A link with probability 0.9 means that cluster is highly predictive of the next layer's cluster. Low probability = the representation diverges.

6. **Route coverage**: If the top 5 routes cover 80%+ of probes, routing is concentrated. If they cover <50%, routing is distributed.

### Report Format

Write a markdown report for each window:

```markdown
# Window L{start}-L{end} Analysis

## Cluster Summary
- **C0** (N probes): [dominant label] ([purity]%). [1-sentence description of what this cluster captures]
- **C1** (N probes): ...

## Key Findings
1. [Most striking pattern — usually label separation quality]
2. [Secondary pattern — routing concentration or distribution]
3. [Any anomalies or unexpected groupings]

## Routing Patterns
- [Top route and what it means]
- [Any label-specific routing paths]
- [Transition probability highlights]

## Category Axis Interactions
- [If additional axes exist, note correlations with clusters]
```

## Step 6: Saving Reports

```
POST /api/probes/sessions/{id}/clusterings/{schema_name}/reports/w_0_1
Body: {"report": "# Window L0-L1 Analysis\n\n..."}
```

## Step 7: Element Descriptions

Element descriptions are short human-written labels for each cluster node in a schema. They appear in the UI as tooltips/labels on Sankey nodes.

### Endpoint

```
POST /api/probes/sessions/{session_id}/clusterings/{schema_name}/element-descriptions
Content-Type: application/json
Body: {
  "descriptions": {
    "cluster-0-L22": "Spatial/physical contexts — locations and movement",
    "cluster-1-L22": "Abstract/metaphorical usage",
    "cluster-3-L23": "Mixed financial and temporal senses"
  }
}
```

### Key format

**Clusters**: `cluster-{N}-L{layer}`
- `{N}` is the cluster index (0-based), `{layer}` is the layer number
- Examples: `cluster-0-L22`, `cluster-5-L23`
- Note: This is NOT the Sankey node label format (`L22C0`). The key format uses dashes and spells out `cluster-`.

**Routes**: `route-{signature}`
- Signature uses the Sankey node labels joined by `→`
- Examples: `route-L22C3→L23C4`, `route-L22C0→L23C1`

Both types go in the same `descriptions` dict:
```json
{
  "descriptions": {
    "cluster-3-L22": "Vehicle-dominant cluster (95%) — military and recreational tank contexts",
    "route-L22C3→L23C4": "Pure vehicle route — formal combat and operational narratives"
  }
}
```

### Semantics

- **PATCH/merge behavior**: Descriptions are merged with any existing descriptions. You can POST a subset of clusters and existing descriptions for other clusters are preserved.
- **Overwrite**: Posting a key that already exists overwrites that description.
- **No delete**: To clear a description, POST an empty string for that key.

### When to write descriptions

Write element descriptions during Stage 5 analysis, after examining each cluster's `label_distribution`, `tokens`, and `category_distributions`. Each description should capture the semantic theme of the cluster in 5-15 words.

### Fallback: Direct disk write

If the API endpoint returns 404 (WSL2 reload issue — see `.claude/skills/server/TROUBLESHOOTING.md`), write directly to disk:

```
data/lake/{session_id}/clusterings/{schema}/element_descriptions.json
```

This is a flat JSON dict of `{descKey: description}`. Merge with existing content if the file already exists.

## Default Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| clustering_method | hierarchical | Better for non-spherical clusters |
| reduction_method | umap | Better separation than PCA for visualization |
| reduction_dimensions | 5 | 5D for clustering (trajectory viz uses 3D projection) |
| n_clusters | 6 | Start here, adjust if clusters are too granular or too coarse |
| embedding_source | residual_stream | Primary source; expert_output is alternative |
| schema_name | default_umap_h6 | Naming convention: {method}_{reduction}_{clustering_initial}{n} |

## Naming Convention for Schemas

`{purpose}_{reduction}_{clustering_method_initial}{n_clusters}`

Examples:
- `default_umap_h6` — default analysis, UMAP reduction, hierarchical, 6 clusters
- `fine_umap_h12` — finer analysis with 12 clusters
- `expert_pca_k4` — expert output source, PCA, kmeans, 4 clusters
