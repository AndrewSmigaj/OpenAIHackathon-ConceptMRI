# lying_minimal_v1 — V_truth ≈ 1.0 under harmony pipeline + minimal-variance design

> **Update 2026-05-04 (later same day):** see `lying_diverse_v1_findings.md`. When the lie type varies across the dataset (5 categories), V_truth drops to ~0.50–0.60 across all layers, including within each individual category. The single-category V_truth = 1.0 reported below is a within-category artifact of the residual encoding "are these two values identical?" cleanly when only one kind of value varies. The model still recognizes lying behaviorally across all categories (94% accuracy) — but cluster geometry of the verdict-token residual does not generalize.

## TL;DR

When (a) the capture pipeline is fixed to use harmony format with `max_new_tokens=256`, and (b) probe surface variance is minimised by holding everything constant except a single consequential value (CLAIM_TIME vs EVIDENCE_TIME, with strict equality for honest twins), the residual stream at the verdict token cleanly separates lying from honest probes from layer 2 onwards. At k=6 hierarchical clustering, every cluster from L3 through L23 is 100% pure lying or 100% pure honest, with zero canonical-basin flips at any layer transition.

This is the opposite of `lying_balanced_v1`'s headline finding (V_truth ≈ 0). The change is *both* the harmony fix (necessary for non-degenerate model behaviour) and the minimal-variance design (necessary for the clustering algorithm to not be drowning in surface noise). Either change alone would have been insufficient.

## Behavioural baseline

100 probes (50 lying + 50 honest, strict-equality matched pairs by CLAIM_TIME). Captured under the new harmony pipeline (use_chat_template=True, max_new_tokens=256). 99/100 produced an `assistantfinal` commitment in the harmony `final` channel:

| Group | Yes | No | Other (truncated) |
|---|---:|---:|---:|
| Lying  | 49 | 0 | 1 |
| Honest | 0 | 50 | 0 |

The single truncated probe (lying / claim 1:00 AM / evidence 11:23 PM) spent its 256-token analysis-channel budget on a coherent deliberation but didn't reach `assistantfinal`. Its analysis-channel content shows the model correctly identifying the inconsistency.

This is essentially perfect behavioural recognition — a marked improvement over `lying_balanced_v1`'s 55%/7% asymmetry, which was contaminated by raw-text-format degenerate output (cutoff complaints, hallucinated context, format refusals).

## Geometric finding

Schema `lying_minimal_v1_k6_n15` (k=6 hierarchical, 6D UMAP, n_neighbors=15, residual stream at verdict token).

**Cluster purity by layer:**

- L0: 1/6 pure (1 honest-only cluster of N=9; this is a tokenization artefact — the round-hour claim-times where claim and evidence both tokenize as identical short sequences)
- L1: 1/6 pure (1 lying-only cluster of N=5; truth signal starting to surface, four other clusters skew sharply but k=6 doesn't yet partition cleanly)
- L2: 5/6 pure (5 fully pure clusters + 1 mixed cluster of N=6 with 4 honest / 2 lying)
- **L3 through L23: 6/6 pure at every layer** (3 lying-pure + 3 honest-pure)

**Basin topology evolution** (canonical-basin flips per L→L+1):

| Transition | Flips |
|---|---:|
| L0 → L1 | 46/100 |
| L1 → L2 | 26/100 |
| L2 → L3 | 2/100 |
| L3 → L23 | 0/100 (every L→L+1) |

The truth-state computation effectively fires at the L1→L2 transition; by L3 the partition is rigid. From L3 to L23, no probe ever changes which canonical basin it occupies.

**Cluster→behaviour alignment at L23** (the layer that decodes to the harmony-final logits):

- Every lying-pure cluster routes 100% to `verdict=yes` (49 yes + 1 truncated/other = the lying group).
- Every honest-pure cluster routes 100% to `verdict=no` (50 no = the honest group).

This is the cleanest cluster-to-output alignment we've recorded on this platform.

## Why v1_minimal worked when v1_balanced didn't

Two compounding changes:

1. **Harmony format pipeline.** `lying_balanced_v1` was captured before the `use_chat_template=True` fix. Its generated outputs were largely degenerate (raw-text-format confused-LLM continuations). The 240 residuals it captured at the verdict token reflect the model failing to engage with the prompt as a chat turn, not the model's truth-state computation. Behaviour and geometry both compromised.

2. **Surface variance minimisation.** Even with v1_balanced's design corrected for capture format, its 4 templates × 60 base scenarios = 240 probes contained substantial irrelevant variation in audience, speaker, claim verb, evidence type, severity dimension. This variance dominates UMAP+hierarchical clustering at k=6: the algorithm cuts on the largest variance directions, which are surface features, not the ~1 bit truth-state distinction. v1_minimal eliminates ~95% of surface variance — 1 audience, 1 speaker, 1 verb structure, 1 evidence type, 1 question template — leaving only the consequential value (time match/mismatch) as the operative axis of variation.

We can't disentangle which change was load-bearing without an ablation, but the joint effect is dramatic: V_truth ≈ 0 → V_truth ≈ 1.0.

## Caveats

**Token-repetition confound is not fully ruled out.** Honest probes have an identical time-string repeated twice in the input ("…at 5:00 PM on the night…" + "…exited at 5:00 PM that night…"). Lying probes have two different time-strings. UMAP+hierarchical clustering of the residual at the verdict token *could* be picking up "are these tokens identical?" as a feature rather than the truth-state computation per se. The L0 round-hour cluster (L0C3) is direct evidence that token-level features can drive clustering at this stage of the network.

The geometric distinction "lying basin vs honest basin" is robust; the interpretation "the model is computing truth state" is consistent with the data but not yet established. A follow-up probe set with paraphrase-honest twins (e.g. claim "5:00 PM" / honest evidence "five o'clock", same denoted time, different surface tokens) would resolve this: if the paraphrase-honest probes still cluster with the strict-equality honest probes, the cluster encodes truth state; if they cluster with lying probes, the cluster encoded token repetition.

**The 50-probe samples per truth class are small.** Cluster-purity at 6/6 per layer is striking, but with N=50 per class there's no statistical power to distinguish "perfect separation" from "near-perfect with tail outliers below detection threshold." The headline finding survives a sample-size scaling check (probably) but should be repeated at N=200 per class.

**Within-class sub-clusters are unexamined.** k=6 hierarchical clustering produces 3 lying-pure + 3 honest-pure sub-clusters at every L3+ layer. The sub-clusters are stable across layers by probe-set overlap — i.e. they're not drifting categories, they're consistent partitions. What property they encode (time-of-day? magnitude-of-discrepancy? direction-of-shift?) is left for follow-up. Probably worth a higher-k sweep.

## Files

- Probe set: `data/sentence_sets/role_framing/lying_minimal_v1.json`
- Probe guide: `data/sentence_sets/role_framing/lying_minimal_v1.md`
- Session: `session_562d1cc2`
- Schema: `lying_minimal_v1_k6_n15`
- Per-window synthesis reports: `data/lake/session_562d1cc2/clusterings/lying_minimal_v1_k6_n15/reports/{w_0_5,w_5_11,w_11_17,w_17_23}.md`
- Element descriptions: 144 cluster descriptions across all 24 layers
- Code changes that enabled this: harmony format + max_new_tokens=256 (commits e970cd5)

## Suggested next steps

1. **Paraphrase-honest follow-up** — disentangle truth-state encoding from token-repetition feature.
2. **N=200 scaling** — verify the 6/6 cluster purity holds at larger sample size.
3. **k-sweep** — explore within-class sub-cluster identity at k=8, k=12 to characterise the secondary axis.
4. **Re-run lying_balanced_v1 under harmony pipeline** — separate the "harmony fix" effect from the "surface-variance" effect. Predicts: harmony-fixed v1_balanced shows partial truth signal (cleaner than V_truth ≈ 0) but not full like v1_minimal.
