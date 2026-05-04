# Lying Elicitation v1 — Preliminary Findings

**Status**: Draft, sanity-checked twice (most recent revision: 2026-05-04 with hand-classified verdicts replacing the regex). Numbers are stable but the *interpretation* still has open questions called out below. Do not cite as conclusions until at least one replication.

## Update 2026-05-04: classifier refinement changed the headline

The original within-condition asymmetry (override V_verdict=0.45, no-override V_verdict=0.30) was largely an artifact of the loose regex classifier missing "no" judgments hidden in deliberation text under the no-override condition. Hand-classifying all 120 generations into 7 fine-grained categories (yes_clean, no_clean, yes_reasoning, no_reasoning, mixed, truncated, degenerate) and recomputing V gives:

- Within-override V_verdict ≈ 0.44 (k=4 n=15 at L6)
- Within-no-override V_verdict ≈ **0.45** (k=4 n=15 at L17)

They're essentially equal. **The "partial suppression unmasked by override" framing is no longer supported by this data.** The override doesn't uniquely unmask geometric structure that the no-override condition lacks — both conditions form clean verdict-correlated clusters.

What IS still true:
- The cross-condition yes-rate shift is dramatic and real (3% → 45%+ under override).
- Both conditions have residual-stream geometry organized by what verdict the model is about to commit to.
- The override SHIFTS the model from one verdict-basin to another rather than UNMASKING a basin that wasn't visible.

What can't be settled with this study: whether the override-induced "yes" verdicts represent *recognition* (the model judges the speaker is lying because the evidence shows it) or *compliance with the override instruction* (the model says yes because told not to be diplomatic, regardless of truth). All probes are lying scenes; we have no honest controls. **The cleanest test of recognition vs compliance is the half-lies/half-truths design** the user named as a future direction.

**Session**: `session_b960315d` (120 probes, all `label=lying`)
**Schemas built**: k×n_neighbors ∈ {2,4,6} × {5,8,15} (7 schemas total on disk)
**Probe set**: `data/sentence_sets/role_framing/lying_elicitation_v1.json`

## Design recap

120 probes, all clear-cut lying scenes (claim contradicted by evidence). 2×2×3 factorial:
- `speaker`: first_person ("Was I lying?") / third_person ("Was Sam lying?")
- `diplomacy`: none (`Was I lying? What is the verdict?`) / override (`Was I lying? Do not be diplomatic. State the verdict: yes or no.`)
- `severity`: extreme (firearm, child harm, fatal fraud) / moderate (federal/medical/SEC) / mild (roommate, sibling, partner)

Single-group design — the question is *what makes the model commit to "yes" verdicts on lying scenes*, not *can clusters separate lying from honest*.

## Behavioral output (no platform involvement)

Verdict classification by regex on `generated_text` (loose pattern matching for first-token answer plus self-talk patterns like "answer: yes", "verdict: yes"):

| Diplomacy | yes | no | none (deliberation/no-commit) |
|---|---|---|---|
| **none** (n=60) | 2 (3%) | 45 (75%) | 13 (22%) |
| **override** (n=60) | 27 (45%) | 14 (23%) | 19 (32%) |

**Override flips yes-rate from 3% → 45%** in self-talk. The first-token answer is much more conservative — only 1 of 120 is a clean "Yes." at position zero. Most "yes" judgments are inside the model's deliberation text.

**Caveats on the classifier**: 32 probes ended up classified "none" because the model produced harmony-style deliberation ("we have to decide if Sam was lying...") that truncated before committing. These aren't *no judgment*; they're *commitment cut off*. A finer classifier — or longer generation — would likely reassign some of them to yes/no based on deliberation lean.

## Cluster geometry (with sanity checks)

### V_diplomacy = 1.000 across all schemas — surface confound, not a finding

At every schema (k=2/4/6, n_neighbors=5/8/15), V_diplomacy at L1+ is 1.000. This is the trivial 12-token surface difference (the override condition adds "Do not be diplomatic. State the verdict: yes or no."). Clusters perfectly partition into "all-override" and "all-no-override" subgroups. **This is the floor, not the result.**

### V_verdict (cross-condition) = 0.570 at k=2 — mostly the same trivial split

At k=2, V_verdict at L0/L5+ is 0.57-0.58 — comparable to the published tank/suicide probes' 0.55. **But this is mostly the diplomacy-driven verdict shift restated geometrically**: cluster A = all 60 no-override probes (3% yes), cluster B = all 60 override probes (45% yes). The V is large because diplomacy and verdict are correlated, both driven by the override prompt change.

Treating this as a publishable headline would over-claim. The cross-condition V is contaminated by the input-token surface effect.

### V_verdict within each diplomacy condition — the actual signal

Computed by restricting probes to one diplomacy condition and measuring how the clusters within that condition organize by verdict.

| Schema | Within-override (best L) | Within-no-override (best L) |
|---|---|---|
| k=4 n=15 | **L8 V=0.450** | L11 V=0.337 |
| k=6 n=15 | **L8 V=0.450** | L13 V=0.283 |
| k=4 n=8 | L5 V=0.370 | L15 V=0.337 |
| k=4 n=5 | L5 V=0.427 | L21 V=0.328 |

(k=2 can't measure within-condition V_verdict because each condition has exactly one cluster by construction — V_diplomacy=1.0.)

**Within-override V≈0.45 is the real cluster→verdict signal.** Adding more clusters (k=6) doesn't help; reducing n_neighbors didn't help. k=4 n=15 is at the optimum.

### What within-override looks like at L5 (k=6)

| Cluster | n | Top severity | yes | no | none |
|---|---|---|---|---|---|
| L5C0 | 26 | extreme/moderate | **69%** | 15% | 15% |
| L5C3 | 18 | mixed | 22% | 11% | **67%** ← deliberation |
| L5C4 | 16 | mostly mild | 31% | **50%** | 19% |

Three distinct verdict-correlated clusters within the override condition:
- **"Going to commit yes" basin** — populated by extreme/moderate scenarios
- **"Deliberating without committing" basin** — populated by the cases where the model produces harmony-style reasoning that truncates
- **"Still going to say no" basin** — populated by mild scenarios where the override doesn't override the diplomatic prior

### What within-no-override looks like at L5 (k=6)

| Cluster | n | yes | no | none |
|---|---|---|---|---|
| L5C1 | 29 | 3% | 76% | 21% |
| L5C2 | 20 | 5% | 60% | 35% |
| L5C5 | 11 | 0% | **100%** | 0% |

Uniformly "no" across all 3 sub-clusters. Verdict variance is too low for cluster geometry to discriminate cleanly.

## What this is and isn't evidence for

### What it shows
1. The diplomacy override changes the model's verbal output distribution dramatically (3% → 45% yes-rate in self-talk).
2. The within-override verdict-cluster structure (V≈0.45) shows the model has at least 3 distinct internal states under override: yes-bound, deliberating, no-bound.
3. **Severity mediates** the override effect: extreme scenarios shift toward yes under override; mild ones stay no even with the same override instruction.

### What it doesn't cleanly show
**The within-condition asymmetry can't be attributed to "override unmasks suppression" alone.** The override produces both more verdict variance AND more cluster organization. Without a way to vary one without the other, we can't distinguish:

- (a) The override unlocks a pre-existing recognition state that surfaces into observable geometry.
- (b) The override makes the model do *more computation*, producing more diverse internal states that produce more diverse outputs — without unlocking anything that was previously hidden.

Both are consistent with our data. The user's preferred hypothesis is (a) — partial suppression. (b) is the null hypothesis we can't yet rule out.

### What would distinguish them
- **Capture the harmony `<analysis>` channel separately from final output** (the user's flagged direction). If under no-override the analysis stream contains "yes" judgments that the final output suppresses, that's direct evidence for (a) — the recognition exists upstream of the suppressed commitment. If the analysis stream is also "no" under no-override, (a) is weakened.
- **Half-lies / half-truths revisit** with the override condition. If override + lying scenes → "yes" but override + honest scenes → "no" reliably, the model is *recognizing* (not just complying with the override instruction). If override produces "yes" on both lying and honest scenes, it's compliance not recognition.
- **Base/RLHF before-after comparison** (out of scope for current platform; recorded in RECOMMENDATIONS.md).

## Open methodological issues

1. **My regex classifier is moderate quality.** 32/120 probes classified "none" because they truncated mid-deliberation. A better classifier (LLM-as-judge or longer generation) would tighten the verdict counts and possibly raise V_verdict.
2. **Single-group design limits visualization.** The frontend's cluster sankey and trajectory plot color by `label_distribution` (always uniform "lying" here), so the user's selected color axis isn't applied (see RECOMMENDATIONS.md "frontend color axis selection silently ignored"). The contingency-table panel works correctly; the trajectory/sankey colors do not.
3. **Sample size per cell is small** — 10 probes per (speaker, diplomacy, severity) cell. Severity-mediation patterns should be replicated at higher N before claiming.
4. **Surface tokens dominate diplomacy split**. Any diplomacy-framed analysis at k≤6 has to be done within-condition to control for this.

## Files

- Probe set: `data/sentence_sets/role_framing/lying_elicitation_v1.json`
- Probe guide: `data/sentence_sets/role_framing/lying_elicitation_v1.md`
- Session: `data/lake/session_b960315d/`
- Schemas:
  - `lying_elicitation_v1_k2_n5/`, `_k2_n8/`, `_k2_n15/`
  - `lying_elicitation_v1_k4_n5/`, `_k4_n8/`, `_k4_n15/`
  - `lying_elicitation_v1_k6_n15/`
- Screenshots: `phase1_k6_initial.png`, `phase1_k6_trajectory.png`, `phase1_k2_full.png`, `phase1_k2_traj_view.png`, `phase1_k4_full.png`

## Suggested next steps (for user to direct)

1. **Replicate at higher N** — author elicitation_v2 with 240 probes (20/cell), focus on the severity × diplomacy interaction.
2. **Harmony-stream extraction** — investigate whether `generated_text` contains harmony channel markers that we should split into `<analysis>` vs final-output. Classify each separately.
3. **Half-lies / half-truths** with the override condition — the cleanest test of recognition vs compliance.
4. **Better classifier** — LLM-as-judge over the 120 generations to reduce the "none" residual and get higher-fidelity verdict counts.

The user has already named (3) as a future direction. (1) and (2) are prerequisites for cleanly testing it.
