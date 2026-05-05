# lying_v4 — Audience-fix alone doesn't move V_truth, BUT centroid-projection reveals truth IS encoded.

## TL;DR

Two interlocking findings:

1. **Audience-fix doesn't lift cluster V_truth.** Replacing all audiences in `lying_v3` with "federal investigator" eliminates 81% of L20 residual variance (audience axis collapses to 0). But cluster V_truth at k=6 stays at 0.51–0.61, basically unchanged from `lying_v3` (0.55–0.60). Why? **Source variance is still 79%.** Audience and source covaried in v3 (each audience pool came with a matched source pool), so the actual freed-up variance budget after audience-fix is small.

2. **The truth signal is unambiguously encoded** in the residual stream — it just isn't the dominant clustering axis. When I project each probe's residual onto the truth-axis direction (`mean(lying) − mean(honest)`), lying and honest separate with **77–89% threshold accuracy** at L11–L17 across all four sessions including `v3` and `v4`. In `lying_minimal_v1` (where audience and category were held constant) the same projection gives 100% separability. The drop from 100% to 80% is the cost of letting topical/audience variance compete for the residual's variance budget — but the cost isn't fatal. The truth axis survives.

This reframes the prior findings docs: the lying_minimal_v1 V_truth = 1.0 result was NOT solely an artifact of single-category content. The truth signal generalizes — the model has a coherent "is this consistent or not?" representation that produces a stable centroid direction across categories. What does NOT generalize is **truth being the dominant variance axis**, which is a property of the variance budget at the verdict-token residual, not of whether truth is encoded.

## Method change — geometric projection diagnostic

Cluster purity (V_truth) measures: *given that hierarchical clustering at k=6 partitions the residuals, do those partitions align with truth state?* If audience or source has higher variance, the clusters partition by those axes and V_truth comes out low.

Centroid projection measures: *is there a 1D direction in the 2880-d residual space along which lying and honest separate?* This is a strictly geometric construction — compute two means, take their difference, project. No training, no learned probe. The threshold-sweep separability is the maximum fraction of probes correctly classified by any threshold along that one direction.

Both measure something real. The first asks "does the model's representation cluster naturally by truth?" The second asks "does the model's representation contain a truth-state direction at all?" The two answers diverge here, and the divergence is the finding.

## Behavioral baseline (v4)

| Magnitude  | Lying yes / no / other | Honest yes / no / other |
|------------|------------------------|-------------------------|
| gross      | 57 / 0 / 3   (95% acc) | 58 / 0 / 2   (97% acc)  |
| moderate   | 53 / 1 / 6   (88% acc) | 58 / 0 / 2   (97% acc)  |
| subtle     | 50 / 3 / 7   (83% acc) | 59 / 0 / 1   (98% acc)  |

Slightly better than v3 (gross detection 95% vs v3's 88%). Holding audience constant doesn't hurt behavior.

## Variance decomposition at L20

Comparing v3 (varying audience) to v4 (audience held to "federal investigator"):

| Axis       | v3 η² (n_groups) | v4 η² (n_groups) | Δ (v4 − v3) |
|------------|------------------|------------------|-------------|
| **truth**  | 0.020 (2)        | 0.021 (2)        | +0.001      |
| lie_type   | 0.192 (6)        | 0.200 (6)        | +0.008      |
| magnitude  | 0.020 (3)        | 0.009 (3)        | −0.012      |
| **audience** | **0.811 (158)** | **0.000 (1)**   | **−0.811**  |
| **source** | 0.808 (159)      | 0.795 (159)      | −0.013      |
| pair_id    | 0.885 (180)      | 0.866 (180)      | −0.019      |

**Audience went from 81% → 0% (verified).** The freed variance went mostly nowhere — truth, category, magnitude all moved by < 1.5 points. **Source still explains 79.5% of variance** even after audience-fix, because audience and source were highly correlated in v3 (each scenario came with matched audience+source).

The pair_id η² of 87% in v4 is consistent: each pair's distinct claim+evidence content (still varying across pairs) accounts for most of the residual variance.

## Cluster purity at k=6 (V_truth, k=6 hierarchical)

| Layer | minimal | diverse | v3 | v4 |
|------:|:-------:|:-------:|:--:|:--:|
| L0    | 0.62    | 0.50    | 0.53 | 0.52 |
| L3    | **1.00** | 0.50   | 0.50 | 0.51 |
| L11   | 1.00    | 0.52    | 0.52 | 0.52 |
| L15   | 1.00    | 0.55    | 0.57 | 0.59 |
| L17   | 1.00    | 0.60    | 0.59 | 0.61 |
| L20   | 1.00    | 0.61    | 0.59 | 0.58 |
| L23   | 1.00    | 0.57    | 0.54 | 0.59 |

minimal stands alone at 1.00. The other three sit at 0.50–0.61. Audience-fix didn't move the needle.

## Truth-axis projection separability (the key new measurement)

For each session, compute the centroid direction `lying_mean − honest_mean` at the chosen layer, then project every probe's residual onto that direction and find the best threshold. Separability = fraction of probes correctly classified by that threshold.

| Layer | minimal | diverse | v3 | v4 |
|------:|:-------:|:-------:|:--:|:--:|
| L3    | **1.00** | 0.62   | 0.57 | 0.64 |
| L7    | 1.00    | 0.73    | 0.68 | 0.70 |
| L11   | 1.00    | 0.86    | 0.83 | 0.89 |
| L15   | 1.00    | 0.83    | **0.89** | 0.88 |
| L17   | 1.00    | 0.81    | 0.83 | 0.77 |
| L20   | 1.00    | 0.80    | 0.83 | 0.78 |
| L23   | 1.00    | 0.74    | 0.69 | 0.72 |

Cohen's d for lying vs honest projections:
- minimal: 4.4 (L3) to 12.9 (L15)
- diverse: 0.29 (L3) to 2.17 (L11)
- v3: 0.29 (L3) to **2.32** (L15)
- v4: 0.51 (L3) to **2.46** (L11)

The L11–L15 region is where the truth axis is most cleanly expressed. v3 and v4 both peak at 89% separability there — same as `lying_minimal_v1` was at L11. The progression from L3 to L11 is the model **building** the truth representation; from L11 to L23 the projection separability degrades slightly (Cohen's d drops from 2.5 to ~1.0) as deeper layers may be incorporating output-decoding-relevant content that's orthogonal to truth.

## What this reframes

In `lying_v3_findings.md` I concluded H4 ("persistent topic dominance") with the gloss "the truth-state computation is happening somewhere we don't measure." That conclusion was wrong. The truth-state computation IS happening at the verdict-token residual — it produces a clean centroid direction with 80–89% separability. The previous wrong gloss came from conflating "is truth encoded?" with "does cluster structure at k=6 reflect truth?". They're different questions.

In `lying_minimal_v1_findings.md` I added a forward-pointer suggesting the V_truth = 1.0 result was an artifact of single-category structure, and possibly token-equality detection rather than truth-state computation. The projection result here shows the truth axis is real, generalizes across categories with N=180 per truth class, and survives at 80–89% separability. The minimal_v1 perfect cluster separation was clean because all OTHER variance was zero — not because the underlying truth axis was an artifact.

## What we now know about variance dominance

Each axis of the design space contributes variance to the residual at the verdict token:

| Axis | Approximate η² | Notes |
|------|----------------|-------|
| pair_id (per-probe content) | 87% | Dominant — every pair has unique claim+evidence content |
| audience | 81% (when varying) | Eliminated in v4 |
| source | 79% | Still varying in v4 |
| lie_type | 19% | Mid-tier |
| magnitude | 1–2% | Small |
| **truth** | **2%** | Small |

Truth being a 2% axis in a 2880-d space means it's a small but coherent direction. UMAP+hierarchical clustering at k=6 picks the largest 5 axes for partitioning; truth doesn't make the cut. Direct projection onto the truth direction recovers it.

## Suggested next experiments

1. **lying_v5: also fix source.** Use a single generic evidence-source phrase ("the case file" or "the records") for every probe. Predicts truth η² ≥ 10–15% (now competing with category/magnitude only) and cluster V_truth probably ≥ 0.80 at L11–L17.

2. **Trajectory analysis on the truth direction.** Project the per-layer residual onto the L11 truth direction and watch how a probe's projected position evolves L0 → L23. Lying probes should drift positive over the build-up layers; honest probes should drift negative. The L→L+1 displacement vectors might cluster more cleanly than absolute residuals.

3. **Per-category truth axis comparison.** Compute the truth axis separately within each category (time, money, location, ...). Are these directions parallel or orthogonal? If parallel, the model has a single category-agnostic truth axis. If orthogonal, the model has category-specific lying detectors that happen to all separate lying from honest in their own subspaces.

4. **Decompose the L0→L11 truth-axis development.** When does the truth direction emerge? At L0 separability is at chance for v3/v4 but already 1.0 for minimal. What's happening in L1–L10 in v3/v4 that produces the 89% L11 axis?

## Files

- Probe set: `data/sentence_sets/role_framing/lying_v4.json`
- Probe guide: `data/sentence_sets/role_framing/lying_v4.md`
- Session: `session_7d0ee2c3`
- Schema: `lying_v4_k6_n15`
- Behavioral data: 95% gross / 88% moderate / 83% subtle on lying detection; 97% / 97% / 98% on honest detection.
