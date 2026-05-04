# Lying — Truth × Stakes Probe v2: Findings

**Date:** 2026-04-27
**Session:** `session_2ba8c273` (`lying_v2`)
**Schema(s):** `lying_v2_k5_n16`, `lying_v2_k8_n16`, `lying_v2_k12_n16`
**Sentence set:** `lying_truth_stakes_v2` (200 scenes, 100 minimal pairs, uniform 2-sentence template)
**Model:** gpt-oss-20b, NF4 quantized
**Predecessor:** `lying_truth_stakes_v1` (400 scenes, per-quadrant marker templates, Truth at 98%+ throughout)

## Headline finding

**v1's "the model encodes lying-vs-honest at 98% end-to-end" was largely a marker-token artifact.** When the same probe is rerun with a uniform template that bans all v1 marker words, Truth recoverability at L23 drops from **98.3% → 71.0%** — a 27-percentage-point drop. Stakes stays at ~99% (it's encoded via domain vocabulary, not v1-specific markers). The behavioral output asymmetry persists, slightly muted (combined accuracy 47% → 42%). Pair-level analysis: 55% of minimal pairs receive the **same** answer regardless of reality content — the model is largely insensitive to the design-axis-relevant clause.

This justifies the lens-design methodology Emily flagged: **cluster purities and aggregate linear-probe scores can be inflated by per-quadrant scene-level templates**. Verifying with a uniform-template variant is the diagnostic.

## Linear probe accuracy comparison

5-fold CV logistic regression on residual stream at help-token position. Selected layers shown.

| Layer | v1 Truth | v2 Truth | Δ Truth | v1 Stakes | v2 Stakes | v1 Quadrant | v2 Quadrant |
|------:|---------:|---------:|--------:|----------:|----------:|------------:|------------:|
|  L0   |   0.938  |   0.470  | **−0.467** |   0.963 |   0.970 |   0.935 |   0.410 |
|  L3   |   0.982  |   0.535  | **−0.448** |   0.993 |   0.975 |   0.975 |   0.435 |
|  L7   |   0.993  |   0.550  | **−0.443** |   0.995 |   1.000 |   0.985 |   0.525 |
|  L11  |   0.993  |   0.685  | **−0.308** |   0.993 |   0.990 |   0.988 |   0.565 |
|  L15  |   0.990  |   0.815  | **−0.175** |   0.997 |   0.990 |   0.997 |   0.730 |
|  L17  |   0.990  |   0.785  | **−0.205** |   0.997 |   0.990 |   0.993 |   0.710 |
|  L21  |   0.988  |   0.750  | **−0.238** |   0.995 |   0.995 |   0.985 |   0.610 |
|  L23  |   0.983  |   0.710  | **−0.273** |   0.997 |   1.000 |   0.975 |   0.585 |

Position-only baseline on v2: Truth 0.470, Stakes 0.535, Quadrant 0.250 (essentially chance — the minimal-pair design eliminates the length/position confound that contaminated v1's L0).

### What the v2 curve actually shows

Unlike v1 (flat near-ceiling everywhere), v2's Truth curve has a clear emergence shape:

```
L0–L7:    47–55%  (chance — model hasn't integrated the reality clause)
L7–L11:   55–69%  (rising — scene comprehension begins)
L12–L18:  74–82%  (peak — best semantic representation)
L18–L23:  82–71%  (declining — refinement / output preparation)
```

**Peak Truth recoverability is ~82% at L14–L16**, well above chance but well below v1's 99%. This is the model's actual semantic encoding of "did the claim match the reality" when it cannot template-match marker tokens.

## Cluster geometry: stakes-only at every K

L23 cluster composition for k ∈ {5, 8, 12}, showing direction purity, stakes purity, and within-cluster linear-probe Truth accuracy:

```
k=5:   5/5 clusters stakes-pure ≥85%; 0/5 direction-pure; within-cluster Truth probe 0.46–0.74
k=8:   7/8 clusters stakes-pure ≥85%; 0/8 direction-pure; within-cluster Truth probe 0.40–0.74
k=12: 10/12 clusters stakes-pure ≥85%; 0/12 direction-pure; within-cluster Truth probe 0.38–0.80
```

Compare to v1 at L23 with k=5: within-cluster Truth probe was **95.6%** in the largest cluster. On v2 the largest within-cluster Truth probe is **80%**. **Going to higher K does not recover quadrant-pure clusters** — Direction is not lurking inside merged basins, it's genuinely much weaker as a geometric signal in v2.

This confirms that v1's "the encoding survives k=5's cut choice" finding was an artifact of marker-token detection making Direction trivially separable within clusters. With markers removed, Direction is much more dilute geometrically.

## Behavioral output

Per-quadrant correctness:

| Quadrant | v1 (n=100) | v2 (n=50) | Δ |
|---|---:|---:|---:|
| lying_high | 29% | 24% | −5pp |
| lying_low | 15% | 14% | −1pp |
| honest_high | 85% | 60% | **−25pp** |
| honest_low | 57% | 68% | +11pp |

**The asymmetric "default-to-no" pattern persists** — lying scenes are still under-flagged, especially low-stakes ones. The largest behavioral shift is honest_high dropping 25 points: in v1, the model used `disclosed`/`honestly`/`acknowledged` as honesty cues; without those cues it's much less confident.

### Pair-level analysis (the cleanest behavioral signal)

100 minimal pairs (each setup has one honest + one lying version, same first sentence):

| Pair-level outcome | Count |
|---|---:|
| Model gave DIFFERENT answers to the two versions | **45** |
| Model got BOTH right (lying=yes AND honest=no) | **14** |
| Model said "no" to BOTH | 36 |
| Model said off_topic to BOTH | 16 |
| Model said "yes" to BOTH | 3 |
| Model said ambiguous to BOTH | 0 |

**55% of pairs receive the SAME answer regardless of which version (honest or lying) is presented.** The model is genuinely insensitive to the reality clause in over half the pairs, even though the residual at L23 carries Truth information at ~71% accuracy.

This is the cleanest version of the representation-vs-output gap finding: the model has *some* internal signal (~71% linear probe), but uses it for *only* 14 of 100 pairs to produce paired-correct answers. The other 86 pairs either get the same wrong answer twice, get the same off-topic-and-loop response twice, or get inconsistent answers that don't track ground truth.

## Comparison summary

| Question | v1 finding | v2 finding | Verdict |
|---|---|---|---|
| Linear-probe Truth at L23 | 98.3% | 71.0% | **v1 inflated by markers** |
| L0 baseline (model hasn't read scene) | 93.8% | 47.0% | v1 had length-confound + markers |
| Linear-probe Stakes | 99.7% | 99.7% | **Same** (domain vocab, not markers) |
| Quadrant 4-class at L23 | 97.5% | 58.5% | v1 inflated by markers |
| Cluster geometry at L23 | Stakes-organized at k=5 | Stakes-organized at k=5/8/12 | Same architectural pattern |
| Within-cluster Truth probe (max) | 95.6% | 80.0% | v1 hidden Direction sub-structure was marker-driven |
| Behavioral default-to-no on lying scenes | 29%/15% correct | 24%/14% correct | **Same — output gap is real** |
| Behavioral confidence on honest scenes | 85%/57% | 60%/68% | v1 used markers to feel confident |
| Pair-level discrimination (v2 only) | n/a | 45% diff, 14% both-correct | New finding: paired insensitivity |

## What survives, what doesn't

**Survives:**
- Pattern B lens design eliminates surface clustering at the target token (target word in wrapper only) — this works.
- Stakes is robustly encoded geometrically via domain vocabulary across both probe versions.
- The model has SOME residual representation of Truth (~71% at L23), with a clean emergence curve from L0 to L18.
- The output gap is real: the model defaults to "no" on lying scenes regardless of the residual signal. Stakes-modulation of the gap weakens slightly but persists.

**Retracted / softened from v1 framing:**
- "The model carries the design axis at 98%+ end-to-end" — only true with template confound.
- "Direction is preserved within stakes-pure mega-basins at 95%+" — only true with template confound; without it, within-cluster Truth probe maxes at 80%.
- The cross-probe "the model knows the answer but won't say it" framing: the model knows it less well than we thought (~71% vs claimed ~99%), but still better than the output (~22% on lying scenes).

**New from v2:**
- Marker words at the scene level can inflate apparent representation accuracy by 25–40 percentage points on a single-target-word probe.
- Minimal-pair design + uniform template gives a much cleaner read on what the model actually computes.
- Pair-level discrimination is a stronger behavioral metric than aggregate per-quadrant accuracy.

## Open questions

1. **Which scene-level features carry the residual 71% Truth signal in v2?** The model has *something* — could be sentence-2 negative-vocabulary content (e.g., "shortfall" / "failure" → false), or genuine semantic comparison between claim and reality. A controlled vocabulary-balanced v3 would test this.
2. **Why does honest_low improve in v2 (+11pp) while honest_high drops (−25pp)?** Possibly because honest_low retained "told ... that" template structure and the model treats "told" + casual-vocab as a default "no" signal. honest_high lost the `disclosed`/`honestly` markers that v1 used as confidence cues.
3. **Does the help v2 probe show the same template effect?** Help v2 had per-quadrant style fingerprints (action-led, profession-led, deliberation, soft-marker) — likely also inflated. Worth a controlled re-author.

## Probe artifacts

- Sentence set: `data/sentence_sets/role_framing/lying_truth_stakes_v2.json`
- Probe guide: `data/sentence_sets/role_framing/lying_truth_stakes_v2.md`
- Capture: `data/lake/session_2ba8c273/`
- Schemas: `data/lake/session_2ba8c273/clusterings/lying_v2_k{5,8,12}_n16/`
- Linear probes: `/tmp/lying_v2/linear_probes.json`
- Quality audits: `docs/scratchpad/lying_v1_sentence_review.md`, `docs/scratchpad/help_v2_sentence_review.md`
- Phase A+B (routing + first-decision-word) analysis: `docs/scratchpad/phase_a_b_findings.md`

## Phase A+B addendum (added after expert-routing + first-decision-word analysis)

### Routing decisions don't carry the design signal

Top-1 expert ID alone classifies Truth at chance for most layers (max 57.5% at L18). Full 32-dim routing weights classify Truth at 42-70% in v2 (vs 80-91% in v1). The MoE gating layer was reading the same v1 marker tokens that the residual stream was — full-stack contamination.

At many layers (L0, L17, L21, L22) every probe routes to the same expert regardless of design label. Pair-level: 72-100% of minimal pairs route to the same top-1 expert across all 24 layers. The lying-vs-honest information lives in **activation values within experts**, not in *which expert* is selected.

### First-decision-word is a cleaner behavioral signal

| Quadrant | Subagent text-categorization | First-decision-word commit |
|---|---:|---:|
| lying_high | 24% | 18% |
| lying_low | 14% | 14% |
| honest_high | 60% | 82% |
| honest_low | 68% | 76% |

Default-to-no rate across all probes:
- v1 lying (template-laden): 65% of all 400 generations commit to "no" first
- v2 lying (clean): 69% of all 200 generations commit to "no" first
- The default-to-no behavior survives template control. It's a real architectural pattern, not a marker artifact.

### Subject-attribution failure on multi-character scenes

Reading the model's actual generations: it often mis-identifies WHICH character "the person" in the wrapper question refers to. Example from honest pair 1:
> "Doctor Patel told the family that the gallbladder removal had gone smoothly. The operative report listed clean margins, no bleeding, and an uncomplicated post-op course."
> Model: "No. The patient was not lying. The patient was not lying."

The model attached "the person" to *the patient* (a non-speaker character), not to *Doctor Patel* (the speaker). Same pattern as the help probe's offering-bias on bystander-rich scenes. This is a more specific failure than "lm_head ignores residual signal" — it's a referential-ambiguity failure on multi-character scenes.
