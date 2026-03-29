---
name: temporal
description: Run temporal basin captures — single runs, paired batches, and verification
---

# Temporal Basin Capture

Run temporal capture experiments that measure how MoE routing basins persist or shift as context changes. Each run processes an ordered sequence of sentences (basin A then basin B) and records the model's routing at each step.

## Constants

| Constant | Value |
|----------|-------|
| Capture endpoint | `POST http://localhost:8000/api/experiments/temporal-capture` |
| List runs | `GET http://localhost:8000/api/experiments/temporal-runs/{session_id}` |
| Lag data | `POST http://localhost:8000/api/experiments/temporal-lag-data` |
| Python | `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python` |
| Lake path | `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/data/lake` |

**NEVER use bare `python3`** — always use the full venv path above.

---

## Input Format

The UI generates a copy-paste instruction. Parse it to extract parameters:

```
Run temporal capture on session {session_id}: basin_a={id} ({label}), basin_b={id} ({label}), layer={N}, schema={name}, {mode}, {N}/block
```

Extracted parameters: `session_id`, `basin_a_cluster_id`, `basin_b_cluster_id`, `basin_layer`, `clustering_schema`, `processing_mode`, `sentences_per_block`.

---

## Key Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `generate_output` | `false` | **Always false for temporal.** Generation adds 50 autoregressive forward passes per position — hours of unnecessary compute. Temporal only needs routing data. |
| `sequence_config` | `block_ab` | A sentences first, then B. Use `block_ba` for reverse direction. |
| `custom_sentences` | null | Pass explicit sentence list instead of random sampling. Used for sentence pairing. |
| `custom_regime_boundary` | null | Override auto-detection of regime boundary. Set to `sentences_per_block` (e.g., 20) when using custom_sentences. |
| `custom_target_word` | null | Target word for custom_sentences mode. Required when using custom_sentences. |

---

## Timing

With `generate_output: false` (the default for temporal):

| Mode | Per run | 10 runs |
|------|---------|---------|
| `expanding_cache_on` | ~35 sec | ~6 min |
| `expanding_cache_off` | ~35 sec | ~6 min |

With `generate_output: true` (NOT recommended — adds 50 autoregressive steps per position):

| Mode | Per run | 10 runs |
|------|---------|---------|
| `expanding_cache_on` | ~1 min | ~10 min |
| `expanding_cache_off` | ~15 min | ~2.5 hours |

Cache_off recomputes the full forward pass from scratch at each position with growing cumulative text (quadratic attention cost), but with `generate_output: false` the difference is minimal since the forward pass is fast on its own.

---

## Operations

Each operation is a self-contained block. Replace `{placeholders}` with actual values.

### OP-1: Batch N Runs

Run N captures sequentially with the same parameters. Each run randomly samples sentences from the basins. Run with `run_in_background: true` for large batches.

```bash
PY=/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python
for i in $(seq 1 {N}); do
  echo "=== {label} run $i/{N} ==="
  curl -s -X POST http://localhost:8000/api/experiments/temporal-capture \
    -H "Content-Type: application/json" \
    -d '{
      "session_id": "{session_id}",
      "basin_a_cluster_id": {basin_a},
      "basin_b_cluster_id": {basin_b},
      "basin_layer": {basin_layer},
      "clustering_schema": "{schema}",
      "sentences_per_block": {sentences_per_block},
      "processing_mode": "{mode}",
      "sequence_config": "{block_ab_or_ba}",
      "generate_output": false
    }' | $PY -c "
import json, sys
d = json.load(sys.stdin)
if 'temporal_run_id' in d:
    print(f'  OK: {d[\"temporal_run_id\"]} ({d[\"sequence_positions\"]} pos)')
else:
    print(f'  ERROR: {json.dumps(d, indent=2)}')
    sys.exit(1)
" || { echo "ABORTING"; break; }
done
echo "=== Done ==="
```

### OP-2: Paired cache_off

Run cache_off captures using the **same sentences** as existing cache_on runs. This ensures valid ΔPersistence comparison. Run with `run_in_background: true` — cache_off is slow (~15 min/run).

**Prerequisite**: cache_on runs must already exist (from OP-1).

```bash
PY=/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python
LAKE=/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/data/lake

# Generate one curl command per unpaired cache_on run, then execute each
$PY -c "
import json
runs = json.load(open('$LAKE/{session_id}/temporal_runs.json'))
cache_on = [r for r in runs if r['processing_mode'] == 'expanding_cache_on']
cache_off_count = len([r for r in runs if r['processing_mode'] == 'expanding_cache_off'])
todo = cache_on[cache_off_count:]  # skip already-paired
print(f'TOTAL={len(todo)}')
for i, run in enumerate(todo):
    sents = [run['sentence_texts'][str(j)] for j in range(run['sequence_positions'])]
    payload = json.dumps({
        'session_id': '{session_id}',
        'basin_a_cluster_id': run['basin_a_cluster_id'],
        'basin_b_cluster_id': run['basin_b_cluster_id'],
        'basin_layer': run['basin_layer'],
        'processing_mode': 'expanding_cache_off',
        'sequence_config': run['sequence_config'],
        'clustering_schema': run['clustering_schema'],
        'generate_output': False,
        'custom_sentences': sents,
        'custom_target_word': '{target_word}',
        'custom_regime_boundary': run['regime_boundary'],
    })
    print(payload)
" | {
  read -r HEADER
  TOTAL=\${HEADER#TOTAL=}
  N=0
  while read -r PAYLOAD; do
    N=\$((N + 1))
    echo "=== cache_off \$N/\$TOTAL ==="
    echo "\$PAYLOAD" | curl -s -X POST http://localhost:8000/api/experiments/temporal-capture \
      -H "Content-Type: application/json" -d @- | $PY -c "
import json, sys
d = json.load(sys.stdin)
if 'temporal_run_id' in d:
    print(f'  OK: {d[\"temporal_run_id\"]} ({d[\"sequence_positions\"]} pos)')
else:
    print(f'  ERROR: {json.dumps(d, indent=2)}')
    sys.exit(1)
" || { echo "ABORTING"; break; }
  done
  echo "=== Done ==="
}
```

Replace `{session_id}` and `{target_word}` with actual values (e.g., `session_1434a9be` and `tank`).

**Resumable**: If interrupted, re-running the same command skips already-completed cache_off runs.

### OP-3: Verify Run Counts

Show runs grouped by mode × direction.

```bash
PY=/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python
$PY -c "
import json
from collections import Counter
runs = json.load(open('data/lake/{session_id}/temporal_runs.json'))
counts = Counter((r['processing_mode'], r.get('sequence_config', '?')) for r in runs)
for k, v in sorted(counts.items()):
    print(f'  {k}: {v} runs')
print(f'Total: {len(runs)}')
"
```

**Expected for a complete experiment (40 runs per probe):**
```
  ('expanding_cache_off', 'block_ab'): 10 runs
  ('expanding_cache_off', 'block_ba'): 10 runs
  ('expanding_cache_on', 'block_ab'): 10 runs
  ('expanding_cache_on', 'block_ba'): 10 runs
Total: 40
```

---

## Processing Modes

| Mode | Input per step | Cache | Speed |
|------|---------------|-------|-------|
| `expanding_cache_on` | Single sentence | KV cache chains forward | Fast (~1 min/run) |
| `expanding_cache_off` | All sentences concatenated | No cache, full recompute | Slow (~15 min/run) |

**ΔPersistence = lag(cache_on) − lag(cache_off)**

If ΔPersistence > 0, the KV cache creates extra routing persistence beyond what the text context alone produces.

---

## Workflows

### Full Experiment (40 runs per probe)

The standard 2×2 factorial design: cache_on/off × A→B/B→A × 10 reps.

1. **Verify backend ready**: Check `/health` for `model_loaded: true`
2. **Run OP-1**: 10× `expanding_cache_on`, `block_ab` (~10 min)
3. **Run OP-1**: 10× `expanding_cache_on`, `block_ba` (~10 min)
4. **Run OP-2**: paired cache_off for all 20 cache_on runs (~5 hours, run overnight)
5. **Run OP-3**: verify 40 total

### Add More Runs

To add N more runs to an existing condition:

1. **Run OP-1**: N× with the desired mode + direction
2. If cache_on: **Run OP-2** to generate paired cache_off runs
3. **Run OP-3**: verify new totals

### Sentence Pairing (Why OP-2 Exists)

Cache_on and cache_off must process the **same sentences** in the **same order** for ΔPersistence to be valid. Without pairing, differences could be due to different sentence content rather than cache effects.

OP-1 (cache_on) randomly samples sentences and stores them in `temporal_runs.json` → `sentence_texts`. OP-2 reads those sentences and passes them back as `custom_sentences` for the cache_off run. The `custom_regime_boundary` parameter ensures the regime split is at the correct position (e.g., 20).

---

## Interpreting Results

### Basin Axis Projection

Each temporal position gets a scalar value: 0.0 = at basin A centroid, 1.0 = at basin B centroid. Computed as Fisher's Linear Discriminant on raw residual stream vectors (no reducer needed, ~0.03s for 400 probes).

### Lag Chart

- **X-axis:** sequence position (1 to 2N)
- **Y-axis:** basin axis projection (0.0 = basin A, 1.0 = basin B)
- **Vertical dashed line** at regime boundary (position N)
- **Thin lines** = individual runs, **bold dashed** = mean, **shaded** = confidence band

### Key Metrics

- **Routing lag**: first position after boundary where projection crosses 0.5 and stays crossed for 3+ consecutive positions
- **ΔPersistence**: lag(cache_on) − lag(cache_off). If > 0, the KV cache creates extra routing persistence beyond what the text context alone produces.
- **Basin separation**: L2 distance between centroids (measures how separable the basins are)

### Verification Checks

- All projection values should be in roughly [−0.2, 1.2] range (slight overshoot is normal)
- Run counts should match expected (40 for full experiment: 10 reps × 2 orderings × 2 cache conditions)
- Cache_on and cache_off runs should be paired (same sentences, same order) — this is why OP-2 exists

---

## Important Rules

- **`generate_output: false` always** — temporal doesn't need generated text. With `true`, each position runs 50 autoregressive forward passes (adds hours per run).
- **Never parallel captures** — GPU will OOM (~15GB model). One run at a time.
- **Cache_off runs overnight** — ~15 min each, 10+ hours for a full batch.
- **Always pair cache_on/off sentences** — use OP-2, never run cache_off via OP-1 independently.
- **Backend must have model loaded** — check `/health` for `model_loaded: true`.
- **NEVER use bare `python3`** — always the full venv path.
- **No Python scripts** — use bash loops with inline curl. No separate .py files for batch orchestration.
