# Requirements: Temporal Tab & Output Panel

## Overview

Two new features that extend Concept MRI from static per-sentence analysis to dynamic sequential analysis and close the causal loop from routing to prediction.

**Current state:** Each sentence is processed independently (no KV cache, no shared state). We capture routing decisions, MLP embeddings, and residual streams. We do NOT capture what the model predicts.

**After these features:** We can (A) study how routing evolves when semantic context shifts over a sequence of sentences, and (B) see what the model would output and correlate predictions with routing patterns.

---

## Feature A: Temporal Tab

### Motivation

The existing analysis shows that MoE routing cleanly separates semantic regimes (e.g., roleplay vs factual "threatened" sentences occupy distinct residual stream clusters). But this is static — each sentence is processed in isolation. The temporal tab answers: **what happens when the model has been reading factual text and suddenly encounters roleplay?**

This maps directly to safety-relevant questions: if a model has been processing benign knife usage and then encounters a harmful context, how quickly do the routing patterns shift? Is there inertia? Do some layers lag behind others?

### Core Concept

Sentences are fed sequentially with an expanding KV cache. Each sentence builds on the context of all previous sentences. The capture records the same data (routing, embeddings, residual streams) but indexed by sequence position.

A **regime boundary** is the point where the label switches (e.g., position 20 in a "20 A then 20 B" sequence). The key visualization shows routing patterns before and after the boundary.

### Sequence Configurations

Users define how sentences are ordered:

| Config | Description | Use Case |
|--------|-------------|----------|
| `block_ab` | N sentences of A, then N of B | Clean regime transition |
| `block_ba` | N of B, then N of A | Reverse direction comparison |
| `block_aba` | N of A, N of B, N of A | Recovery/reversion study |
| `interleaved` | Alternating A, B, A, B... | Rapid switching |
| `gradual` | Mostly A → mixed → mostly B | Gradual transition |
| `custom` | User-specified sequence of probe IDs | Full control |

Within each block, sentences are randomly sampled from the corresponding group in the sentence set.

### Backend Requirements

**New endpoint:** `POST /api/experiments/temporal-capture`

```python
class TemporalCaptureRequest(BaseModel):
    sentence_set_name: str
    sequence_config: str          # "block_ab", "block_ba", "block_aba", "interleaved", "gradual", "custom"
    sentences_per_block: int = 20
    layers: Optional[List[int]] = None
    session_name: Optional[str] = None
    custom_sequence: Optional[List[str]] = None  # probe IDs for "custom" mode
```

**Response:** Same as `SentenceExperimentResponse` but with temporal metadata.

**Capture changes:**
- Call `capture_probe()` with `use_cache=True` and chain `past_key_values` between calls
- Already supported: `capture_probe()` accepts `use_cache` and `past_key_values` params
- Add `sequence_position: int` and `cumulative_token_count: int` to each ProbeRecord
- Add `sequence_config` to session manifest metadata

**New Parquet fields in tokens.parquet:**

| Field | Type | Description |
|-------|------|-------------|
| `sequence_position` | int | 0-indexed position in the sequence |
| `cumulative_token_count` | int | Total tokens in KV cache at this point |
| `regime` | str | Which block this position belongs to ("A_0", "B_0", "A_1") |

**No new Parquet files needed** — routing, embeddings, and residual streams are captured per-probe as usual. The sequence_position in tokens.parquet provides the temporal ordering.

### Frontend Requirements

**New section** in the experiment page, below Latent Space Analysis (or as a tab).

**Primary visualization: Temporal Routing Heatmap**
- X-axis: sequence position (0, 1, 2, ... N)
- Y-axis: layers (grouped by window)
- Cell color: expert ID or cluster assignment
- Vertical dashed line at regime boundary
- Hover: show sentence text, label, expert/cluster details

**Secondary visualization: Routing Drift Plot**
- X-axis: sequence position
- Y-axis: routing similarity to regime A centroid (or distance metric)
- One line per layer
- Shows how quickly each layer "switches" after the regime boundary

**Tertiary: Latent Position Over Sequence**
- Reuse SteppedTrajectoryPlot but with sequence position as the stepping axis instead of layer
- Each point is one sentence's residual stream position at a fixed layer
- Shows the cloud drifting from one regime's manifold to the other

**Controls:**
- Sequence config selector (dropdown)
- Sentences per block (number input)
- Layer selection (reuse existing range selector)
- Play/step controls to animate through the sequence

### Key Questions This Answers

1. How many sentences into a new regime before routing flips?
2. Do all layers shift simultaneously or is there a cascade?
3. Is the transition sharp or gradual?
4. Does the model ever "resist" a regime change (routing inertia)?
5. After switching to B, if we switch back to A, does routing return to the original pattern?

---

## Feature B: Output Panel

### Motivation

We can see how the model routes and represents "threatened" differently in roleplay vs factual contexts. But we can't see what it would DO with those different representations. The output panel closes the loop: **routing → expert processing → residual stream → predicted next token**.

This answers: do different routing patterns produce different predictions? If a roleplay "threatened" routes through Expert 5 instead of Expert 0, does the model predict different continuation tokens?

### Core Concept

After each forward pass, capture the logits at the target word position (and optionally the final position). Extract the top-k predicted next tokens with softmax probabilities. Store alongside existing probe data. Display in the UI and make available as a color/filter axis.

### Backend Requirements

**Extend `capture_probe()` in `integrated_capture_service.py`:**

Currently (line 376): `outputs = self.model(**forward_kwargs)` — logits are discarded.

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

### Phase 1: Output Panel backend (can ship independently)
1. Create `OutputPredictionRecord` schema
2. Extend `capture_probe()` to extract logits and compute top-k
3. Add Parquet writer for predictions
4. Update manifest and API responses
5. **Recapture one session** to verify data

### Phase 2: Output Panel frontend
1. Add predictions to sentence list display
2. Add "prediction" as a dynamic axis
3. Extend card panel with prediction details
4. Add aggregate prediction view

### Phase 3: Temporal Tab backend
1. Add `sequence_position` / `regime` fields to ProbeRecord
2. Create temporal capture endpoint with KV cache chaining
3. Add sequence configs (block_ab, interleaved, etc.)
4. **Run temporal capture** on one sentence set to verify

### Phase 4: Temporal Tab frontend
1. Temporal routing heatmap (sequence position x layer)
2. Routing drift plot
3. Temporal latent trajectory view
4. Sequence controls and animation

### Rationale for this order
- Output panel is simpler (extends existing capture, no new model interaction patterns)
- Output panel data is useful immediately (adds context to all existing visualizations)
- Temporal tab requires more design thought around KV cache management and sequence UI
- Both backends can be developed independently; frontends depend on backend data

---

## Open Questions

1. **KV cache memory:** With 40 sentences × ~25 tokens each, the KV cache grows to ~1000 tokens. Is this within gpt-oss-20b's context window? Need to check max_position_embeddings.
2. **Temporal session reuse:** Should temporal sessions be compatible with existing analysis (expert routes, latent space) or a separate analysis mode?
3. **Output position:** Should we capture predictions at the target word position only, or also at the final token position? Final position = "what would the model generate next given the full sentence."
4. **Batch recapture:** Adding output predictions to the pipeline means all existing sessions lack prediction data. Do we recapture everything, or make predictions optional/additive?
5. **Temporal sentence count:** How many sentences per block is enough to establish a "regime"? Need to experiment — start with 20 and adjust.
