# Multi-Model Design — Concept MRI

*Investigation date: 2026-03-24*

How to support multiple MoE models in the same Concept MRI deployment.

---

## Current State

The adapter pattern is already designed for multiple models. Two adapters exist:

| Adapter | Model | Layers | Experts | Top-K | Hidden | Router Style |
|---------|-------|--------|---------|-------|--------|-------------|
| `GptOssAdapter` | gpt-oss-20b | 24 | 32 | 4 | 2880 | TOPK_THEN_SOFTMAX |
| `OLMoEAdapter` | OLMoE-1B-7B | 16 | 64 | 8 | 2048 | SOFTMAX_THEN_TOPK |

The registry supports multiple aliases per adapter (short name + HuggingFace ID).

### What's Already Model-Agnostic

| Component | Status | Notes |
|-----------|--------|-------|
| Adapter registry | Ready | `get_adapter(key)` returns any registered adapter |
| Session metadata | Ready | `CaptureManifest` stores `model_name` + full topology |
| Data lake | Ready | Session-isolated, model info in manifest |
| Analysis services | Ready | Read topology from manifest, no hardcoded assumptions |
| Frontend | Ready | Completely model-agnostic, displays `model_name` from API |
| Reduction service | Ready | Operates on embeddings regardless of source model |

### What's Hardcoded

**`dependencies.py` line 40** — the critical blocker:
```python
adapter = get_adapter("gpt-oss-20b")  # hardcoded at startup
```

This locks the entire API to one model per process lifetime. The model is loaded into GPU memory during FastAPI startup and never changed.

**Fallback layer counts** in `routing_capture.py` and `integrated_capture_service.py`:
```python
layers_to_capture = adapter.layers_range() if adapter else list(range(24))
```

These fallbacks assume gpt-oss-20b's 24 layers. They only trigger if no adapter is passed, which shouldn't happen in normal operation.

**`.env.example`** defines `MODEL_NAME=ossb20b` but this variable is never read by the code.

---

## Design Decision: How Users Select a Model

### Option A: Environment Variable at Startup (Recommended)

```python
# dependencies.py
model_key = os.getenv("CONCEPT_MRI_MODEL", "gpt-oss-20b")
adapter = get_adapter(model_key)
```

**Pros**: Simple, no API changes, one model loaded = predictable GPU usage.
**Cons**: Requires restart to switch models.

**With Claude Code**: The `/server` skill would accept a model parameter. Claude sets the env var before starting the backend. Users say "start with OLMoE" and Claude handles it.

### Option B: Runtime Model Switching via API

Add an endpoint that unloads the current model and loads a new one:
```
POST /api/models/select  {"model_key": "olmoe-1b-7b"}
```

**Pros**: No restart needed.
**Cons**: Complex — must safely unload GPU memory, reinitialize services, handle in-flight requests. Risk of OOM if unload is incomplete.

### Option C: Multiple Models Loaded Simultaneously

Load all registered models at startup, route requests by parameter.

**Pros**: Instant model switching.
**Cons**: Impossible with current hardware. gpt-oss-20b uses ~15GB VRAM. Loading a second model requires 32GB+ GPU or aggressive quantization.

### Recommendation

**Option A** for now. It's a 5-line change, works with Claude Code's server management, and matches the single-user research workflow. Option B is a future improvement if users frequently switch models within a session.

---

## Data Lake: No Changes Needed

The current structure already works for mixed-model sessions:

```
data/lake/
├── session_abc/              # gpt-oss-20b capture
│   ├── capture_manifest.parquet  ← model_name: "gpt-oss-20b"
│   ├── tokens.parquet
│   ├── routing.parquet           # 24 layers × 32 experts
│   └── embeddings.parquet        # hidden_size: 2880
├── session_xyz/              # OLMoE capture
│   ├── capture_manifest.parquet  ← model_name: "OLMoE-1B-7B"
│   ├── tokens.parquet
│   ├── routing.parquet           # 16 layers × 64 experts
│   └── embeddings.parquet        # hidden_size: 2048
└── _sessions/
    ├── session_abc.json          # model_name in metadata
    └── session_xyz.json
```

Analysis services already read topology from the manifest, so they adapt automatically. The frontend displays whatever the API returns — different layer counts, different expert counts, different Sankey layouts.

No need to partition by model name. Session isolation is sufficient.

---

## Frontend: Model Display

The frontend needs minor additions for a good multi-model experience:

1. **Workspace page**: Show model name next to each session (already in manifest data)
2. **Experiment page header**: Display which model this session was captured with
3. **No model selector needed** — sessions are captured with whatever model the backend loaded

These are cosmetic additions, not architectural changes.

---

## Adding a New Model: Step-by-Step

1. **Create adapter** (`backend/src/adapters/new_model_adapter.py`):
   - Define `ModelTopology` with layer count, expert count, top-K, hidden size
   - Define `ModelCapabilities` with router style, expert style
   - Implement `load_model()`, `get_layer()`, `get_moe_block()`, `get_router()`, `compute_routing_weights()`
   - Register: `register_adapter("new-model", NewModelAdapter)`

2. **Wire model selection** (one-time change):
   - Read `CONCEPT_MRI_MODEL` env var in `dependencies.py`
   - Update `/server` skill to accept model parameter

3. **Test**:
   - Start backend with new model
   - Run a probe capture
   - Verify Sankey visualization renders (different layer/expert counts)
   - Verify analysis endpoints work with new topology

4. **No changes needed** to: data lake, analysis services, frontend, reduction service, clustering.

**Estimated effort**: 2-4 hours for a well-documented model (HuggingFace transformers compatible). The adapter implementation is the bulk of the work — understanding how the new model exposes its MoE routing weights.

---

## Open Questions

- **Comparative analysis**: How should users compare routing patterns across models? Same sentence set, two models, side-by-side Sankeys? This is a UI and analysis design question, not an infrastructure one.
- **Model-specific sentence sets**: Some sentence sets might be designed for models with specific tokenization. Should sentence set metadata include compatible models?
- **Routing weight normalization**: Different router styles produce different weight scales. Are the analysis services robust to this, or do they assume a specific scale?
