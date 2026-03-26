# Requirements: Temporal Tab & Output Panel

## Overview

Two features extending Concept MRI from static per-sentence analysis to dynamic sequential analysis and causal prediction analysis.

**Current state:** Each sentence is processed independently (no KV cache, no shared state). We capture routing decisions, MLP embeddings, and residual streams.

**After these features:** We can (A) study how routing evolves when semantic context shifts over a sequence of sentences, and (B) see what the model would output and correlate predictions with routing patterns.

**Paper reference:** `attractorpaper.md` — the temporal tab implements the Sequential Temporal Analysis and Cache Intervention protocols.

---

## Feature A: Temporal Tab

### Motivation

The existing analysis shows that MoE routing cleanly separates semantic regimes (e.g., aquarium vs vehicle meanings of "tank" occupy distinct residual stream clusters). But this is static — each sentence is processed in isolation. The temporal tab answers: **what happens when the model has been reading aquarium text and suddenly encounters vehicle sentences?**

Lag = confusion between basins. If the model has been processing basin A sentences and encounters a basin B sentence, does it still route the target word through basin A's cluster? How many sentences before it "realizes" the regime changed?

This maps directly to the paper's RQ3 (temporal dynamics) and the alignment concern: persistent regimes create temporal vulnerability windows.

### Workflow: Claude Code as Runtime

The frontend is a **display surface** — it shows analysis results and helps configure parameters. Claude Code is the runtime that executes pipeline stages.

1. **Run static analysis** — Claude Code runs cluster analysis on a session, identifies basins
2. **Select basins in UI** — user picks two opposing clusters from dropdowns (e.g., C0 = vehicle, C3 = aquarium at layer 22)
3. **Copy instruction** — UI generates a readable instruction for Claude Code with basin IDs, layer, schema, and processing mode
4. **Claude Code runs capture** — `POST /api/experiments/temporal-capture` creates a new session with KV cache chaining
5. **Claude Code runs cluster analysis** — on the new temporal session using the same schema
6. **View results** — lag chart renders inline, scrubber drives existing Sankey/trajectory views
7. **Repeat** — each run randomizes sentence order, builds statistical power

### Core Concept: Three Processing Conditions

The temporal experiment has three distinct processing conditions combining **input construction** and **KV cache**:

#### Condition 1: Expanding window, cache OFF (`expanding_cache_off`)
- At step N, sentences 1..N are **concatenated into a single input**
- Full forward pass from scratch — no cached computations
- **Pure context baseline** — any lag is driven entirely by what the model can see

#### Condition 2: Expanding window, cache ON (`expanding_cache_on`)
- Single sentence input, KV cache carries forward from all prior sentences
- Computationally faster than cache OFF
- The paper's "standard processing" condition

#### Condition 3: One sentence at a time, cache ON (`single_cache_on`)
- Each sentence processed individually, KV cache carries forward
- Isolates the **memory contribution** — can cached attention alone shift basins?

#### What comparisons measure

| Comparison | Question |
|------------|----------|
| Condition 1 vs 2 | Does caching change lag? (ΔPersistence) |
| Condition 1 vs 3 | Context visibility vs pure memory |
| Condition 2 vs 3 | Full text visible vs just cached K/V |

**ΔPersistence = lag(Condition 2) − lag(Condition 1)**

### Sequence Construction

Sentences come from the selected basin clusters via `probe_assignments.json` from the named schema.

**Block A→B:** N sentences from cluster A, then N sentences from cluster B. Within each block, randomly sampled. Each run uses a different random ordering.

| Config | Description | Use Case |
|--------|-------------|----------|
| `block_ab` | N of A then N of B | Clean regime transition (MVP) |
| `block_ba` | N of B then N of A | Reverse direction (hysteresis test) |
| `block_aba` | N of A, N of B, N of A | Recovery/reversion study |

### Backend (Implemented)

**Endpoint:** `POST /api/experiments/temporal-capture` — fully implemented at `experiments.py:474-625`

**Request/Response:** See `schemas.py:358-382` — `TemporalCaptureRequest` / `TemporalCaptureResponse`

**Enrichments (to be added):**
- Store source probe metadata in `categories_json` (source_probe_id, source_basin, source_cluster_id)
- Store run registry + sentence text mapping in `temporal_runs.json` in source session dir
- New endpoint: `GET /api/experiments/temporal-runs/{session_id}` — list temporal runs
- New endpoint: `POST /api/experiments/temporal-lag-data` — compute basin axis projection

### Lag Metric: Basin Axis Projection

For each temporal probe, project its residual stream vector onto the axis between basin A and basin B centroids:

```
centroid_a = mean(source_vectors[basin_a_probes])  # shape [2880]
centroid_b = mean(source_vectors[basin_b_probes])
axis = centroid_b - centroid_a
projection = dot(vec - centroid_a, axis_norm) / axis_length
```

Result: 0.0 = at basin A centroid, 1.0 = at basin B centroid. Values between = transitioning.

Equivalent to Fisher's Linear Discriminant. Standard neuroscience decoding approach. Computed on raw residual stream vectors (no reducer needed). ~0.03s for 400 probes.

### Frontend: Temporal Analysis Section

Replaces the LLMAnalysisPanel (dead code). Positioned below Cluster Routes Section.

#### Basin Selection Panel
- Layer dropdown (from available layers in cluster analysis)
- Basin A / Basin B dropdowns (shows cluster ID + dominant label + purity + probe count)
- Processing mode: expanding_cache_on (default) / expanding_cache_off / single_cache_on
- Instruction text box with Copy button — generates readable instruction for Claude Code

#### Lag Chart
- **X-axis:** sequence position (0, 1, 2, ... 2N)
- **Y-axis:** basin axis projection (0.0 = basin A, 1.0 = basin B)
- **Vertical dashed line** at regime boundary
- **One line per run**, colored by processing mode
- **Dot** tracks scrubber position
- Multiple runs of same condition: thin lines + bold average + shaded confidence band

#### Scrubber
- HTML `<input type="range">` slider (consistent with existing trajectory plot controls)
- Steps through sequence positions
- **Drives the existing Sankey/trajectory views** above — highlights the current probe's trajectory path through clusters
- Shows sentence text, regime label, and projection value below the slider
- Multiple runs selected → multiple trajectory paths highlighted

#### Trajectory Highlighting
- Scrubber emits current probe_id → ExperimentPage passes to SteppedTrajectoryPlot as `highlightedProbeId`
- Highlighted trajectory rendered as overlay `line3D` (bold, `zLevel:999`) + `scatter3D` (larger markers)
- All other trajectories dimmed (low opacity)
- Temporal session probes appear in shared reduced space by appending temporal session IDs to the trajectory plot's `sessionIds` array

#### Lag Metrics Display
- **Routing lag:** first position after boundary where projection crosses 0.5 and stays > 0.5 for 3 consecutive positions
- **ΔPersistence:** lag(cache_on) − lag(cache_off)
- **Basin separation:** L2 distance between centroids (measures how separable basins are)
- Requires multiple conditions to have been run

#### Controls
- Scrubber: step through positions
- Run checkboxes: toggle individual runs on/off
- Show/hide average line (when 2+ runs of same condition)

### Evolution Path

**MVP:** Select two clusters → Claude Code runs A→B with expanding_cache_on and expanding_cache_off → see lag charts, scrub through positions, view trajectory highlighting, compute ΔPersistence.

**V2:** Multiple randomized runs per condition, average + confidence bands, statistical tests.

**V3:** Layer cascade analysis (do some layers lag behind others?). Map regime labels to original basin names in trajectory colors.

**V4:** Hysteresis testing (A→B vs B→A). Recovery testing (A→B→A). Cross-probe basin validation.

---

## Feature B: Output Panel

(Unchanged from original — not implementing for the paper. Preserved for reference.)

### Motivation

Close the causal loop: routing → expert processing → residual stream → predicted next token. Do different routing patterns produce different predictions?

### Core Concept

After each forward pass, capture logits at target word position. Extract top-k predicted next tokens with softmax probabilities. Store alongside existing probe data. Display in UI as a color/filter axis.

### Status

**Not yet implemented.** The temporal tab is the scientific priority for the paper. Output panel extends the capture pipeline and is useful but not paper-critical.

---

## Open Questions

1. **KV cache memory:** With 40 sentences × ~25 tokens each, the KV cache grows to ~1000 tokens. Need to verify this is within the model's context window.
2. **Temporal sentence count:** How many sentences per block is enough to establish a "regime"? Start with 20, adjust based on results.
3. **Cross-probe basin validation:** Do basins from one probe family predict basins in another? Requires a "basin library" concept — future work.
