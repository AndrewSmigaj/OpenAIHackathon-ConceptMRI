# Open LLMRI — Backend

FastAPI server that captures MoE routing patterns and provides analysis endpoints.

## Architecture

```
api/
├── main.py              # FastAPI app, lifespan (model loading), CORS, health endpoint
├── dependencies.py      # Service initialization and dependency injection
├── schemas.py           # Pydantic request/response models
└── routers/
    ├── probes.py        # Session management, probe capture, clustering schemas
    ├── experiments.py   # Route analysis, cluster analysis, temporal capture, LLM insights
    ├── generation.py    # Sentence set listing and generation
    └── prompts.py       # Scaffold template delivery

adapters/
├── base_adapter.py      # ModelAdapter ABC — abstracts model-specific behavior
├── gptoss_adapter.py    # gpt-oss-20b: 24 layers, 32 experts, top-4, TOPK_THEN_SOFTMAX
├── olmoe_adapter.py     # OLMoE-1B-7B: 16 layers, 64 experts, top-8, SOFTMAX_THEN_TOPK
└── registry.py          # Adapter registration and lookup

services/
├── probes/
│   └── integrated_capture_service.py  # Session management, model inference, Parquet I/O
├── experiments/
│   ├── expert_route_analysis.py       # Expert-level routing analysis (Sankey data)
│   ├── cluster_route_analysis.py      # Cluster-level routing analysis (after UMAP/PCA)
│   ├── output_category_nodes.py       # Build output layer nodes from categorized probes
│   ├── category_axis_analyzer.py      # Dynamic axis detection from session data
│   └── llm_insights_service.py        # Optional LLM-powered analysis (user API key)
├── features/
│   └── reduction_service.py           # PCA/UMAP dimensionality reduction
└── generation/
    └── sentence_set.py                # Load and validate sentence set JSON files

schemas/                  # Parquet data contracts (Pydantic models)
├── tokens.py            # ProbeRecord — input text, label, generated output
├── routing.py           # RoutingRecord — per-layer expert routing weights
├── embedding.py         # EmbeddingRecord — per-layer expert output embeddings
├── residual_stream.py   # ResidualStreamState — per-layer residual stream vectors
├── clustering.py        # ClusteringConfig — reduction + clustering parameters
└── capture_manifest.py  # CaptureManifest — session provenance metadata

core/
├── parquet_reader.py    # Generic Parquet → Pydantic record reader
└── parquet_writer.py    # Batched Parquet writer with schema validation
```

## Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Model load state, GPU availability |
| `/api/probes` | GET | List all probe sessions |
| `/api/probes/{id}` | GET | Session details with sentences |
| `/api/probes/sentence-experiment` | POST | Run full sentence capture experiment |
| `/api/experiments/analyze-routes` | POST | Expert routing analysis (Sankey data) |
| `/api/experiments/analyze-cluster-routes` | POST | Cluster routing analysis (after reduction) |
| `/api/experiments/reduce` | POST | PCA/UMAP dimensionality reduction |
| `/api/experiments/temporal-capture` | POST | Temporal basin transition experiment |
| `/api/probes/sessions/{id}/clusterings` | GET | List clustering schemas |
| `/api/probes/sessions/{id}/clusterings/{name}` | GET | Load schema with reports and descriptions |

## Running

```bash
cd backend/src
../../.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Model loading takes several minutes. Check `/health` — `model_loaded: true` means ready.

## The Adapter Pattern

All model-specific behavior (layer count, expert count, routing style, weight loading) is encapsulated in adapters. To add a new model:

1. Create `adapters/your_model_adapter.py` implementing `BaseModelAdapter`
2. Define a `ModelTopology` with the model's constants
3. Register it: `register_adapter("your-model", YourAdapter)`

The rest of the pipeline (capture, analysis, visualization) works unchanged.
