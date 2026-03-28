# Concept MRI

**Attractor Basin Dynamics in MoE Language Models**

Concept MRI is a research tool for measuring how Mixture of Experts language models commit to interpretive states, how those states resist updating, and where that resistance creates alignment failures. It captures residual stream activations and expert routing patterns across every layer, then uses UMAP projection and hierarchical clustering to identify stable geometric regions — attractor basins — that predict model behavior before any output is generated.

The accompanying paper is in [`paper/main.pdf`](paper/main.pdf).

---

## Research Findings

### Basin geometry predicts model behavior

Clusters identified purely from residual stream geometry predict what the model will do. In the **tank polysemy probe**, five meanings of the word "tank" separate into distinct geometric clusters that predict output topic (Cramer's V = 0.548, p < 0.001). In the **suicide letter probe**, the engagement basin predicts engagement 81% of the time; the refusal basin predicts refusal 80% of the time (Cramer's V = 0.554, p < 0.001).

This is not just descriptive — the model is entering states that drive different behavior. Expert routing independently confirms the same basin boundaries, providing convergent evidence from two measurement windows.

**Tank polysemy** — 5 word senses route to distinct geometric regions:

![Tank polysemy basin identification — expert routing Sankey, latent space Sankey, and UMAP trajectories](paper/polysemybasinsnew.png)

![Contingency table — cluster membership predicts output topic](paper/polysemyoutput.png)

**Suicide letter probe** — genuine vs non-genuine requests separate cleanly:

![Suicide letter probe basin identification — genuine and non-genuine requests in distinct geometric regions](paper/suicidebasins.png)

![Contingency table — basin membership predicts engagement vs refusal](paper/fictionrealindividualsentencesoutputcontigency.png)

### Accumulated context overrides distress sensitivity

The temporal dynamics differ sharply between the two probes, and that contrast is the central finding.

In the **polysemy probe**, the starting basin holds as context accumulates. After the context switch, a noisy transition occurs — the model enters a confusion zone before gradually resolving toward the new basin:

![Polysemy temporal analysis — basin held, noisy transition after switch](paper/polysemyconfusion.png)

In the **suicide letter probe**, both orderings collapse toward the engagement basin within the first few sentences and remain there through the context switch. No transition is visible. The model correctly identifies genuine distress in individual sentences (99% cluster purity), but under accumulated context, that sensitivity disappears:

![Suicide letter temporal analysis — both orderings collapse to engagement basin](paper/fictionrealprobe.png)

This characterizes an alignment failure invisible to harmful-output detection: the model produces benign outputs, just the wrong ones. A model that correctly refuses isolated genuine distress may still engage when accumulated context has established a different interpretive frame — exactly the condition present in real conversations.

---

## How It Works

### Claude Code as Analysis Runtime

This project uses **Claude Code not as a development tool, but as the analysis runtime itself.** The `.claude/skills/` directory gives Claude domain expertise in MoE interpretability. `docs/PIPELINE.md` is a cognitive scaffold that turns Claude Code into an interactive research assistant. The human steers; Claude executes and reasons.

| Skill | What It Does |
|-------|-------------|
| `/probe` | Co-design a new experiment — target word, sentence groups, sentence generation |
| `/pipeline` | Check pipeline state and suggest next step |
| `/categorize` | Classify model-generated outputs along semantic axes |
| `/analyze` | Read cluster/route data, reason about patterns, write reports |
| `/server` | Start, stop, and check status of servers |
| `/temporal` | Run temporal basin capture experiments |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code (Runtime)                  │
│  Skills: /probe  /pipeline  /categorize  /analyze        │
│  Scaffold: CLAUDE.md → PIPELINE.md → Probe Guides        │
└────────────────────────┬────────────────────────────────┘
                         │ natural language + API calls
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                         │
│  Adapters → Capture Service → Analysis Services          │
│  Model: gpt-oss-20b (NF4 quantized, ~15GB VRAM)        │
└────────────────────────┬────────────────────────────────┘
                         │ Parquet read/write
┌────────────────────────▼────────────────────────────────┐
│                    Data Lake                              │
│  data/lake/{session_id}/                                 │
│    tokens.parquet · routing.parquet · embeddings.parquet │
│    residual_streams.parquet · clusterings/{schema}/      │
└─────────────────────────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────┐
│                  React Frontend                          │
│  Sankey diagrams · Stepped UMAP trajectories             │
│  Temporal basin analysis · Click-to-inspect cards        │
└─────────────────────────────────────────────────────────┘
```

### Data flow

- **Probe capture**: Sentences → model forward pass → routing weights + residual streams → Parquet files
- **Basin identification**: Parquet → UMAP 6D → hierarchical clustering → behavioral validation
- **Temporal analysis**: Expanding context window → UMAP projection onto basin axis → persistence measurement

---

## Quick Start

### Prerequisites

- CUDA GPU with 16GB+ VRAM (developed on RTX 5070 Ti)
- Python 3.11+, Node.js 18+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- ~40GB disk space for model weights

### Setup

```bash
git clone https://github.com/AndrewSmigaj/OpenAIHackathon-ConceptMRI.git
cd OpenAIHackathon-ConceptMRI

python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

### Download the model

```bash
.venv/bin/pip install huggingface_hub[cli]
huggingface-cli download openai/gpt-oss-20b --local-dir data/models/gpt-oss-20b
```

### Run

```bash
claude   # Open Claude Code in the project root, then: /server start
```

Or manually:
```bash
# Terminal 1: Backend
cd backend/src && ../../.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

- **Frontend**: http://localhost:5173
- **API docs**: http://localhost:8000/docs

---

## License

The model (gpt-oss-20b) is Apache 2.0 licensed by OpenAI.
