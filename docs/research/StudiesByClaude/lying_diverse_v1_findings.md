# lying_diverse_v1 — V_truth ≈ 0.5 across kinds of lying. Truth signal does NOT generalize at the verdict-token residual.

## TL;DR

When the lie type varies across the dataset (5 categories: time / money / location / quantity / identity), the residual stream at the verdict token **stops cleanly separating lying from honest**. V_truth at k=6 hierarchical clustering is ~0.55-0.60 across all layers — barely above chance (0.50). The 100% cluster purity that `lying_minimal_v1` showed when surface variance was held to a single category does NOT replicate when topical content diversifies.

This means the "truth-state representation" interpretation of `lying_minimal_v1` was over-confident. The signal that produced V_truth ≈ 1.0 there is largely a within-category artifact. When category content varies, that signal is dominated by topical-content variance and clustering at the verdict-token residual no longer recovers truth state.

The model's *behaviour* is unchanged: 46/50 lying → "yes", 48/50 honest → "no" (94% accuracy across categories, with only 6 truncations and zero false positives/negatives). So the model **knows** the truth state — it commits the right verdict — but that knowledge is not visible in cluster geometry of the verdict-token residual when topical content also varies.

## Behavioural baseline

100 probes (50 lying + 50 honest, 5 categories × 10 matched pairs). Captured under the harmony pipeline.

| Category   | Lying yes / no / other | Honest yes / no / other | Per-pair accuracy |
|------------|------------------------|-------------------------|-------------------|
| time       |  8 / 0 / 2             |  0 / 10 / 0             | 90% |
| money      | 10 / 0 / 0             |  0 / 10 / 0             | 100% |
| location   | 10 / 0 / 0             |  0 /  8 / 2             | 90% |
| quantity   | 10 / 0 / 0             |  0 / 10 / 0             | 100% |
| identity   |  8 / 0 / 2             |  0 / 10 / 0             | 90% |
| **Total**  | **46 / 0 / 4**         | **0 / 48 / 2**          | **94%** |

All 6 "other" cases are truncations (analysis channel ran past `max_new_tokens=256` without reaching `assistantfinal`). Zero false positives, zero false negatives. The model recognizes lying across all 5 categories.

## Geometric finding — V_truth ≈ chance

Schemas tested: `lying_diverse_v1_k{2,6,10}_n15`. Same UMAP and hierarchical clustering pipeline as `lying_minimal_v1_k6_n15`.

### Cluster purity by truth-state across layers

| Layer | k=2 V_truth | k=6 V_truth | k=10 V_truth | k=6 V_lietype |
|------:|:-----------:|:-----------:|:------------:|:-------------:|
| L0    | 0.50        | 0.52        | —            | 0.47          |
| L3    | 0.50        | 0.52        | 0.53         | 0.42          |
| L11   | 0.50        | 0.52        | 0.53         | 0.46          |
| L17   | 0.55        | 0.60        | 0.60         | 0.48          |
| L20   | 0.60        | 0.61        | 0.63         | 0.53          |
| L23   | 0.60        | 0.57        | 0.63         | 0.51          |

`lying_minimal_v1_k6_n15` for comparison: V_truth = 1.000 at every layer L3–L23. Diverse drops it to ~0.60 max.

### What does k=2 reveal? (the cleanest test)

At k=2 the algorithm is forced to make ONE binary cut. If the model encoded truth state as the dominant axis at the verdict-token residual, that cut would split lying-from-honest. It doesn't. At L23 the binary cut is:

- C0 (N=65): 37 lying + 28 honest. Categories: 13 time + 5 money + 20 location + 11 quantity + 16 identity.
- C1 (N=35): 13 lying + 22 honest. Categories: 7 time + 15 money + 9 quantity + 4 identity.

So C1 is "money + quantity" - dominant whereas C0 is "everything else" - dominant. The split is **categorical content** with a slight truth bias overlaid (37/28 vs 13/22). V_truth at k=2 = 0.59 — barely above 0.50 chance.

### Within-category V_truth (the strongest fairness test)

Even restricting to a single category (e.g. just the 20 time probes), V_truth tops out at ~0.55-0.75 at any layer. So this isn't an "across-category dilution" artifact — within each category, truth state still doesn't separate cleanly when other category content is also in the dataset's UMAP fit.

| Layer | V_truth within `time` | within `money` | within `location` | within `quantity` | within `identity` |
|------:|:--:|:--:|:--:|:--:|:--:|
| L17   | 0.55 | 0.55 | 0.60 | 0.75 | 0.60 |
| L20   | 0.55 | 0.60 | 0.60 | 0.75 | 0.65 |
| L23   | 0.55 | 0.55 | 0.60 | 0.60 | 0.60 |

(Compare lying_minimal_v1, where the time category alone gave V_truth = 1.0.)

## What this overturns

The `lying_minimal_v1` synthesis claimed: "the residual stream at the verdict token cleanly separates lying from honest from layer 2 onwards" with the qualifier "the stronger interpretation that the residual encodes a truth-state computation rather than a token-repetition feature is consistent but not yet established."

**The qualifier was load-bearing and now reads as the actual story.** What v1 measured was almost certainly the residual encoding a within-category "are these two values identical?" signal, which is high-amplitude and clean *when only one kind of value varies*. Once five kinds of values vary (time-of-day numbers, dollar amounts, city names, item counts, person names), the residual no longer carries that signal as the dominant clustering axis. Topic dominates.

The model behaviorally still gets 94% accuracy, so somewhere in the network the truth-state computation is happening. But it is not legible at the verdict-token residual under UMAP+hierarchical clustering at k≤10 in the presence of topical variance. We do not have visibility into where it lives.

## What this means for the platform's central claim

Open LLMRI's central claim is that residual-stream clusters at task-relevant tokens predict and explain model behaviour. For **single-axis tasks** with low surface variance (the `lying_minimal_v1` setup), the claim holds in striking form — V_truth = 1.0. For **multi-axis tasks where the design axis competes with topical variance** (the `lying_diverse_v1` setup), the verdict-token residual at k=6–10 is dominated by topical structure and the design axis becomes invisible to clustering.

This is not a fatal limitation, but it bounds the scope of cluster-geometry evidence. Specifically:

1. **A clean cluster separation is strong evidence the design axis is encoded — but only as the dominant axis.** Other axes can be present and undetectable.
2. **The absence of cluster separation is NOT evidence the axis is unencoded.** It only means the axis is not the dominant variance direction in the residual at this token under this clustering algorithm.
3. **Cluster geometry alone cannot establish "the model is computing X" for low-variance Xs in the presence of high-variance confounders.** Behavioural evidence (commitment in the harmony-final channel) provides independent confirmation that X is computed somewhere; cluster geometry confirms WHERE only when X is the dominant axis.

## Suggested next experiments

Given the user's insistence on geometric (not linear-probe) techniques:

1. **Increase k aggressively (k=20, 30) to give space for both axes.** With 100 probes that's 5 per cluster — noisy but might separate if both axes are encoded. This is a methodology test more than a science test.
2. **Capture at a different position** — e.g. at the *evidence value* token rather than the verdict token. The truth computation might happen at the comparison site, not at the commit site.
3. **Trajectory analysis**: instead of clustering single residuals, compare the *direction of motion* between consecutive layers. If the truth-state computation happens during specific transitions, the L→L+1 displacement vectors might separate more cleanly than the absolute positions.
4. **Reduce category variance, keep multi-category**: 5 lie types but each *parameterized* the same way (e.g. all categories use a numeric value: time-as-minutes-since-midnight, money-as-dollars, count-as-integer, even location-as-zipcode, identity-as-employee-ID). This decouples category structure from topical content.
5. **Higher N per cell** — the within-category 0.55-0.75 V_truth might be partly small-N noise (only 20 probes per category × ~3 clusters = ~7 per cell). Author N=200 per category and re-test.

## Files

- Probe set: `data/sentence_sets/role_framing/lying_diverse_v1.json`
- Probe guide: `data/sentence_sets/role_framing/lying_diverse_v1.md`
- Session: `session_d32d8095`
- Schemas: `lying_diverse_v1_k{2,6,10}_n15`
- Behavioural data: 94% verdict accuracy across 5 categories, 6 truncations, 0 misclassifications

## Compared with

`lying_minimal_v1` (single-category, V_truth = 1.0). The contrast is the headline.
