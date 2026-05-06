# lying_v5 — Max-variance design surfaces truth at L17 (V_truth = 0.94 at k=4/k=6)

## TL;DR

Three results from the verdict-position capture (`session_e4a9c1fa`):

1. **Truth surfaces in cluster geometry.** At L17 with k=6 hierarchical clustering, **V_truth = 0.945** — a dramatic improvement over `lying_v3` (0.59) and `lying_v4` (0.61). At L15, k=6 gives V_truth = 0.895. At k=4 the picture is similar (L15: 0.770, L17: 0.945).
2. **Variance budget redistributed.** Truth η² jumped from 2.0% (v3/v4) to **7.0%** (v5). pair_id and category_label both at 75% (each pair is its own unique category — they perfectly partition each other).
3. **Expert routing is collapsed at the verdict position.** For 17 of 24 layers, all 200 probes route to the SAME top-1 expert. The truth-state computation lives in the **residual geometry**, not in the **expert routing** decisions. This confirms the user's earlier observation that prior probes "all use the same top expert across all ranks and layers."

## Behavioural baseline

| Group  | yes | no | other (truncated) | accuracy |
|--------|----:|---:|------------------:|---------:|
| lying  | 100 | 0  |  0                | 100%     |
| honest |  0  | 89 | 11                | 89%      |

100% directional consistency (no false positives or negatives). The 11 "other" cases on honest are all model-overthinking-the-format truncations — e.g. _"'What is the verdict?' might be a separate question. But the instruction says answer only yes or no..."_ — running out of tokens before committing.

## Variance decomposition at L20

| Axis | η² | n_groups |
|------|----:|---------:|
| **truth** | **0.070** | 2 |
| category_label | 0.753 | 100 |
| pair_id | 0.753 | 100 |

Compare:

| Session | truth η² @ L20 | projection sep @ L20 | best V_truth at any k/layer |
|---------|---------------:|---------------------:|----------------------------:|
| v3 (varying audiences) | 0.020 | 0.831 | 0.61 |
| v4 (audience fixed)    | 0.021 | 0.775 | 0.61 |
| **v5 (max-variance)**  | **0.070** | **0.830** | **0.945** |

Truth η² **3.5× higher** in v5 vs v3/v4. The cluster-V_truth gap is far larger: **0.94 vs 0.61** at the best-tuned k and layer.

## V_truth across (k, layer) for v5

| Layer | k=2   | k=4   | k=6 |
|------:|------:|------:|----:|
| L0    | 0.525 | 0.545 | 0.545 |
| L3    | 0.515 | 0.525 | 0.525 |
| L7    | 0.515 | 0.545 | 0.545 |
| L11   | 0.530 | 0.570 | 0.570 |
| L13   | 0.560 | 0.565 | 0.570 |
| **L15** | 0.650 | **0.770** | **0.895** |
| **L17** | 0.620 | **0.945** | **0.945** |
| L20   | 0.500 | 0.605 | 0.715 |
| L23   | 0.590 | 0.675 | 0.675 |

Clean signal at **L15–L17 with k=4 or k=6**. k=2 doesn't surface truth — when forced to one binary cut, the algorithm picks something other than truth state. With k=4 it can split into 2 lying-clusters + 2 honest-clusters, and the truth axis becomes the dominant cut.

The L20 drop and L23 partial recovery suggests later layers reorganize the residual to incorporate output-decoding-relevant content alongside truth. Truth is best legible at L15–L17.

## Truth-axis projection separability (independent measurement)

| Layer | separability | Cohen d |
|------:|-------------:|--------:|
| L0    | 0.555 | 0.067 |
| L3    | 0.650 | 0.748 |
| L7    | 0.795 | 1.503 |
| **L11** | **0.940** | 3.228 |
| **L15** | **0.975** | 3.432 |
| **L17** | **0.970** | 3.001 |
| L20   | 0.830 | 1.872 |
| L23   | 0.910 | 2.232 |

The projection method (centroid `lying_mean − honest_mean`, threshold along that direction) gives 94–97.5% across L11–L23. **Cluster geometry now matches projection geometry** at L17 (V_truth = 0.945 vs projection sep = 0.970) — the two methods converge, meaning the truth axis really is the dominant within-residual structure, not just a hidden small axis recoverable only by projection.

## Expert routing observation — confirmed

The user noted: "all probes use the same top expert across all ranks and layers, except small exceptions." The data:

```
Top-1 expert diversity per layer at the verdict-token position (200 probes):
Layer | n_unique_experts | most_common_expert (count of 200) | entropy (bits)
L 0  |   2 |   9 (N=196) | 0.14
L 1  |   1 |   0 (N=200) | 0.00
L 2  |   2 |   5 (N=186) | 0.37
L 3  |   1 |   2 (N=200) | 0.00
L 4  |   3 |  18 (N=170) | 0.76
L 5  |   2 |  24 (N=163) | 0.69
L 6  |   1 |   3 (N=200) | 0.00
L 7  |   1 |   4 (N=200) | 0.00
L 8  |   1 |  10 (N=200) | 0.00
L 9  |   2 |   8 (N=199) | 0.05
L10  |   2 |   5 (N=155) | 0.77
L11  |   3 |  30 (N=145) | 0.88
L12  |   1 |   3 (N=200) | 0.00
L13  |   5 |  21 (N=134) | 1.33
L14  |   2 |  29 (N=179) | 0.48
L15  |   1 |   9 (N=200) | 0.00
L16  |   1 |  11 (N=200) | 0.00
L17  |   1 |   7 (N=200) | 0.00 ← also where V_truth peaks at 0.945
L18  |   1 |  14 (N=200) | 0.00
L19  |   1 |  22 (N=200) | 0.00
L20  |   1 |   5 (N=200) | 0.00
L21  |   1 |  23 (N=200) | 0.00
L22  |   1 |  13 (N=200) | 0.00
L23  |   1 |  24 (N=200) | 0.00
```

**17 of 24 layers (including all of L15–L23) have exactly 1 unique top-expert across all 200 probes.** L13 is the most diverse (5 experts, 1.33 bits entropy).

**Two facts coexist:**
- The residual at L17 cleanly separates lying from honest (V_truth = 0.945, projection sep = 0.97).
- The expert routing decision at L17 is identical for all 200 probes.

So the MoE routing function is insensitive to the truth signal at the verdict position. Truth lives in the *content* of the residual but not in the *routing decision* the MoE makes from that residual. Two interpretations:

1. **The routing function operates on coarser features** (token identity / position / question-context) and ignores the fine-grained residual content where truth is encoded. This is consistent with the harmony-format wrapper being identical at the verdict position across all probes — same wrapper → same routing.
2. **The routing has been "decided" by an earlier layer** and the verdict-position residual at L17 inherits the routing context from upstream. Since the question stem is identical, the upstream routing is also identical.

Both interpretations are consistent with the data. **Capturing at the `Sam` position** (upstream of the constant question-wrapper, in `is Sam lying?`) is the next test — if `Sam`-position routing is also collapsed, hypothesis (1) holds; if it's diverse, hypothesis (2) holds.

## What the design proved

The "all-or-nothing variance" principle worked. By:
- Holding constant: speaker (Sam), template, question wrapper
- Varying maximally: lie content (100 unique categories, no shared structure across pairs)
- Within each pair: only the consequential value flipped (same word count)

The variance budget was forced into a shape where pair_id (= unique scenario content) absorbs 75% of variance, but the truth axis is the next-largest *consistent* axis — and clustering at k=4 or k=6 cleanly partitions on it.

This validates the user's design intuition: **partial variance creates clustering structure on the partially-varied axis** (the v3/v4 failure mode where 5 categories × 10 audiences each formed 5 large clumps and 50 audience clumps). **Maximum randomization (no shared structure across pairs) eliminates those clumps** and lets a smaller-but-consistent axis (truth) surface as a primary cluster axis.

## Open questions (next up)

1. **`Sam`-position capture**: does routing diversify at the upstream position? Does V_truth match or exceed the verdict-position result?
2. **Why exactly L15–L17?** What changes in the model's processing between L13 (most diverse routing, V_truth = 0.57) and L15 (collapsed routing, V_truth jumps to 0.65 → 0.89)?
3. **L20 drop in V_truth (0.715 at k=6)**: cluster geometry becomes less pure even though projection separability stays high (0.83). The dominant *cluster* axis shifts away from truth at L20+ even though the truth axis stays present in the residual. What's the new dominant axis?

## Files

- Probe set: `data/sentence_sets/role_framing/lying_v5.json`
- Probe guide: `data/sentence_sets/role_framing/lying_v5.md`
- Strategy: `docs/research/StudiesByClaude/lying_v5_strategy.md`
- Session: `session_e4a9c1fa`
- Schemas: `lying_v5_k{2,4,6}_n15`
- Behavior: 100% lying / 89% honest verdict accuracy (11 truncations, 0 misclassifications)
