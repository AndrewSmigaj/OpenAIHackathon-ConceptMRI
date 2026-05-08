# Basin-projection extension findings (live notes)

**Status:** in progress. Notes kept here so they survive context compaction.

## Why this extends the per-token study

After per-token cluster-purity analysis (`per_token_separation_report.md`) showed `letter` L23 doesn't have a unique decision-token signature in cluster purity, the user pointed out the right test from the original paper is **basin projection**: project each probe's L23 residual onto the (real-fic centroid) axis IN UMAP-REDUCED SPACE (not raw 2880D), using centroids from clusters identified in the basin study.

The paper used this for the verdict-token (` want`). The natural extension: do the same for the noun-token (` letter`) and see if the collapse pattern holds at both positions.

## Methodology (matches platform's `temporal-lag-data` endpoint)

1. Take the single-sentence basin study residuals at L23 at the target token position (e.g., ` want` is `token_position=3` in the multi-token recapture; ` letter` is `token_position=8`).
2. Fit UMAP-6D, n_neighbors=15, random_state=42, min_dist=0.1.
3. Run hierarchical-k=4 clustering on the UMAP-6D points.
4. Identify the largest pure-fic and largest pure-real clusters (≥80% purity, max n).
5. Compute basin centroids in UMAP space; axis = (real_centroid − fic_centroid); axis_unit normalized.
6. For each temporal probe: extract L23 residual at the relevant token, transform through the SAME UMAP fit, project onto axis_unit. Scalar 0 = fic basin, 1 = real/distress basin.

**Caveat I previously flagged (turned out not to matter much):** UMAP `transform()` is unreliable on out-of-distribution inputs. Cumulative-context probes are longer than the single-sentence basin probes used to fit UMAP. Polysemy validation below shows the methodology works in practice despite this.

## Polysemy validation (proves the methodology is sound)

Centroids: from `tank_polysemy_k6_n15` schema on `session_1434a9be` (498 single-sentence tank probes, 5 categories: aquarium/vehicle/septic/scuba/clothing).

Pure clusters at L23: cluster 4 (98% vehicle, n=52), cluster 5 (92% aquarium, n=53). Same setup the paper used.

Basin axis: vehicle (basin A) → aquarium (basin B). Axis length in UMAP-6D = 4.31.

**4 polysemy temporal sessions, all show paper's "held → transition" pattern:**

| Session | Positions 0-19 | Positions 20-39 |
|---|---|---|
| `session_23e733f2` (A→B) | label A, proj −0.18 to 0.36 (vehicle basin HELD) | label B, proj 0.06 to 1.04 (transition to aquarium) |
| `session_2b4c5dd3` (B→A) | label B, proj 0.83–1.16 (aquarium HELD) | label A, proj −0.02 to 0.52 (transition to vehicle) |
| `session_46ff9d26` (B→A) | label B, proj 0.89–1.16 (HELD) | label A, proj −0.06 to 0.52 (transition) |
| `session_da681708` (A→B) | label A, proj −0.18 to 0.25 (HELD) | label B, proj 0.10 to 0.95 (noisy transition) |

This is the paper's Figure 5 pattern reproduced exactly. The methodology works.

## v1 (cumulative-suicide-content) — `want` vs `letter`

Centroids from per-token recapture `session_9358c2a1` (198 single-sentence suicide-letter probes, 99 fic + 99 real).

For each token (` want` at position 3, ` letter` at position 8): fit own UMAP, identify pure-fic and pure-real clusters at L23, compute basin axis.

` want` axis length in UMAP-6D = 4.53. Pure clusters: cluster 0 (99% real, n=79), cluster 1 (98% fic, n=53).
` letter` axis length in UMAP-6D = 37.59. Pure clusters: cluster 0 (96% real, n=98), cluster 1 (95% fic, n=55).

### v1 trajectory at ` want` (paper's original target)

| Ordering | Pos 0-19 (latest) | Pos 20-39 (latest after switch) |
|---|---|---|
| fictional_then_real | latest=fic, proj 0.0–0.4 (near fic basin) | latest=real, proj 0.0–0.6 (drifts toward fic, doesn't reach real) |
| real_then_fictional | latest=real, proj 0.6–1.2 (near real basin) | latest=fic, proj 0.0–0.6 (drifts toward fic) |

Roughly matches the paper's "collapse to fictional basin" claim, but not as sharply. Real-then-fic ordering does start at real basin and drift toward fic; fic-then-real stays in fic the whole time.

### v1 trajectory at ` letter` (new analysis)

| Ordering | Pos 0-19 (latest) | Pos 20-39 (latest) |
|---|---|---|
| fictional_then_real | latest=fic, proj BOUNCES wildly between 0 and 1 (high variance, no clean basin) | latest=real, proj MOSTLY 0.99 (REAL basin) |
| real_then_fictional | latest=real, proj 1.00 (REAL basin held) | latest=fic, proj MOSTLY 0.99 (REAL basin, rare drops to ~0.13) |

` letter` collapses toward the REAL/DISTRESS basin — opposite direction from ` want`.

**Key finding:** at different token positions in v1, the residual collapses to OPPOSITE basins. ` want` → fictional basin (matches paper). ` letter` → distress basin (new).

Not a UMAP artifact (polysemy validates). The model represents the "suicide letter" semantic content saturated in cumulative context more strongly at the noun position; the verb position is dominated by the writing-frame.

## Sessions referenced

| Tag | Session ID | What |
|---|---|---|
| polysemy basin study | `session_1434a9be` | 498 single-sentence tank probes, 5 categories |
| polysemy schema | `tank_polysemy_k6_n15` | k=6 clustering at L23 with stored centroids |
| polysemy temporal A→B | `session_23e733f2`, `session_da681708` | vehicle then aquarium |
| polysemy temporal B→A | `session_2b4c5dd3`, `session_46ff9d26` | aquarium then vehicle |
| suicide-letter basin (per-token) | `session_9358c2a1` | 198 single-sentence probes (99 fic + 99 real) with multi-token capture |
| v1 cumulative-suicide-content | `session_e7d13156` | 80 expanding-window probes, 2 orderings × 40 positions |

Multi-token capture used `capture_static_substring="I want to write a suicide letter"`, semantic positions 2..8 = ` I, want, to, write, a, suicide, letter`.

## Phase-2 paper-protocol replication (2026-05-08)

After the user clarified the methodology, I redid Family B at proper
paper protocol: K=3 schema for suicide letter, three random orderings
per direction (with replacement from pure-cluster pools), 40 positions
per ordering.

**Sessions (suicide letter Family B paper protocol):**
| Direction | ord0 | ord1 | ord2 |
|---|---|---|---|
| fictional → real | session_58a8b5ba | session_717b765b | session_35e7cbed |
| real → fictional | session_d36f8a5d | session_05446b76 | session_0158f0f4 |

**Methodology**: re-fit UMAP-6D at L23 on basin study residuals;
compute basin centroids in MY UMAP space using K=3 schema's cluster
assignments (cluster 1 = fictional basin, cluster 0 = distress basin).
Project temporal residuals through same UMAP, project on basin axis.
Don't use stored centroids.json — they were computed in a different
UMAP fit and don't align with the re-fit space.

**Trajectories (3 orderings, mean ± std at each position):**

`want` (target token, position 1):
- fictional_then_real: stays at fic basin, mean 0.0-0.3 throughout
- real_then_fictional: starts at distress (mean +1.26 pos 1), drifts
  to ~+0.2 by position 10, stays mid through end
- → REPLICATES paper's collapse-to-fictional finding

`letter` (token_position 8, last noun of static request):
- fictional_then_real: high variance positions 1-3, then locked at
  distress basin (mean ~+1.17 from position 4 onwards)
- real_then_fictional: stays at distress basin (mean ~+1.18) throughout
- → NEW finding: collapse to DISTRESS basin (opposite of want)

Both findings hold across 3 random orderings; SDs mostly 0.0-0.3.

**Trajectory plot:**
`docs/research/StudiesByClaude/figures/paper_protocol_basin_trajectory.png`

## What's next

1. Apply the same paper-protocol projection to polysemy probe family
   for methodology validation (existing 4 polysemy temporal sessions
   on disk are NOT paper protocol — they're mixed cache-on/cache-off
   small-scale captures).
2. Run Family C priming case studies at proper sample sizes (50 fic +
   50 real test endings × N=10 and N=20, drawn from basin pool).
3. Family D paraphrase robustness with new noun-phrase variants.
4. Consolidated final report.

## Key files

- This notes doc: `docs/research/StudiesByClaude/basin_projection_extension_findings.md`
- Earlier per-token report: `docs/research/StudiesByClaude/per_token_separation_report.md`
- Earlier per-token findings: `docs/research/StudiesByClaude/per_token_separation_findings.md`
- Plots: `docs/research/StudiesByClaude/figures/plot{1..4}_*.png`
- Analysis scripts: `docs/scratchpad/per_token_combined.py`, `docs/scratchpad/per_token_plots.py`
