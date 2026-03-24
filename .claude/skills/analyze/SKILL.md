---
name: analyze
description: Analyze a saved clustering schema — read data, reason about patterns, write reports
---

# Schema Analysis

Analyze cluster/route data from a Concept MRI session. This is an LLM reasoning task — read actual sentences, distributions, and route patterns. NO keyword/regex hacks.

## Workflow

### 1. Identify Session & Schema

Ask the user which session and schema to analyze, or detect from context.

```bash
# List available schemas
curl http://localhost:8000/api/probes/sessions/{session_id}/clusterings
```

### 2. Load Probe Guide

From session metadata, get `sentence_set_name`:
```bash
curl http://localhost:8000/api/probes/{session_id}
```

Then read the probe guide for experiment-specific analysis focus:
```
glob data/sentence_sets/**/{sentence_set_name}.md
```

### 3. Analyze Windows (Start from Last Layer)

Start with the last-layer window (e.g., [22,23]) where routing decisions are most crystallized, then work backward.

For each window, load cached data:
```bash
curl -X POST http://localhost:8000/api/experiments/analyze-cluster-routes \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "window_layers": [X, Y],
    "clustering_schema": "SCHEMA_NAME",
    "output_grouping_axes": ["topic"]
  }'
```

Examine the response:

**Nodes** (clusters): Read `label_distribution`, `category_distributions`, `tokens` (example sentences). Name each cluster by what it actually captures.

**Links** (transitions): Read `probability`, `label_distribution`. Identify pure vs mixed routes.

**Top Routes**: Read `example_tokens`, `coverage`, `avg_confidence`. Understand what sentences follow each path.

**Output Nodes** (if present): Which clusters route to which output categories? Any input/output mismatches?

### 4. Deep-Dive on Interesting Routes

For routes with confusion or unexpected patterns:
```bash
curl "http://localhost:8000/api/experiments/route-details?session_id=...&signature=ROUTE_SIG&window_layers=X,Y"
```

Read ALL sentences. Identify structural patterns, semantic themes, reasons for misclassification.

### 5. Write Reports

Per-window report (see ANALYSIS.md for full template):

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
curl -X POST http://localhost:8000/api/probes/sessions/{id}/clusterings/{schema}/reports/w_{start}_{end} \
  -H "Content-Type: application/json" \
  -d '{"report": "..."}'
```

### 7. Cross-Window Synthesis

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
