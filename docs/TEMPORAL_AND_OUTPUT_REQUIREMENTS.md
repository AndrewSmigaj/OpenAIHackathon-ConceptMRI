# Requirements: Temporal Tab & Output Panel

## Overview

Two new features that extend Concept MRI from static per-sentence analysis to dynamic sequential analysis and close the causal loop from routing to prediction.

**Current state:** Each sentence is processed independently (no KV cache, no shared state). We capture routing decisions, MLP embeddings, and residual streams. We do NOT capture what the model predicts.

**After these features:** We can (A) study how routing evolves when semantic context shifts over a sequence of sentences, and (B) see what the model would output and correlate predictions with routing patterns.

**Paper reference:** `attractorpaper.md` — the temporal tab implements the Sequential Temporal Analysis and Cache Intervention protocols described in the Methods section.

---

## Feature A: Temporal Tab

### Motivation

The existing analysis shows that MoE routing cleanly separates semantic regimes (e.g., roleplay vs factual "threatened" sentences occupy distinct residual stream clusters). But this is static — each sentence is processed in isolation. The temporal tab answers: **what happens when the model has been reading factual text and suddenly encounters roleplay?**

Lag = confusion between basins. If the model has been processing basin A sentences and encounters a basin B sentence, does it still assign the target word to basin A's cluster? How many sentences before it "realizes" the regime changed?

This maps directly to the paper's RQ3 (temporal dynamics) and the alignment concern: persistent regimes create temporal vulnerability windows.

### User Workflow

The temporal tab is **driven by the static analysis** — user must first run cluster analysis to identify basins:

1. **Run static analysis** (Expert Routes / Latent Space) on a session
2. **Identify two opposing clusters** (e.g., C0 = factual, C5 = roleplay at layer 23)
3. **Select those two clusters** as basin indicators in the temporal tab UI
4. **Hit "Run Temporal Analysis"** — backend takes sentences assigned to each cluster and builds the expanding window sequence
5. **View the lag chart** — does the model show confusion between basins at the transition?
6. **Add more runs** — each run randomizes sentence order within blocks, building up statistical power
7. **View average** — with multiple runs, see the average transition curve plus individual runs

### Core Concept: Three Processing Conditions

The temporal experiment has three distinct processing conditions that combine two variables: **input construction** (expanding window vs single sentence) and **KV cache** (on vs off).

#### Condition 1: Expanding window, cache OFF
- At step N, sentences 1..N are **concatenated into a single input**
- Full forward pass from scratch — no cached computations
- The model sees the complete accumulated context as raw text each time
- **Pure context baseline** — any lag is driven entirely by what the model can see

#### Condition 2: Expanding window, cache ON
- Same expanding window (all sentences concatenated), but KV cache reuses prior computations
- At step N, only the new sentence needs fresh attention; prior sentences' K/V are cached
- Computationally faster than cache OFF
- The paper's "standard processing" condition

#### Condition 3: One sentence at a time, cache ON
- Each sentence is processed **individually** — only the current sentence is the input
- KV cache carries forward from ALL prior sentences
- The model "remembers" prior sentences **solely through cached attention**, not visible text
- Isolates the **memory contribution** — can the model maintain/shift basins from cached representations alone?
- (Cache OFF makes no sense here — model would have zero memory of prior sentences)

#### What comparisons measure

| Comparison | Question |
|------------|----------|
| Condition 1 vs 2 | Does caching change lag? (ΔPersistence from the paper) |
| Condition 1 vs 3 | Context visibility vs pure memory — does the model need to re-read prior sentences, or is cached attention enough? |
| Condition 2 vs 3 | Does having the full text visible (vs just cached K/V) affect basin transition speed? |

**ΔPersistence = lag(Condition 2) − lag(Condition 1)** quantifies how much cached memory extends regime influence beyond what recomputation alone produces.

### Sequence Construction

Sentences come from the selected basin clusters. The user selects two clusters (or two experts), and the backend pulls all probe sentences assigned to those clusters from the static analysis.

**Block A→B:** N sentences from cluster A, then N sentences from cluster B.

Within each block, sentences are **randomly sampled** from the available pool. Each "run" uses a different random ordering — this is how multiple runs build statistical robustness.

**Later sequence configs** (not MVP):

| Config | Description | Use Case |
|--------|-------------|----------|
| `block_ab` | N of A then N of B | Clean regime transition (MVP) |
| `block_ba` | N of B then N of A | Reverse direction (hysteresis test) |
| `block_aba` | N of A, N of B, N of A | Recovery/reversion study |

Hysteresis = comparing A→B lag vs B→A lag. If they differ, the basins have asymmetric "depth."

### Backend Requirements

**New endpoint:** `POST /api/experiments/temporal-capture`

```python
class TemporalCaptureRequest(BaseModel):
    session_id: str                    # Source session (for sentence/cluster data)
    basin_a_cluster_id: int            # Cluster ID for basin A
    basin_b_cluster_id: int            # Cluster ID for basin B
    basin_layer: int                   # Layer where clusters were identified
    sentences_per_block: int = 20      # N sentences per regime block
    processing_mode: str = "expanding_cache_on"  # "expanding_cache_off", "expanding_cache_on", "single_cache_on"
    sequence_config: str = "block_ab"  # "block_ab", "block_ba", "block_aba"
    layers: Optional[List[int]] = None
    run_label: Optional[str] = None    # e.g. "run_1", "run_2" for multi-run
```

**Alternative: select two experts instead of two clusters:**
```python
    basin_type: str = "cluster"        # "cluster" or "expert"
    basin_a_id: int                    # Cluster or expert ID for basin A
    basin_b_id: int                    # Cluster or expert ID for basin B
```

**Response:**
```python
class TemporalCaptureResponse(BaseModel):
    temporal_run_id: str               # Unique ID for this run
    session_id: str                    # Source session
    sequence_positions: int            # Total positions in sequence
    regime_boundary: int               # Position where A→B switch occurs
    processing_mode: str
    basin_a_sentences: int             # How many A sentences used
    basin_b_sentences: int             # How many B sentences used
```

**Capture flow:**
1. Look up probe assignments from the source session's cluster analysis
2. Collect all probe IDs assigned to basin A cluster and basin B cluster
3. Randomly sample N from each pool
4. Build sequence: [A₁, A₂, ..., Aₙ, B₁, B₂, ..., Bₙ]
5. For each sentence in order, behavior depends on `processing_mode`:
   - **`expanding_cache_off`**: Concatenate sentences 1..i into one input, full forward pass, no cache
   - **`expanding_cache_on`**: Concatenate sentences 1..i, forward pass with KV cache reuse from prior step
   - **`single_cache_on`**: Only sentence i as input, but chain `past_key_values` from prior step
   - Record sequence_position, regime label, cumulative token count, processing_mode
6. Store results with temporal metadata

**New Parquet fields in tokens.parquet:**

| Field | Type | Description |
|-------|------|-------------|
| `sequence_position` | int | 0-indexed position in the sequence |
| `cumulative_token_count` | int | Total tokens in KV cache at this point |
| `regime` | str | Which block ("A" or "B") |
| `temporal_run_id` | str | Groups probes from the same temporal run |
| `processing_mode` | str | "expanding_cache_off", "expanding_cache_on", or "single_cache_on" |

**No new Parquet files needed** — routing, embeddings, and residual streams are captured per-probe as usual. The sequence_position provides temporal ordering.

### Frontend Requirements

**New section** in the experiment page, below Latent Space Analysis.

#### Basin Selection Panel
- Two dropdowns (or click-to-select from the Sankey/cluster view): "Basin A" and "Basin B"
- Each shows available clusters (with their label distribution summary, e.g., "C5: 95% roleplay")
- Toggle: cluster-based or expert-based basin indicators
- Sentences per block (number input, default 20)
- Processing mode selector: "Expanding (no cache)" / "Expanding (cached)" / "Single sentence (cached)"
- **"Run Temporal Analysis" button**
- **"Add Run" button** — runs another iteration with different random sentence ordering

#### Primary Visualization: Basin Assignment Over Sequence (the lag chart)

This is the core chart. For each sequence position:
- **X-axis:** sequence position (0, 1, 2, ... 2N)
- **Y-axis:** distance to basin A centroid vs basin B centroid (or simply: which cluster was the probe assigned to)
- **Vertical dashed line** at the regime boundary (position N)
- **Color:** basin A color on left, basin B color on right
- **Lag region:** highlighted area between the regime boundary and when the signal actually flips

**Single run:** one line showing centroid distances or cluster assignment at each position.

**Multiple runs:**
- Each run as a thin semi-transparent line
- **Bold average line** computed across runs
- Shaded confidence band (±1 SD or min/max)

**Scrubber:** slider or step buttons to move through sequence positions. At each position, highlight the current sentence in a side panel (show text, label, which cluster it was assigned to).

#### Lag Metrics Display
- **Routing lag:** first position where cluster assignment flips and stays flipped for 3 consecutive positions
- **Latent lag:** first position where centroid distance to B < distance to A for 3 consecutive positions
- **ΔPersistence:** lag(expanding_cache_on) − lag(expanding_cache_off) — how much cache extends regime persistence
- **Memory-only lag:** lag from single_cache_on — can cached attention alone maintain/shift basins?
- Display as simple stats next to the chart; requires multiple conditions to have been run

#### Controls
- Scrubber: step through sequence positions
- Run selector: toggle individual runs on/off
- Show/hide average line
- Layer selector (which layer's clusters to track)

### Key Questions This Answers

1. How many sentences into a new regime before the model's residual stream shifts basins?
2. Is there measurable lag (confusion between basins) at the regime boundary?
3. Does KV cache amplify persistence? (ΔPersistence > 0)
4. Is the transition symmetric? (A→B lag = B→A lag, or hysteresis?)
5. With many runs, what's the average transition curve? Is it sharp or gradual?

### Evolution Path

**MVP:** Select two clusters → run one A→B sequence → see the lag chart with cluster assignments.

**V2:** Multiple runs with averages, cache ON/OFF comparison, ΔPersistence metric.

**V3:** Expert-based basin indicators alongside cluster-based. Layer cascade analysis (do some layers lag behind others?).

**V4:** Hysteresis testing (A→B vs B→A). Recovery testing (A→B→A).

**Science:** Craft better probes. Test whether basins identified from one probe family (e.g., "threatened") predict basins in another (e.g., "attacked"). Do the same experts/clusters serve as basin indicators across target words?

---

## Feature B: Output Panel

### Motivation

We can see how the model routes and represents "threatened" differently in roleplay vs factual contexts. But we can't see what it would DO with those different representations. The output panel closes the loop: **routing → expert processing → residual stream → predicted next token**.

This answers: do different routing patterns produce different predictions? If a roleplay "threatened" routes through cluster C5 instead of C0, does the model predict different continuation tokens?

### Core Concept

After each forward pass, capture the logits at the target word position (and optionally the final position). Extract the top-k predicted next tokens with softmax probabilities. Store alongside existing probe data. Display in the UI and make available as a color/filter axis.

### Backend Requirements

**Extend `capture_probe()` in `integrated_capture_service.py`:**

Currently: `outputs = self.model(**forward_kwargs)` — logits are discarded.

Change: extract `outputs.logits` at the target word position.

```python
# After forward pass
logits = outputs.logits[0, target_position, :]  # [vocab_size]
probs = torch.softmax(logits, dim=-1)
top_k_probs, top_k_ids = torch.topk(probs, k=10)

# Decode to text
tokenizer = self.adapter.get_tokenizer()
top_k_tokens = [tokenizer.decode([tid]) for tid in top_k_ids.tolist()]
```

**New schema: `OutputPredictionRecord`**

```python
@dataclass
class OutputPredictionRecord:
    probe_id: str
    position: int               # token position (target_word_position)
    position_type: str          # "target_word" or "final"
    top_k_token_ids: List[int]  # [10]
    top_k_tokens: List[str]     # decoded text ["the", "a", "his", ...]
    top_k_probs: List[float]    # [0.23, 0.18, 0.12, ...]
    entropy: float              # prediction entropy (uncertainty)
    top1_token: str             # convenience: most likely next token
    top1_prob: float            # convenience: probability of top prediction
```

**New Parquet file:** `output_predictions.parquet` in session directory.

**Adapter extension:**
- `get_tokenizer()` already exists on adapters
- Add `get_vocab_size() -> int` for validation

**Manifest update:**
- Add `"output_predictions"` to `data_lake_paths`

**API extension:**
- Add predictions to `SessionDetailResponse.sentences` (each ProbeExample gets `top_predictions` field)
- New endpoint: `GET /api/probes/sessions/{session_id}/predictions` — returns full prediction data

### Frontend Requirements

**Output Panel (collapsible section in the experiment page):**

- Shows alongside or below the sentence list
- For each probe/sentence: top-5 predicted next tokens as horizontal bar chart
- Token text + probability bar + percentage
- Color-coded by whether the prediction matches across labels (same prediction = gray, different = highlighted)

**Integration with existing visualizations:**

- **New axis: "prediction"** — available in the Color/Blend dropdowns
  - Values: the set of unique top-1 predictions across all probes
  - Color probes by what the model would predict next
  - Reveals: do probes routed through the same expert predict the same next token?

- **Card panel extension:**
  - When clicking a node/cluster/trajectory, show the prediction distribution for probes in that selection
  - "What does this expert predict?" — aggregate top-1 predictions for all probes routed through that expert

- **Filter by prediction:**
  - Click a predicted token to filter to all probes that share that top-1 prediction
  - Cross-reference with label: "80% of probes predicting 'the' are factual"

**Aggregate view:**
- Prediction distribution per label group (bar chart)
- "Do roleplay and factual 'threatened' predict different next tokens?"
- Prediction entropy comparison: which regime has more confident predictions?

### Key Questions This Answers

1. Do different routing patterns produce different predictions?
2. Is prediction confidence correlated with routing confidence?
3. Do all probes in a residual stream cluster predict the same next token?
4. Is the model more uncertain (higher entropy) for one semantic regime?
5. Can you predict what a sentence's label is from the model's predicted next token alone?

---

## Implementation Order

### Phase 1: Temporal Tab backend (priority — implements the paper's core experiment)
1. Add `sequence_position` / `regime` / `temporal_run_id` fields to ProbeRecord
2. Create temporal capture endpoint with KV cache chaining
3. Accept basin selection (two cluster IDs + layer) from frontend
4. Pull sentences from cluster assignments, build sequence, run capture
5. **Run one temporal capture** on threatened session to verify

### Phase 2: Temporal Tab frontend
1. Basin selection panel (two cluster dropdowns from existing cluster analysis)
2. Lag chart: centroid distance / cluster assignment over sequence position
3. Scrubber to step through positions
4. Multiple runs: "Add Run" button, individual + average lines
5. Lag metrics display

### Phase 3: Output Panel backend
1. Create `OutputPredictionRecord` schema
2. Extend `capture_probe()` to extract logits and compute top-k
3. Add Parquet writer for predictions
4. Update manifest and API responses
5. **Recapture one session** to verify data

### Phase 4: Output Panel frontend
1. Add predictions to sentence list display
2. Add "prediction" as a dynamic axis
3. Extend card panel with prediction details
4. Add aggregate prediction view

### Rationale for this order
- Temporal tab implements the paper's central experiment — it's the scientific priority
- The static analysis already identifies opposing basins clearly (those screenshots!)
- Output panel extends the capture pipeline — useful but not paper-critical
- Both backends are independent; frontends depend on backend data

---

## Open Questions

1. **KV cache memory:** With 40 sentences × ~25 tokens each, the KV cache grows to ~1000 tokens. Is this within gpt-oss-20b's context window? Need to check max_position_embeddings.
2. **Cluster assignments from which run?** Temporal tab needs probe→cluster assignments from a prior static analysis. We need to either save these or recompute them. Currently `probe_assignments` is returned in the API response but not persisted.
3. **Output position:** Should we capture predictions at the target word position only, or also at the final token position? Final position = "what would the model generate next given the full sentence."
4. **Batch recapture:** Adding output predictions to the pipeline means all existing sessions lack prediction data. Do we recapture everything, or make predictions optional/additive?
5. **Temporal sentence count:** How many sentences per block is enough to establish a "regime"? Start with 20 and adjust based on results.
6. **Cross-probe basin validation:** The paper asks whether basins from one probe family predict basins in another. This requires a "basin library" concept — storing identified basins for reuse. Not MVP but shapes the architecture.
