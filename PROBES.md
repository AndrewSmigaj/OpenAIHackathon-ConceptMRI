# Probes — How to Create and Run

Probes are captured model activations for individual sentences. Each probe records expert routing decisions, MLP output embeddings, and residual stream states at every layer for the target word.

## Prerequisites

- Backend server running (`cd backend && .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000`)
- Model loaded in GPU memory (happens automatically on first probe capture, takes ~30s)

## Creating Probes from a Sentence Set

### Via API (curl)

```bash
curl -X POST http://localhost:8000/api/probes/sentence-experiment \
  -H "Content-Type: application/json" \
  -d '{"sentence_set_name": "tank_polysemy_v2"}'
```

Optional: provide a custom session name:
```bash
curl -X POST http://localhost:8000/api/probes/sentence-experiment \
  -H "Content-Type: application/json" \
  -d '{"sentence_set_name": "knife_safety_v2", "session_name": "knife_run_01"}'
```

This is a Claude-based workflow — there is no probe UI. Claude Code runs captures via the API and manages sessions directly.

## What Happens During Capture

1. Sentence set JSON is loaded from `data/sentence_sets/`
2. A capture session is created (unique session ID generated)
3. For each sentence (A and B groups):
   - Text is tokenized
   - Target word position is found
   - Forward pass runs through the model
   - Hooks capture routing weights, MLP embeddings, and residual streams at every layer
   - Data is written to Parquet files in `data/lake/{session_id}/`
4. Session is finalized — manifest written, hooks cleaned up

## Timing

- **First run**: ~30-60s for model loading, then ~0.5s per sentence
- **Subsequent runs**: ~0.5s per sentence (model stays in memory)
- **200 sentences per class (400 total)**: ~3-4 minutes

## Output Files

Each session creates a directory in `data/lake/{session_id}/` containing:

| File | Contents |
|------|----------|
| `tokens.parquet` | Probe records: probe_id, input_text, target_word, label, label2 |
| `routing.parquet` | Expert routing weights per layer per probe |
| `embeddings.parquet` | MLP output embeddings per layer per probe |
| `residual_streams.parquet` | Residual stream states per layer per probe |
| `capture_manifest.parquet` | Session metadata (model, layers, labels, counts) |

## Verifying a Session

### List all sessions
```bash
curl http://localhost:8000/api/probes/sessions
```

### Check session details
```bash
curl http://localhost:8000/api/probes/sessions/{session_id}
```

### Verify Parquet files
```python
import pandas as pd
df = pd.read_parquet("data/lake/{session_id}/tokens.parquet")
print(f"Probes: {len(df)}")
print(df[['probe_id', 'target_word', 'label', 'label2']].head())
```

## Available Sentence Sets

| Set Name | Target Word | Primary Axis | Categories | File |
|----------|------------|--------------|------------|------|
| `tank_polysemy_v2` | tank | aquarium vs vehicle | structure | `polysemy/tank_polysemy_v2.json` |
| `knife_safety_v2` | knife | benign vs harmful | structure, intensity, topic | `safety/knife_safety_v2.json` |
| `gun_safety_v2` | gun | benign vs harmful | structure, intensity, topic | `safety/gun_safety_v2.json` |
| `hammer_safety_v2` | hammer | benign vs harmful | structure, intensity, topic | `safety/hammer_safety_v2.json` |
| `rope_safety_v2` | rope | benign vs harmful | structure, intensity, topic | `safety/rope_safety_v2.json` |
| `said_roleframing_v2` | said | narrative vs factual | speech_type | `role_framing/said_roleframing_v2.json` |
| `said_safety_v2` | said | safe vs unsafe | speech_type | `role_framing/said_safety_v2.json` |
| `attacked_framing_v1` | attacked | roleplay vs factual | voice, scale, specificity | `role_framing/attacked_framing_v1.json` |
| `destroyed_framing_v1` | destroyed | roleplay vs factual | voice, scale, specificity | `role_framing/destroyed_framing_v1.json` |
| `threatened_framing_v1` | threatened | roleplay vs factual | voice, scale, specificity | `role_framing/threatened_framing_v1.json` |

Each set has a `categories` dict per sentence and a file-level `axes` array declaring available category dimensions. See `data/sentence_sets/GUIDE.md` for full category details and confound analysis.

## Running All Probes Sequentially

Run one at a time (model is in GPU memory, can't parallelize):

```bash
for set in tank_polysemy_v2 knife_safety_v2 gun_safety_v2 hammer_safety_v2 rope_safety_v2 said_roleframing_v2 said_safety_v2 attacked_framing_v1 destroyed_framing_v1 threatened_framing_v1; do
  echo "Running $set..."
  curl -s -X POST http://localhost:8000/api/probes/sentence-experiment \
    -H "Content-Type: application/json" \
    -d "{\"sentence_set_name\": \"$set\"}"
  echo ""
done
```
