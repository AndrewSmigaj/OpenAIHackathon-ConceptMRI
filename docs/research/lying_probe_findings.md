# Lying — Truth × Stakes Probe v1: Findings

**Date:** 2026-04-27
**Session:** `session_47d16472` (`lying_v1`)
**Schema:** `lying_v1_k5_n16` (k=5, UMAP 6D, n_neighbors=16, residual stream, last-occurrence)
**Sentence set:** `lying_truth_stakes_v1` (400 scenes, 4 quadrants of 100, scene+question wrapper)
**Model:** gpt-oss-20b, NF4 quantized
**Methodology:** Pattern B lens design (per `/probe` skill) + linear-probe verification before cluster analysis

## Headline finding

**The model has a near-perfect internal representation of who is lying — and a near-systematic refusal to use it at the output, gated by stakes.**

Concretely:
- Linear probes on the residual stream recover the lying-vs-honest distinction at **93.8% from L0** and **98.3% at L23** (chance = 0.500). The composition (4-class quadrant) is recoverable at **97.5% at L23**.
- At the output, the model correctly identifies lying in only **22% of lying scenes** overall: **29% on lying_high**, **15% on lying_low**.
- Output behavior is gated by the **stakes** axis, not by the truth axis. The L23 cluster with the **most high-stakes scenes** (C0, 99% high) gives the **highest lying-recall** (33%); the L23 cluster with the most **lying-pure** scenes (C4, 75% lying) gives only **15% recall**.
- False positives are rare — the model commits to "yes/lying" only when stakes-vocabulary AND lying-evidence align. Two of five L23 clusters produce zero false-positives.

The model knows. It just won't say.

## Linear-probe accuracy by layer

5-fold cross-validated logistic regression on the 2880-dim residual stream at the help-token position. Position-alone baseline shown below for confound check.

| Layer | Truth (lying vs honest) | Stakes (high vs low) | Quadrant (4-class) |
|------:|------------------------:|---------------------:|-------------------:|
|  L0   |  0.938 |  0.963 |  0.935 |
|  L1   |  0.972 |  0.970 |  0.938 |
|  L3   |  0.982 |  0.993 |  0.975 |
|  L5   |  0.988 |  0.993 |  0.982 |
|  L7   |  0.993 |  0.995 |  0.985 |
|  L11  |  0.993 |  0.993 |  0.988 |
|  L15  |  0.990 |  0.997 |  0.997 |
|  L17  |  0.990 |  0.997 |  0.993 |
|  L23  |  0.983 |  0.997 |  0.975 |
| Position-only baseline | 0.292 | 0.597 | 0.440 |
| Chance |  0.500 |  0.500 |  0.250 |

Faster convergence than the v2 help probe (which had Direction at 81% at L0 and reached 99% at L7). The lying probe is at 94% by L0 and only ramps two more points to 99% by L8. The model integrates "is this person lying" almost entirely in block 0.

The position-alone baseline confirms a small length confound: stakes-baseline 60% (high-stakes scenes are 1-3 tokens longer on average than low-stakes scenes). This contaminates the L0 numbers slightly but cannot explain >90% accuracy.

## Behavioral correctness per quadrant

| Quadrant | N | Correct | Note |
|---|---:|---:|---|
| honest_high | 100 | **85%** | Model correctly says "no" most of the time |
| honest_low | 100 | **57%** | Many off_topic / ambiguous (mundane scenes don't strongly trigger commitment) |
| lying_high | 100 | **29%** | Model says "no" 50% of the time despite clear deception in scene |
| lying_low | 100 | **15%** | White lies almost never flagged; model defaults to "no" |

The model has a **strong "no" bias on lying scenes**. The asymmetry by stakes (29% vs 15%) shows the bias is partly mitigated when stakes are high — high-stakes language acts as a permission gate for the model to commit to "yes the person lied".

## L23 cluster composition + output behavior

| L23 Cluster | N | Lying% | High-stakes% | Correctly flagged lying (yes_yes) | False positive (yes_no) | Lying scenes wrongly said honest (no_no) | Honest scenes correctly said honest (no_yes) |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 120 | 50% | **99%** | 20 | 0 | 26 | 47 |
| C1 | 67 | 67% | 39% | 7 | 2 | 27 | 17 |
| C2 | 74 | 9% (mostly honest) | 5% (mostly low) | 0 | 8 | 3 | 38 |
| C3 | 75 | 53% | 25% | 10 | 2 | 22 | 26 |
| C4 | 64 | **75%** | 50% | 7 | 0 | 31 | 14 |

**The diagnostic comparison**:
- **C0** (high-stakes mega-basin, only 50% lying): yields 20 correct lying-flags and **0 false positives** → **lying-recall = 33%**
- **C4** (lying-richest basin, 75% lying): yields 7 correct lying-flags → **lying-recall = 15%**

The model is **more confident at flagging deception in C0 than in C4** even though C4 contains a much higher proportion of actual liars. What predicts the model's "yes" output is not whether the scene depicts a lie — it's whether the scene contains high-stakes context.

Two of five clusters (C0, C4) produce **zero false positives**. The model is conservative — when it commits to "yes", it's right. The failure mode is exclusively under-flagging.

## What k=5 finds vs what's actually encoded

This is the key methodological point Emily flagged previously: cluster purities are not faithful evidence of representation.

At every layer L0..L23:
- k=5 hierarchical produces 4-5 clusters that are >85% **stakes-pure**
- 0-2 clusters are >70% **truth-pure** at any layer
- 0 clusters are quadrant-pure (Truth-pure AND Stakes-pure simultaneously) at L23

But linear probes show **Quadrant decodable at 97.5% at L23**. The compositional information is fully present; k=5 simply allocates its 5 cuts to the dominant variance axis (Stakes), and the Truth axis becomes a finer sub-structure inside each cluster.

This is identical to the v2 help-probe pattern and confirms the methodological warning: **never claim "X is encoded" or "X is lost" from cluster purities alone**. The probe-skill update from yesterday now requires linear-probe corroboration for any such claim.

## The stakes-as-permission-gate finding

The clearest mechanistic explanation of the 29%/15% accuracy gap on lying scenes:

The model uses stakes-vocabulary as a **necessary precondition** for committing to "yes the person lied". When stakes are low (white lies, social grace, kid stories), the model defaults to "no" regardless of how clearly the scene depicts deception. When stakes are high (medical, financial, legal, personal-serious), the model is willing to commit to "yes" — but only at 29% of the time, still far below its 98% encoding accuracy.

This generalizes the v2 help probe's "offering bias on bystander-rich scenes" finding into a more specific claim: **the model uses surface stakes-vocabulary as an output gate that overrides its internal truth representation**.

Alignment relevance: a model that under-flags casual deception is exactly the failure mode you'd want to detect. White lies and social-grease deceptions are the *easy* case for a deception detector; the model handles them worse than serious frauds. This is a precision-aware but recall-blind detector.

## Layer-by-layer cluster geometry summary

- **w0 (L0–L6)**: stakes-pure cuts dominate from L1 onward. Two persistent low-stakes basins emerge (white-lie, mundane-honest). The two high-stakes quadrants merge into one stakes-pure mixed basin. Linear probes at near-ceiling throughout.
- **w1 (L5–L11)**: same pattern; high-stakes basin progressively partitions by *domain* (personal, legal, professional) rather than truth. L11 has TWO high-stakes mixed basins, neither truth-pure.
- **w2 (L11–L17)**: brief truth-pure clusters appear at L13–L15 (one each for lying_high, honest_high, honest_low). L15→L16 is a 75% reorganization that merges the high-stakes lying+honest into one basin. Cluster reshuffling does not correlate with linear-probe changes (which stay flat at 99%).
- **w3 (L17–L23)**: L18C1 is the cleanest single-axis basin in the entire window (85% lying-pure), then progressively absorbed into stakes-organized basins by L23. By L23, 0 of 5 clusters are quadrant-pure even though linear-probe quadrant accuracy is 97.5%.

The repeated pattern: **k=5 spends its cuts on Stakes because Stakes has more geometric variance, not because Truth is less encoded.**

## Comparison to v2 help probe

| Phenomenon | Help probe (v2) | Lying probe (v1) |
|---|---|---|
| L0 linear-probe accuracy on primary axis | 81% (Direction) | 94% (Truth) |
| Layer of linear-probe ceiling | L7 at 99% | L8 at 99% |
| L23 linear-probe accuracy | 99.3% Direction | 98.3% Truth |
| L23 cluster geometry | Stakes-organized (k=5 picks stakes cuts) | Stakes-organized (k=5 picks stakes cuts) |
| Behavioral failure mode | Offering bias on bystander scenes (request_high 46% accuracy) | "No" bias on lying scenes (lying_low 15%, lying_high 29%) |
| Failure-mode mechanism | High-stakes basin pools request+offer; defaults to "offering" | High-stakes basin gates "yes" commitments; defaults to "no" outside high-stakes |

Same architectural pattern: **the residual stream encodes the design axes near-perfectly; the lm_head defaults to a stakes-modulated answer regardless of the encoded ground truth.** This is now a confirmed cross-probe phenomenon — two independent design axes (Direction, Truth) both show the same representation-vs-output gap with stakes acting as the output's permission gate.

## Methodology validation

This is the third application of the Pattern-B lens design (after help_v2). The pattern continues to work:
- Wrapper question is identical across 400 probes → no surface-clustering at target token possible
- Linear probes corroborate cluster findings before they're claimed
- Cluster reorganization across layers is no longer mistaken for representation change

Linear-probe sweep was added as a Phase D step before /analyze, with results passed into the analysis subagents' prompts. This avoided the kind of "collapse" overclaim that v2 originally made.

## Probe artifacts

- Sentence set: `data/sentence_sets/role_framing/lying_truth_stakes_v1.json`
- Probe guide: `data/sentence_sets/role_framing/lying_truth_stakes_v1.md`
- Capture: `data/lake/session_47d16472/`
- Schema: `data/lake/session_47d16472/clusterings/lying_v1_k5_n16/`
- Reports: `reports/w_0_5.md`, `w_5_11.md`, `w_11_17.md`, `w_17_23.md`
- Element descriptions: 310 (120 cluster + 190 route)
- Linear probe results: `/tmp/lying_v1/linear_probes.json`

## Open questions worth follow-up

1. **k-sweep at L23**: rebuild at k=8 / k=12 and check whether quadrant-pure sub-clusters re-appear inside the high-stakes mega-basin. If yes, confirms k=5 was the only constraint hiding compositional structure. If no, suggests stakes really does dominate the geometry beyond a clustering choice.
2. **Lm_head investigation**: the representation-vs-output gap is now confirmed across two probes. The next mechanistic question is what the lm_head's "yes"/"no" token directions actually project from the L23 residual. If the projection is nearly orthogonal to the linear-probe Truth axis, that's a clean explanation for why the encoded answer doesn't reach the output.
3. **Padded-length variant**: scene lengths vary by quadrant (high-stakes scenes 1-3 tokens longer on average), which carries 60% Stakes signal at L0 from position alone. A padded version of this probe (uniform token count before wrapper) would isolate the actual representation signal at the embedding layer.
4. **Stakes-attenuated test**: if the "no" bias on lying_low is driven by lack of stakes-vocabulary, then injecting neutral stakes language into low-stakes lying scenes should improve recall. A small follow-up sentence set with controlled vocabulary across stakes×truth would test this.
