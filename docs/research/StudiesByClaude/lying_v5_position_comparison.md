# lying_v5 — Sam-position is the cleaner capture site for truth

## TL;DR

Capturing the residual at the **Sam** token (last occurrence: in `is Sam lying?`) gives a **dramatically cleaner truth signal** than capturing at **verdict** (last occurrence: in `What is the verdict?`):

- **Sam-position cluster V_truth at k=6 is 0.93–0.96 from L11 through L23** — broad layer range, no late-layer drop.
- **Verdict-position cluster V_truth peaks at L17 (0.945) but drops to 0.72 at L20 and 0.68 at L23.**
- **Sam-position projection separability hits 1.000 (perfect) at L15 and L17.**
- At k=2 (forced binary cut), Sam-position L15 splits 100% honest in one cluster and 93.5% lying in the other — the binary cut IS the truth axis.

The Sam position is upstream of the constant question wrapper (`Answer only yes or no - is Sam lying? What is the verdict?`). At the verdict position, the model has already "decided" and the residual is being prepared for output decoding, which loads other axes onto the residual that compete with truth at clustering. The Sam position, while still in the question, is at the moment the model is *evaluating* — and that's where the truth representation is cleanest.

## Setup

Same probe set (`lying_v5.json`), captured twice:
- **Session A (verdict)**: `target_word="verdict"` → `session_e4a9c1fa`
- **Session B (Sam)**:     `target_word="Sam"`     → `session_0163093a`

Same 200 probes, same generated text both times (deterministic; verified identical generated_text per probe across the two sessions). The only difference is which token's residual gets stored in `residual_streams.parquet`. Same UMAP+hierarchical clustering pipeline applied to each.

## Behavioral identity (same model, same outputs)

Both sessions produce the same generated text per probe input — the model doesn't know it's being captured at different positions. Behavior is identical: 100% lying detection, 89% honest detection, 11 truncations on honest where the model overthought the format instruction.

## V_truth comparison (cluster purity at k=6 hierarchical)

| Layer | **Sam-position** | verdict-position | delta |
|------:|-----------------:|-----------------:|------:|
| L0    | 0.525            | 0.545            | -0.02 |
| L3    | 0.535            | 0.525            | +0.01 |
| L7    | 0.515            | 0.545            | -0.03 |
| L11   | **0.930**        | 0.570            | **+0.36** |
| L13   | **0.960**        | 0.570            | **+0.39** |
| L15   | **0.965**        | 0.895            | +0.07 |
| L17   | **0.955**        | 0.945            | +0.01 |
| L20   | **0.945**        | 0.715            | **+0.23** |
| L23   | **0.915**        | 0.675            | **+0.24** |

The Sam-position truth signal:
- **Emerges 4 layers earlier** (L11 vs L15 for the verdict position to reach >0.85)
- **Persists through L23** (0.915) instead of decaying

## V_truth at k=2 (the binary-cut diagnostic)

When forced to make ONE binary partition, does the algorithm pick truth?

| Layer | Sam k=2 | verdict k=2 |
|------:|--------:|------------:|
| L11   | 0.510 | 0.530 |
| L13   | 0.505 | 0.560 |
| **L15** | **0.965** | 0.650 |
| L17   | **0.950** | 0.620 |
| L20   | 0.560 | 0.500 |
| L23   | 0.540 | 0.590 |

At Sam-position L15 and L17, the **single binary cut at k=2 IS the truth axis**: V_truth = 0.95+. The verdict-position never reaches that — its k=2 peak is 0.65.

L15 cluster composition at k=2 (Sam-position):
- C0 (N=107): 100 lying, 7 honest → 93.5% lying
- C1 (N=93):  0 lying, 93 honest → 100.0% honest

The 7 mis-clustered honest probes in C0 are likely the truncation cases (where the model didn't commit a final verdict, leaving the residual in an ambiguous state) — but I haven't verified that mapping yet.

## Variance decomposition comparison

η² for the truth axis at each layer, both positions:

| Layer | Sam η² | verdict η² | ratio |
|------:|-------:|-----------:|------:|
| L0    | 0.0006 | 0.0004     | 1.5x  |
| L3    | 0.0100 | 0.0029     | 3.4x  |
| L7    | 0.0168 | 0.0128     | 1.3x  |
| L11   | **0.0659** | 0.0317 | 2.1x  |
| L13   | **0.0866** | 0.0420 | 2.1x  |
| **L15** | **0.1174** | 0.0952 | 1.2x  |
| L17   | 0.1034 | 0.1045     | 1.0x  |
| L20   | 0.0624 | 0.0700     | 0.9x  |
| L23   | 0.0700 | 0.0489     | 1.4x  |

Sam-position truth η² peaks at **0.117 at L15** (11.7% of total residual variance is truth axis). At L11–L15 the Sam position has 2× the truth variance the verdict position has at the same layers. The tables converge by L17–L20 — by then the model has "committed" and the truth representation is being shared between the two positions.

## Projection separability comparison

Centroid-direction projection (mean(lying) − mean(honest)), threshold-sweep separability:

| Layer | Sam   | verdict | difference |
|------:|------:|--------:|-----------:|
| L0    | 0.550 | 0.555   | -0.01 |
| L3    | 0.740 | 0.650   | +0.09 |
| L7    | 0.890 | 0.795   | +0.10 |
| L11   | 0.985 | 0.940   | +0.05 |
| L13   | **0.995** | 0.915 | +0.08 |
| **L15** | **1.000** | 0.975 | +0.03 |
| **L17** | **1.000** | 0.970 | +0.03 |
| L20   | 0.965 | 0.830   | +0.14 |
| L23   | 0.900 | 0.910   | -0.01 |

**Sam-position hits perfect (1.000) projection separability at L15 and L17.** The truth axis at the Sam position is so cleanly defined that a single linear threshold along it correctly classifies all 200 probes.

## Expert routing diversity comparison

Top-1 expert diversity per layer (200 probes):

| Layer | Sam unique experts (entropy) | verdict unique experts (entropy) |
|------:|:-----------------------------:|:-------------------------------:|
| L 0   | 1 (0.00)                      | 2 (0.14)                        |
| L 1   | 3 (0.09)                      | 1 (0.00)                        |
| L 2   | 2 (1.00)                      | 2 (0.37)                        |
| L 3   | 2 (0.50)                      | 1 (0.00)                        |
| L 4   | 3 (1.04)                      | 3 (0.76)                        |
| L 5   | 2 (0.05)                      | 2 (0.69)                        |
| L 6   | 1 (0.00)                      | 1 (0.00)                        |
| L 7   | 2 (0.11)                      | 1 (0.00)                        |
| L 8   | 2 (0.88)                      | 1 (0.00)                        |
| **L 9** | **6 (1.92)**                | 2 (0.05)                        |
| L10   | 3 (0.80)                      | 2 (0.77)                        |
| **L11** | **4 (1.24)**                | 3 (0.88)                        |
| L12   | 4 (0.88)                      | 1 (0.00)                        |
| L13   | 2 (0.72)                      | 5 (1.33)                        |
| L14   | 3 (0.76)                      | 2 (0.48)                        |
| **L15** | **3 (1.52)**                | 1 (0.00)                        |
| L16   | 1 (0.00)                      | 1 (0.00)                        |
| L17   | 1 (0.00)                      | 1 (0.00)                        |
| L18   | 2 (0.38)                      | 1 (0.00)                        |
| L19   | 3 (0.50)                      | 1 (0.00)                        |
| L20   | 1 (0.00)                      | 1 (0.00)                        |
| L21   | 2 (0.14)                      | 1 (0.00)                        |
| L22   | 1 (0.00)                      | 1 (0.00)                        |
| L23   | 2 (0.05)                      | 1 (0.00)                        |

The Sam position has more diverse routing than verdict at L7–L15 (the layers where the truth signal is being *built*). L9 has 6 unique experts at Sam vs 2 at verdict; L15 has 3 vs 1. Both positions collapse to 1 expert at L16–L17 and largely stay there, but the Sam position briefly recovers some diversity at L18–L19.

This supports a layered picture:
- **L7–L15**: model is *evaluating Sam's claim* against reality. At the Sam position (in `is Sam lying?`) the routing is content-sensitive — different experts for different lie types. Truth axis is being built.
- **L16+**: model has *decided*. Routing collapses to wrapper-driven decisions. Truth representation is locked in but no longer reflected in routing.

The verdict position (in `What is the verdict?`) is downstream of the decision and shows collapsed routing throughout. The Sam position captures the model mid-evaluation.

## What this means for the platform's central claim

**UMAP+hierarchical clustering of residual-stream activations at task-relevant tokens DOES surface the design axis when:**
1. **Probe design holds non-target features either constant (variance = 0) or fully randomized (no shared structure across pairs).** The "all-or-nothing variance" principle.
2. **Capture position is upstream of constant question wrappers.** The Sam-position is upstream of `is Sam lying? What is the verdict?`; the verdict-position sits inside that wrapper.

These two design choices took V_truth at k=6 from **0.55–0.61 (v3, v4) to 0.95–0.96 (v5 at Sam)**. Cluster geometry is now showing the model's internal lying-vs-honest distinction as the dominant axis, not as a hidden 2% subspace.

## Files

- Probe set: `data/sentence_sets/role_framing/lying_v5.json` (verdict capture target) + `lying_v5_at_sam.json` (Sam capture target, identical text)
- Sessions: `session_e4a9c1fa` (verdict), `session_0163093a` (Sam)
- Schemas: `lying_v5_k{2,4,6}_n15` (verdict), `lying_v5_sam_k{2,4,6}_n15` (Sam)
- Strategy: `docs/research/StudiesByClaude/lying_v5_strategy.md`
- Position-A findings: `docs/research/StudiesByClaude/lying_v5_findings.md`
