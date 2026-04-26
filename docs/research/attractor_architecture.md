# Open LLMRI v2 — Architecture & Implementation Plan

## Context

Open LLMRI is a **general-purpose MoE interpretability tool** with three analysis modes. It captures routing and embedding data for any text input with target token tracking, and each tab provides a different analytical lens on that data.

The attractor paper experiment (Role Stickiness) is one use case — the Temporal tab — but the software serves broader MoE analysis needs.

## Model: OLMoE-1B-7B

| Property | Value |
|----------|-------|
| HuggingFace ID | `allenai/OLMoE-1B-7B` |
| Layers | 16 |
| Experts per layer | 64 |
| Top-K routing | K=8 |
| Hidden size | 2048 |
| Total params | ~6.9B |
| Active params | ~1.3B per token |
| VRAM (fp16) | ~14GB |
| License | Apache 2.0 |

---

## Model Adapter Abstraction

The current system hardcodes model-specific paths (ossb20b module paths, 24 layers, 32 experts, K=4, 2880 hidden dim). To avoid repeating this with OLMoE, we introduce a `ModelAdapter` that encapsulates all model-specific details. Switching models = write a new adapter subclass.

### What varies between MoE models
- **Module paths**: where the MoE block, router/gate, experts live (`layer.mlp` vs `layer.block_sparse_moe`, `moe.router` vs `moe.gate`)
- **Router computation**: softmax→topk (OLMoE, Mixtral) vs topk→softmax (ossb20b)
- **Expert structure**: individual `nn.ModuleList` (OLMoE) vs fused collective module (ossb20b quantized)
- **Architecture constants**: layers, experts, hidden_size, top_k
- **Loading requirements**: dtype, quantization, trust_remote_code
- **Router bias**: some have it (ossb20b), some don't (OLMoE)

### File structure — `backend/src/adapters/`

```
adapters/
  __init__.py
  base_adapter.py       # ModelAdapter ABC, ModelTopology, ModelCapabilities
  registry.py           # Adapter registry + auto-registration
  olmoe_adapter.py      # OLMoEAdapter
  gptoss_adapter.py     # GptOssAdapter (backward compat)
```

### ModelTopology (frozen dataclass)
```python
num_layers: int          # 16 for OLMoE, 24 for ossb20b
num_experts: int         # 64 for OLMoE, 32 for ossb20b
top_k: int               # 8 for OLMoE, 4 for ossb20b
hidden_size: int         # 2048 for OLMoE, 2880 for ossb20b
model_name: str          # Human-readable name for manifests
model_id: str            # HuggingFace model ID
```

### ModelCapabilities (frozen dataclass)
```python
has_individual_experts: bool     # Can hook individual expert modules
has_shared_experts: bool         # DeepSeek-MoE style shared experts
has_router_bias: bool            # Router has bias parameter
router_style: RouterStyle        # SOFTMAX_THEN_TOPK or TOPK_THEN_SOFTMAX
expert_style: ExpertStyle        # INDIVIDUAL or COLLECTIVE
```

### ModelAdapter ABC — abstract methods
```python
# Properties
topology -> ModelTopology
capabilities -> ModelCapabilities

# Loading
load_model(model_path, device_map) -> (model, tokenizer)

# Module resolution (used by hook registration)
get_layer(model, layer_idx) -> nn.Module
get_moe_block(layer) -> nn.Module
get_router(moe_block) -> nn.Module
get_experts_module(moe_block) -> nn.Module

# Router computation (used by hooks)
compute_routing_weights(moe_block, hidden_states) -> Tensor [batch, seq, num_experts]
```

### How it's used

**Hook registration** (`routing_capture.py`):
```python
# Before (hardcoded):
layer = self.model.model.layers[layer_idx]
layer.mlp.register_forward_hook(...)
router_logits = F.linear(hidden_states, module.router.weight, module.router.bias)

# After (adapter-driven):
layer = self.adapter.get_layer(self.model, layer_idx)
moe_block = self.adapter.get_moe_block(layer)
moe_block.register_forward_hook(...)
routing_weights = self.adapter.compute_routing_weights(moe_block, hidden_states)
```

**Model loading** (`dependencies.py`):
```python
adapter = get_adapter("olmoe-1b-7b")  # from registry
model, tokenizer = adapter.load_model(model_path)
capture_service = IntegratedCaptureService(model, tokenizer, adapter=adapter, ...)
```

**Schema validation** — schemas become plain data containers. Validation uses `adapter.topology` for bounds (not hardcoded `<= 23`, `<= 31`).

### Hardcoded locations to fix (from codebase audit)
- `routing_capture.py`: module paths, `F.linear(...)` routing, `k=4`
- `integrated_capture_service.py`: `list(range(24))`, `model_name="gpt-oss-20b"`
- `dependencies.py`: model path, loading args, `list(range(24))`
- `routing.py`: `<= 23`, `<= 31`, `np.log(32)`, `shape[0] != 32`
- `expert_internal_activations.py`: `<= 23`, `<= 31`
- `expert_output_states.py`: `<= 23`
- `pca_generation_service.py`: `range(24)`, `2880`
- `capture_manifest.py`: `model_name="gpt-oss-20b"`

---

## Software Design: Three Tabs, One Capture System

### Unified Capture Layer

The core change: generalize from "2 tokens" to "any text + target token."

The capture takes:
- **Text**: any length (a word pair, a sentence, a paragraph)
- **Target word**: the token to analyze (e.g., "tank", "said", "knife")
- **Metadata**: categories, labels, whatever the experiment needs

It captures (at the target token position, across all layers):
- Top-K routing decisions (expert IDs, weights, gate entropy)
- Residual stream embedding (2048D for OLMoE)
- MLP/expert output states

All three tabs read from the same captured data. The difference is how they slice it.

### Tab 1: Expert Analysis (exists, evolve)

**Purpose**: Understand expert routing patterns — which experts activate for which tokens, how routing flows across layers.

**Input**: A session of captured probes (text + target word, any length)

**Controls**:
- Session selector
- Category filter panel (checkboxes by category, select all/clear)
- Layer range selector (4 ranges covering layers 0-15)
- Color axis selector (primary + optional secondary)
- Balanced sampling toggle
- Max routes / show-all toggle

**Visualizations**:
- **Sankey diagrams** (MultiSankeyView) — 6 consecutive layer-transition Sankeys per range, colored by category
- **Expert specialization tables** — which experts handle which categories
- **Highway identification** — common multi-layer routing paths
- **Route details panel** — click a route to see which tokens use it

**What changes**: Generalizes from 2-token probes to any text length. Same visualizations, same coloring. The only backend change is the capture now accepts longer text.

### Tab 2: Latent Space Analysis (exists, evolve)

**Purpose**: Understand how tokens move through representation space — manifold structure, clustering, trajectories.

**Input**: Same session of captured probes

**Controls**:
- Session selector
- Category filter panel
- Layer selection
- **Dimensionality reduction method**: PCA or UMAP (selectable)
- **Clustering method**: k-means, hierarchical, DBSCAN (selectable, as now)
- Number of components / PCA variance threshold

**Visualizations**:
- **3D stepped trajectory plot** — shows how target token embeddings move through reduced space layer by layer (works with PCA or UMAP)
- **Clustering view** — how tokens cluster by category at each layer
- **Centroid distance analysis** — between-category separation per layer
- **Silhouette scores** — within-cluster cohesion

**What changes**: Add UMAP as an option alongside PCA. Same trajectory visualization, same clustering — just selectable reduction method. Generalizes to any text length.

### Tab 3: Temporal / Attractor Analysis (new)

**Purpose**: Analyze how routing-representation regimes persist and transition over ordered sequences of sentences. This is the paper's experiment.

**Input**: A temporal experiment — ordered sequences of sentences with regime labels, processed using standard autoregressive operation (expanding context).

**Controls**:
- Experiment selector
- Sequence selector (pick which sequence to inspect)
- Layer selector (auto-suggested best layer, manually overridable)
- Expert selector (auto-suggested characteristic experts, manually overridable)

**Visualizations**:

1. **Expert Activation Heatmap** — rows = experts (or top-N experts), columns = sequence positions, color = activation weight. Shows the full temporal picture at a glance. Regime labels color-coded along the x-axis.

2. **Sankey Scrubber** — one Sankey diagram that updates as you drag a slider through sequence positions. Shows routing at any specific point. Lets you see routing before, during, and after the regime transition.

3. **Lag Plot** — dual time-series chart:
   - Top: characteristic expert activation across sequence positions
   - Bottom: target token distance to regime centroids across sequence positions
   - Vertical line marks transition point
   - Shaded regions show stabilization thresholds

4. **Regime Timeline** — horizontal bar showing A/B labels color-coded, with transition point marked. Serves as navigation — click to jump the scrubber.

5. **Metrics Summary Panel** — routing lag, latent lag, joint lag with confidence intervals. Layer ranking table. Expert discrimination table.

**Unique features**:
- Ordered sequences of sentences (not a bag of probes)
- Expanding context (standard autoregressive — full history always available)
- Temporal metadata (regime label, transition step, sequence position)
- Lag metrics (routing lag, latent lag, joint lag)
- Auto-analysis (best layer, characteristic experts) with manual override

---

## Data Flow

```
USER INPUT
  |
  +-- Expert/Latent tabs: text + target word + categories -> create session -> run probes
  |
  +-- Temporal tab: sentence sets + experiment config -> build sequences -> run experiment
  |
  v
UNIFIED CAPTURE (forward pass, hooks)
  |
  +-- Routing data: top-K experts, weights, entropy per layer at target token
  +-- Embeddings: 2048D residual stream per layer at target token
  +-- Metadata: text, target word, categories, (temporal: regime, position)
  |
  v
PARQUET STORAGE (same schemas for all tabs)
  |
  v
TAB-SPECIFIC ANALYSIS
  |
  +-- Expert tab: route analysis -> Sankey data
  +-- Latent tab: PCA/UMAP reduction -> trajectories, clustering
  +-- Temporal tab: layer selection, expert finding, lag metrics -> temporal plots
  |
  v
API -> FRONTEND VISUALIZATIONS
```

### Two-Dataset Design

Each attractor experiment produces **two probe datasets** from the same sentence set. Both are captured from the Probes page. The three analysis tabs are **read-only** — they select which dataset to analyze.

**1. Individual Sentences Dataset**
Each sentence is fed to the model independently (no context accumulation, no KV cache chaining between sentences). This produces one probe per sentence. Used in:
- **Expert tab** (routing basins) — identifies distinct routing regimes for the target word across regime-A vs regime-B sentences
- **Latent tab** (representation basins) — identifies distinct embedding clusters, confirms A and B form separable attractors

**2. Expanding Text Dataset**
Standard autoregressive processing with KV cache. Sentences are fed one at a time, context expands sentence by sentence (A1, then A1+A2, then A1+A2+A3, ..., then A1...A20+B1, etc.). This produces one probe per step. Used in:
- **Temporal tab** (lag, hysteresis, regime transitions) — measures how the model transitions between the basins identified in the individual sentences dataset

The individual sentences dataset establishes *that* distinct basins exist. The expanding text dataset measures *how* the model moves between them over time.

Both datasets link to the same `ExperimentManifest` via `individual_session_id` and `temporal_session_id` fields.

---

## Phase 1: Model Adapter + Model Setup

### 1a. Create ModelAdapter abstraction
1. Create `backend/src/models/` package
2. Implement `base_adapter.py` — `ModelAdapter` ABC, `ModelTopology`, `ModelCapabilities`, enums
3. Implement `registry.py` — adapter registry with `get_adapter()`, `register_adapter()`, `list_available_models()`
4. Implement `olmoe_adapter.py` — `OLMoEAdapter` with all OLMoE-specific paths and computation
5. Implement `gptoss_adapter.py` — `GptOssAdapter` for backward compatibility

### 1b. OLMoE Module Structure (for hooks)
```
OlmoeForCausalLM
  +-- model (OlmoeModel)
        +-- layers (nn.ModuleList of OlmoeDecoderLayer)
              +-- [i] (OlmoeDecoderLayer)
                    +-- self_attn
                    +-- mlp (OlmoeSparseMoeBlock)
                    |     +-- gate (nn.Linear, hidden_size -> num_experts)  <- ROUTER
                    |     +-- experts (nn.ModuleList of 64 OlmoeMLP)
                    |           +-- [j] (OlmoeMLP)
                    |                 +-- gate_proj
                    |                 +-- up_proj
                    |                 +-- down_proj
                    +-- input/post_attention layernorms
```

**Hook targets for capture:**
- `model.model.layers[i].mlp` — hook on MoE block output (captures combined expert output = residual stream contribution)
- `model.model.layers[i].mlp.gate` — hook to capture router logits before softmax/topk (raw routing weights)

**Router computation** (inside OlmoeSparseMoeBlock.forward):
1. `router_logits = self.gate(hidden_states)` -> [batch, seq, 64]
2. `routing_weights = softmax(router_logits)`
3. `top_k_weights, top_k_indices = topk(routing_weights, k=8)`
4. Selected experts process tokens, outputs weighted-summed

### 1c. Setup tasks
1. Download `allenai/OLMoE-1B-7B` (or `-0924` / `-0125` variant, ~14GB fp16)
2. Update `backend/src/api/dependencies.py`:
   - Accept model key (default `"olmoe-1b-7b"`)
   - Use `get_adapter(model_key)` to get adapter
   - Use `adapter.load_model()` for model loading
   - Use `adapter.layers_range()` for layers_to_capture
   - Pass adapter to `IntegratedCaptureService` and `EnhancedRoutingCapture`
3. Verify "said" tokenizes to a single token with OLMoE tokenizer
4. Test hook registration via adapter methods
5. Test forward pass, verify hooks capture routing_weights [batch, seq, 64] and MLP output [batch, seq, 2048]

---

## Phase 2: Generalize Capture System

### 2a. Evolved Schemas

We evolve the existing schemas in place (breaking changes are OK).

**ProbeRecord** (replaces `TokenRecord` in `backend/src/schemas/tokens.py`):
```
probe_id: str                  # Unique per capture
session_id: str                # Groups related probes
input_text: str                # Full text (was context_text, now any length)
target_word: str               # The word we're tracking (was target_text)
target_token_id: int           # Token ID from tokenizer
target_token_position: int     # Index in tokenized input (was always 0 or 1)
total_tokens: int              # Total tokens in input (new)
categories_json: str           # JSON-serialized dict, e.g. '{"structure": "action", "intensity": "medium", "topic": "culinary"}'
created_at: str

# Optional temporal fields (null for Expert/Latent tabs, set for Temporal tab):
experiment_id: Optional[str]
sequence_id: Optional[str]
sentence_index: Optional[int]
regime_label: Optional[str]
transition_step: Optional[int]
```

**RoutingRecord** (replaces existing in `backend/src/schemas/routing.py`):
```
probe_id: str                  # Links to ProbeRecord
layer: int                     # 0-15 for OLMoE
token_position: int            # KEPT -- target token position (for query compatibility)
routing_weights: List[float]   # Full probability vector (length = num_experts, e.g. 64)
num_experts: int               # Self-describing (64 for OLMoE)
expert_top1_id: int            # Convenience: argmax of routing_weights
expert_top1_weight: float      # Max routing weight
gate_entropy: float
captured_at: str
```
`token_position` KEPT (not removed) -- existing analysis code filters on it (~5 locations).
`expert_top4_ids/weights` removed -- replaced by full `routing_weights`. Top-K computed on the fly.

**EmbeddingRecord** (replaces `ExpertOutputState` in `backend/src/schemas/expert_output_states.py`):
```
probe_id: str                  # Links to ProbeRecord
layer: int
embedding: np.ndarray          # Residual stream at target position (2048D for OLMoE)
embedding_dims: Tuple[int, ...]
captured_at: str
```
No `token_position` field -- always target token.
Renamed from ExpertOutputState -> EmbeddingRecord (clearer name).

**CaptureManifest** (evolves `backend/src/schemas/capture_manifest.py`):
```
session_id: str
session_name: str
model_name: str
num_experts: int               # Model's expert count (64 for OLMoE)
num_layers: int                # Model's layer count (16 for OLMoE)
hidden_size: int               # Model's hidden dim (2048 for OLMoE)
probe_count: int
category_axes: List[str]       # What category dimensions exist, e.g. ["structure", "intensity", "topic"]
created_at: str
```

**ExperimentManifest** (new, for Temporal tab only):
```
experiment_id: str
experiment_name: str
target_word: str
regime_a_label: str
regime_b_label: str
sequence_configs: List[Dict]   # [{type, a_count, b_count}, ...]
total_sequences: int
total_probes: int
model_name: str
sentence_set_source: str
created_at: str
```

**Kept schemas** (with modifications):
- `PCAFeatureRecord` -> evolve to `ReductionFeatureRecord` -- add `method` field ("pca" or "umap"). Keep 128D output. Used by cluster_route_analysis.py.

**Removed schemas:**
- `ExpertInternalActivation` -- removed. Schema file deleted, all write calls and references removed from capture service and API router.

### 2a-note. Migration Impact

Code review found ~30+ field access sites that need updating across 3 backend services:
- `expert_route_analysis.py` -- ~10 refs to `context_text`/`target_text`
- `cluster_route_analysis.py` -- ~15 refs to `context_text`/`target_text`
- `integrated_capture_service.py` -- schema creation calls

The API response contract (frontend types) does NOT break -- services transform data before returning.
Existing Parquet files will be incompatible -- fresh captures needed after migration.

### 2b. Evolve Capture Service

**IntegratedCaptureService** (`backend/src/services/probes/integrated_capture_service.py`):

Key changes:
- Remove single-token validation
- New method: `find_target_token_position(token_ids, target_word, text)` -- locates target in tokenized input
- `capture_single_pair()` -> `capture_probe(input_text, target_word, categories, ...)` -- generalized
- Only extract and store data at the target token position (not all positions)
- Session creation simplified: takes a list of (text, target_word, categories) tuples instead of Cartesian product of word lists
- Backward compatible: `capture_probe("the cat", "cat", ...)` still works for 2-token experiments

For the Temporal tab, the TemporalExperimentRunner calls `capture_probe()` in a loop, managing KV cache externally.

### 2c. Evolve Hook System

**EnhancedRoutingCapture** (`backend/src/services/probes/routing_capture.py`):

Now takes a `ModelAdapter` instead of using hardcoded paths.

**Key changes:**
- Constructor: `__init__(self, model, adapter: ModelAdapter, layers_to_capture=None)`
- `register_hooks()` uses `adapter.get_layer()`, `adapter.get_moe_block()` for module resolution
- MoE combined hook uses `adapter.compute_routing_weights(module, hidden_states)` instead of manual `F.linear(...)`
- Top-K uses `adapter.topology.top_k` instead of hardcoded `k=4`
- `num_experts` from `adapter.topology.num_experts` instead of hardcoded
- Entropy normalization uses `np.log(adapter.topology.num_experts)` instead of `np.log(32)`
- Store full routing weights (softmax of router output) instead of top-4
- Hooks capture all positions; capture service reads only target position

---

## Phase 3: Sentence Generation (for Temporal tab)

### 3a. SentenceSet data model -- `backend/src/services/generation/sentence_set.py`
- `SentenceEntry`: text, regime, target_word, char_span
- `SentenceSet`: version, target_word, regime descriptions, sentences_a[], sentences_b[], validation

### 3b. Pre-generated sentence sets -- `data/sentence_sets/`
Sentence sets organized by category: polysemy (tank), safety (knife/gun/hammer/rope), role_framing (said_roleframing, said_safety, attacked, destroyed, threatened). Each sentence has a `categories` dict with generic axes. See `data/sentence_sets/GUIDE.md` for full schema, categories, and confound analysis.

### 3c. LLM generation service -- `backend/src/services/generation/sentence_generator.py`
User-supplied API key, structured prompts, validation.

---

## Phase 4: Temporal Experiment Orchestration (for Temporal tab)

### 4a. SequenceBuilder -- `backend/src/services/experiments/sequence_builder.py`

Builds ordered sequences of sentences from a SentenceSet.

**Full experiment** (from firstexperiment.md):
- 10 sequences of 20A -> 20B (transition A->B)
- 10 sequences of 20B -> 20A (transition B->A)
- 5 control sequences of 40A (no transition)
- 5 control sequences of 40B (no transition)
- Total: 30 sequences x 40 sentences = 1200 captures (standard autoregressive processing)

Each sequence samples sentences from the set (varied, without replacement where possible).

### 4b. TemporalExperimentRunner -- `backend/src/services/experiments/temporal_experiment_runner.py`

Processes each sequence using standard autoregressive operation: sentences added one at a time, context expands. At every step, capture routing + embedding for "said" in the current sentence.

---

#### EXPERIMENT MECHANICS

**The question:**
When the model has been processing 20 narrative (A) sentences and then switches to factual (B) sentences, how quickly does its internal state (routing + embeddings) shift to match the new regime?

**The setup:**
A sequence of 40 sentences: A1, A2, ... A20, B1, B2, ... B20.
Process them in order. At each step, capture routing and embedding for "said."
This is standard autoregressive LLM operation -- the context expands as you go.

**Step-by-step (expanding context):**

```
Step 0:  model sees: A1                              | capture "said" in A1
Step 1:  model sees: A1, A2                          | capture "said" in A2
Step 2:  model sees: A1, A2, A3                      | capture "said" in A3
...
Step 19: model sees: A1, A2, ..., A20                | capture "said" in A20
Step 20: model sees: A1, A2, ..., A20, B1            | capture "said" in B1  <-- TRANSITION
Step 21: model sees: A1, A2, ..., A20, B1, B2        | capture "said" in B2
...
Step 39: model sees: A1, A2, ..., A20, B1, ..., B20  | capture "said" in B20
```

After the transition at step 20, all 20 A sentences remain in context. The model always has its full history available. The question is: does the A-regime routing/representation persist into the B section, and for how long?

**KV cache is just an optimization:**
These two implementations produce identical results:

```python
# Option A: Feed growing input from scratch each step (simple, slower)
for i, sentence in enumerate(sequence):
    full_text = " ".join([s.text for s in sequence[:i+1]])
    tokens = tokenizer(full_text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(tokens.input_ids, use_cache=False)
    target_pos = find_target_position(tokens.input_ids[0], sentence, "said")
    extract_routing_and_embedding(target_pos)

# Option B: Feed one sentence at a time with KV cache (efficient, same result)
past_kv = DynamicCache()
for i, sentence in enumerate(sequence):
    tokens = tokenizer(sentence.text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(tokens.input_ids, past_key_values=past_kv, use_cache=True)
    past_kv = outputs.past_key_values
    target_pos = find_target_position(tokens.input_ids[0], "said")
    extract_routing_and_embedding(target_pos)
```

We use Option B for efficiency (avoids reprocessing A1..A19 at every step). But the hidden states, routing, and embeddings are mathematically identical to Option A.

**What we measure:**
At each step, for the target token "said" in the current sentence:
- Routing: which experts activate, with what weights (across all 16 layers)
- Embedding: the residual stream vector (2048D, across all 16 layers)

**What we expect:**
- Steps 0-19 (pure A): stable A-regime routing and embedding patterns
- Step 20 (first B sentence): routing/embedding may still look A-like (lag)
- Steps 21-39: gradual shift toward B-regime patterns
- The number of steps before routing/embedding stabilize in B-regime = the lag

**Why this is cleaner than a sliding window approach:**
- Full history is always available -- matches how LLMs actually work in practice
- No artificial context truncation
- No complexity with finding "said" among multiple window occurrences
- Simpler to implement and explain

#### OLMoE model properties relevant to the experiment

| Property | Value | Why it matters |
|----------|-------|----------------|
| Cache type | DynamicCache | Grows as we feed sentences -- no pre-allocation needed |
| Position handling | RoPE (automatic) | No manual position_ids tracking between sentences |
| Model attention | Full attention | Model attends to ALL prior tokens, not just recent ones |
| Max context | 4096 tokens | 40 sentences x ~15 tokens = ~600 tokens -- well within limit |
| Hook behavior with cache | New tokens only | Hooks see `[1, new_count, 2048]`, not the full cached sequence |

**Memory management:**
- KV cache: 16 layers x 2(K+V) x 16 heads x 128 head_dim x 600 tokens x 2 bytes = ~75MB. Fine.
- Clear cache + GPU memory between sequences using `memory_utils.cleanup_gpu_memory()`.

### 4c. Capture Integration

The capture service needs a `past_key_values` parameter for efficient autoregressive processing:
- `capture_probe(sentence_text, target_word, past_key_values=cache, use_cache=True, ...)`
- Returns `(probe_id, updated_past_key_values)` so the runner can chain calls.

Each call feeds one new sentence, the cache provides all prior context.

---

## Phase 5: Analysis Pipeline

### For Latent tab (evolve existing):
- **DimensionalityReductionService** -- Selectable: PCA or UMAP.
  - PCA: existing approach (retain >=80% variance, 128D output)
  - UMAP: n_neighbors, min_dist, n_components as parameters
  - Both produce reduced embeddings stored as ReductionFeatureRecord

### For Temporal tab (new):

**LayerSelectorService** -- `backend/src/services/analysis/layer_selector.py`

Uses pure-regime data (controls + pre-transition sentences) to find best A/B separation layer.

Per layer (0-15): collect embeddings -> PCA reduce -> centroid distance + silhouette score.
Returns ranked layer list. Recommends best layer.

**CharacteristicExpertFinder** -- `backend/src/services/analysis/characteristic_experts.py`

Per layer: compare top-1 routing frequencies between pure-A and pure-B.
Per expert: compute proportion difference (A probes vs B probes that route to it).
Returns: per-layer strongest A-expert and B-expert.

**LagMetricsService** -- `backend/src/services/analysis/lag_metrics.py`

At selected best layer, for each transition sequence:

*Routing lag*: Track B-characteristic expert's routing weight across post-transition steps.
B-baseline = mean +/- SD from pure-B probes.
Lag = first step within 1 SD of B-baseline for 2 consecutive steps.

*Latent lag*: Track embedding projection onto A->B centroid axis (0=A, 1=B).
Lag = first step >= 0.8 projection for 2 consecutive steps.

*Joint lag* = max(routing_lag, latent_lag).

*Aggregation*: Per-sequence values -> mean +/- 95% CI across sequences.

**TemporalReductionService** -- `backend/src/services/analysis/temporal_pca.py`

Fit PCA/UMAP on all embeddings at selected layer -> project per-step embeddings -> return ordered trajectories per sequence.

---

## Phase 6: API Endpoints

- Evolve existing probe endpoints to support any-length text
- Add temporal experiment endpoints (create, status, results, lag-metrics, trajectories)
- Add sentence generation endpoints

---

## Phase 7: Frontend

### Navigation: Three top-level tabs
- Expert Analysis | Latent Space | Temporal Analysis

### Expert tab (evolve existing ExperimentPage):
- Same MultiSankeyView, same category filtering, same coloring
- Generalize probe creation to accept any-length text + target word
- No major visual changes

### Latent tab (evolve existing ExperimentPage PCA mode):
- Add reduction method selector (PCA / UMAP)
- Same 3D stepped trajectory plot (works with either reduction)
- Same clustering views
- Add centroid distance and silhouette display

### Temporal tab (new page):
Components needed:
- **TemporalExperimentPage** -- main page
- **ExpertHeatmap** -- experts x sequence positions heatmap (ECharts)
- **SankeyScrubber** -- Sankey + slider for scrubbing sequence positions
- **LagPlot** -- dual time-series (expert activation + centroid distance)
- **RegimeTimeline** -- clickable A/B color bar
- **MetricsSummaryPanel** -- lag numbers + CI + layer/expert tables
- **ExperimentConfigPanel** -- set up and run experiments

---

## Component Status

### Schemas -- `backend/src/schemas/`

| Component | File | Status |
|-----------|------|--------|
| ProbeRecord (replaces TokenRecord) | `tokens.py` | done |
| RoutingRecord (evolve) | `routing.py` | done |
| EmbeddingRecord (replaces ExpertOutputState) | `embedding.py` | done |
| CaptureManifest (evolve) | `capture_manifest.py` | done |
| ExperimentManifest (new) | `experiment_manifest.py` | done |
| ReductionFeatureRecord (evolve PCAFeatureRecord) | `pca_features.py` | todo |

### Capture -- `backend/src/services/probes/`

| Component | File | Status |
|-----------|------|--------|
| IntegratedCaptureService (evolve) | `integrated_capture_service.py` | done |
| EnhancedRoutingCapture (evolve for OLMoE) | `routing_capture.py` | done |

### Sentence Generation -- `backend/src/services/generation/`

| Component | File | Status |
|-----------|------|--------|
| SentenceSet data model | `sentence_set.py` | todo |
| SentenceGenerator (LLM) | `sentence_generator.py` | todo |
| Pre-generated sentences | `data/sentence_sets/role_stickiness_v1.json` | todo |

### Experiment Orchestration -- `backend/src/services/experiments/`

| Component | File | Status |
|-----------|------|--------|
| SequenceBuilder | `sequence_builder.py` | todo |
| TemporalExperimentRunner | `temporal_experiment_runner.py` | todo |

### Analysis -- `backend/src/services/analysis/`

| Component | File | Status |
|-----------|------|--------|
| LayerSelectorService | `layer_selector.py` | todo |
| CharacteristicExpertFinder | `characteristic_experts.py` | todo |
| LagMetricsService | `lag_metrics.py` | todo |
| TemporalReductionService | `temporal_pca.py` | todo |
| DimensionalityReductionService (PCA+UMAP) | `dimensionality_reduction.py` | todo |

### API -- `backend/src/api/routers/`

| Component | File | Status |
|-----------|------|--------|
| Temporal experiments router | `temporal_experiments.py` | todo |
| Generation router | `generation.py` | todo |

### Frontend

| Component | File | Status |
|-----------|------|--------|
| TemporalExperimentPage | `frontend/src/pages/TemporalExperimentPage.tsx` | todo |
| ExpertHeatmap | `frontend/src/components/charts/ExpertHeatmap.tsx` | todo |
| SankeyScrubber | `frontend/src/components/charts/SankeyScrubber.tsx` | todo |
| LagPlot | `frontend/src/components/charts/LagPlot.tsx` | todo |
| RegimeTimeline | `frontend/src/components/charts/RegimeTimeline.tsx` | todo |
| MetricsSummaryPanel | `frontend/src/components/MetricsSummaryPanel.tsx` | todo |
| ExperimentConfigPanel | `frontend/src/components/ExperimentConfigPanel.tsx` | todo |

### Infrastructure (Modify Existing)

| Component | File | Status |
|-----------|------|--------|
| Model loading (OLMoE) | `backend/src/api/dependencies.py` | todo |
| Register new routers | `backend/src/api/main.py` | todo |
| Hook targets for OLMoE | `backend/src/services/probes/routing_capture.py` | todo |
| Field migration in expert_route_analysis | `backend/src/services/experiments/expert_route_analysis.py` | todo |
| Field migration in cluster_route_analysis | `backend/src/services/experiments/cluster_route_analysis.py` | todo |
| Field migration in pca_generation_service | `backend/src/services/features/pca_generation_service.py` | todo |

---

## Implementation Order

1. **ModelAdapter abstraction** — `backend/src/models/` package (base_adapter, registry, olmoe_adapter, gptoss_adapter)
2. **Model setup** — wire adapter into dependencies.py, download OLMoE, verify hooks via adapter
3. **Generalize capture system** — schemas + services, using adapter.topology for all model-specific values
4. **Verify existing Expert + Latent tabs** work with generalized capture
5. **Sentence generation** + pre-generated set
6. **Temporal experiment orchestration**
7. **Analysis pipeline**
8. **API endpoints**
9. **Frontend** (Temporal tab)

---

## Experiment Design Summary

From firstexperiment.md:

- **Regimes**: A = narrative/medieval fantasy, B = factual/assistant
- **Target token**: "said"
- **Sentences**: 100 per regime, each containing "said" exactly once, plus ~20 neutral controls
- **Transition sequences**: 10x (20A->20B), 10x (20B->20A)
- **Controls**: 5x 40A, 5x 40B
- **Processing**: Standard autoregressive (expanding context, KV cache for efficiency)
- **Metrics**: routing lag, latent lag, joint lag
- **Success criteria**: A/B separate in latent space, distinguishable routing, delayed transition after regime switch

---

## Verification Checklist

1. `get_adapter("olmoe-1b-7b")` returns OLMoEAdapter with correct topology/capabilities
2. `adapter.load_model()` loads OLMoE, forward pass works
3. Hooks registered via adapter capture routing_weights [batch, seq, 64] and embedding [batch, seq, 2048]
4. "said" is a single token in OLMoE tokenizer
5. Existing Expert/Latent analysis still works after capture generalization
6. Small temporal experiment (3A->3B) runs with autoregressive processing
7. Full experiment produces lag metrics
8. Switching adapter to `"gpt-oss-20b"` still works (backward compat)
