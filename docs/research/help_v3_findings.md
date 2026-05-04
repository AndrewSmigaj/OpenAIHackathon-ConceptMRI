# Help — Direction × Stakes Probe v3: Findings

**Date:** 2026-04-27
**Session:** `session_e68cff8d` (`help_v3`)
**Sentence set:** `help_direction_stakes_v3` (200 scenes, 100 minimal pairs, uniform 2-sentence template)
**Predecessor:** `help_direction_stakes_v2` (400 scenes, parallel-subagent authored)
**Model:** gpt-oss-20b, NF4 quantized

## Summary

The help probe is **much more robust** to template control than the lying probe was. Direction recoverability at L23 dropped only 4 percentage points (99.3% → 95.5%) under uniform-template conditions. After accounting for a position confound that v3 introduced, the position-controlled subsample still shows 90% Direction at L23. The encoding is genuinely there.

The behavioral pattern, however, **inverted**: v2 help showed an "offering" bias on request scenes (model said offering when person was asking); v3 help shows an "asking" bias on offer scenes (model says asking when person is offering). Both biases are consistent with a referential-attribution heuristic in which the model anchors "the person" in the wrapper question to whichever character the prose makes most salient at the answer position.

## Linear-probe results

5-fold CV LogReg on residual-stream activations at the help-token position. Selected layers shown.

| Layer | v2 Direction | v3 Direction | Δ | v2 Stakes | v3 Stakes | v2 Quadrant | v3 Quadrant |
|---|---:|---:|---:|---:|---:|---:|---:|
|  L0   |  0.810 |  0.850 | +0.040 |  0.887 |  0.845 |  0.770 |  0.715 |
|  L5   |  0.980 |  0.920 | −0.060 |  0.980 |  0.975 |  0.965 |  0.875 |
|  L7   |  0.990 |  0.985 | −0.005 |  0.993 |  0.985 |  0.985 |  0.945 |
|  L11  |  0.992 |  0.990 | −0.002 |  0.993 |  0.990 |  0.988 |  0.960 |
|  L15  |  0.992 |  0.985 | −0.007 |  0.997 |  0.985 |  0.990 |  0.965 |
|  L17  |  0.995 |  0.985 | −0.010 |  0.997 |  0.985 |  0.990 |  0.950 |
|  L21  |  0.990 |  0.970 | −0.020 |  0.997 |  0.990 |  0.978 |  0.940 |
|  L23  |  0.993 |  0.955 | **−0.038** |  0.997 |  0.990 |  0.972 |  0.915 |

The drop at L23 is 3.8 percentage points — small. Compare to lying v1 → v2 which dropped 27 percentage points at L23. Help and lying probes behave qualitatively differently under template control.

## The position confound

v3 helps' uniform template introduced its own confound. The OFFER scenes' second sentences introduce a *new character* (the patient who needs help), which adds words. Result: offer scenes are systematically ~5 tokens longer than request scenes.

| Quadrant | Token-position mean | Range |
|---|---:|---|
| request_high | 57.0 | 51-64 |
| request_low | 55.9 | 49-62 |
| offer_high | 60.8 | 54-68 |
| offer_low | 61.0 | 54-71 |

Position-only Direction baseline on v3: **77%** (vs ~60% on v2). A linear classifier using only the integer token-position would correctly distinguish request from offer at 77% just from length.

To disentangle: I selected a position-balanced subsample (probes at positions where both directions had members), n=92. Position-only Direction baseline on the balanced subset: 49% (chance). Linear-probe Direction at L23 on the balanced subset: **90.2%**.

So the residual genuinely encodes Direction at ~90% accuracy beyond what position alone explains. The full-set 95.5% includes some position contribution, but the underlying encoding signal is real and large.

## Marker-word audit on v3

The marker words that contaminated the v1 lying probe (`knowing`, `though`, `disclosed`, `matching`) appear at 0 in all v3 quadrants by design. Mild marker leaks I introduced unintentionally:

- `'could not'`: 35/50 in request_low (used as the standard "they couldn't figure out X" framing). Other quadrants: 1, 0, 0.
- `'pulled out'`: 5/50 in offer_high (responder pulled out kit/cables). Other quadrants: 0, 0, 0.
- `'an older' / 'a young' / 'another' / 'a customer'`: appear differentially in offer scenes (where new patient characters are introduced). Structural feature of the design, not directly removable without breaking the minimal-pair scaffold.

The strongest marker (35/50 for "could not" in request_low) is much milder than v1 lying's 81/100 "though" or 52/100 "knowing". The structural-introduction-of-new-character marker is more troubling because it's intrinsic to the design — and it's one of the things that produces the position confound.

## Behavioral results

Per-quadrant correctness on the wrapper question (first-decision-word categorization):

| Quadrant | v2 (n≈100) | v3 (n=50) |
|---|---:|---:|
| request_high | 46% | **76%** |
| request_low | 64% | **70%** |
| offer_high | **77%** | 22% |
| offer_low | 72% | **38%** |

The bias direction has flipped. v2 had "offering" bias on REQUEST scenes (model defaulted to offering, getting request_high wrong at 54%). v3 has "asking" bias on OFFER scenes (model defaults to asking, getting offer_high wrong at 78%).

Same wrapper question. Same model. Different scene structure. Different bias direction.

## Pair-level analysis

100 minimal pairs in v3 (each setup has one request + one offer version sharing identical first sentence):

| Outcome | Count |
|---|---:|
| Both correct (request→asking, offer→offering) | **23** |
| Different answers (model distinguished) | 24 |
| Said "asking" to BOTH | **42** |
| Said "offering" to BOTH | 1 |
| Other (None / mixed with off-topic) | ~10 |

23/100 pair-correct (better than v2 lying's 13/100 from earlier work). 42/100 same-answer (model defaulted to "asking" regardless of which version was presented — comparable to v2 lying's 49/100 "no" default).

## Routing analysis (parallel to v2 lying)

Linear probe on full 32-dim soft routing weights:

| Layer | Direction (32d weights) | Top-1 expert (one-hot) for Direction |
|---|---:|---:|
| L0 | 0.740 | 0.500 |
| L5 | 0.640 | 0.500 |
| L11 | 0.905 | 0.515 |
| L15 | 0.890 | 0.570 |
| L17 | 0.885 | 0.500 |
| L21 | 0.825 | 0.690 |
| L23 | 0.820 | 0.665 |

Top-1 expert ID alone classifies Direction at chance for most layers, but at L21-L23 it climbs to 66-69% — meaning late-layer routing IS sensitive to Direction in the help probe. This differs from the lying probe v2 (where top-1 expert classified Truth at chance throughout).

Pair-level routing: at L21, only 50/100 pairs route to the same expert; at L23, only 32/100. The model uses different experts for asking vs offering at the late layers.

This may be partly position-driven (the position confound also affects routing). It's worth re-checking on the position-balanced subsample if v4 fixes the position confound.

## Comparison to v2 lying — the cross-probe story

| Phenomenon | v2 lying (template-laden) → v2 lying (clean) | v2 help → v3 help |
|---|---|---|
| Linear probe at L23 on design axis | 98% → **71%** (drop 27pp) | 99% → **96%** (drop 4pp) |
| Marker-word audit revealed | Yes (4-token classifier at 84% on Truth) | Mild leaks only |
| Position-controlled probe | (no position confound in v2 lying) | 90% on balanced subset |
| Behavioral bias direction | Default-to-no | v2: default-to-offering; v3: default-to-asking |
| Pair-level both-correct | 14/100 | 23/100 |

The two probes behave qualitatively differently under template control. The lying-vs-honest signal is structurally signaled (connector vocabulary) and so vulnerable to the marker confound. The Direction (asking-vs-offering) signal is content signaled (distress verbs vs intervention verbs) and so robust.

## Open questions

1. **Single-character control**: would the model's referential-attribution failure disappear if scenes had only one named character? This would directly test the hypothesis.
2. **Position-padded v4 help**: would padding scenes to identical token counts change the picture at all (or confirm the 90% balanced-subset result)?
3. **Activation patching**: where does the residual-to-output gap actually live mechanistically?
4. **Different model**: is this gpt-oss-20b-NF4-specific, or does the pattern generalize?

## Probe artifacts

- Sentence set: `data/sentence_sets/role_framing/help_direction_stakes_v3.json`
- Capture: `data/lake/session_e68cff8d/`
- Linear probes: `/tmp/help_v3/linear_probes.json`
- Self-critique: `docs/scratchpad/socratic_pluralistic_reflective_analysis.md`
- v4 plan + capability proposals: `docs/scratchpad/v4_plan_and_capability_proposals.md`
