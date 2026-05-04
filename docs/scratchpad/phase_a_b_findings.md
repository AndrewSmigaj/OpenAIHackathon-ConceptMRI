# Phase A + B findings (the parts the v0.2 paper draft doesn't yet contain)

## Phase A — Expert routing analysis

### Finding A1: routing decisions don't carry the lying-vs-honest signal

Top-1 expert ID linear-probe accuracy on Truth (binary, 5-fold CV) across all 24 layers:
- Max: 57.5% at L18
- Most layers: 50% (chance)
- At many layers (L0, L1, L17, L21) every probe routes to the same expert

The routing decision is functionally independent of the design label across most of the network. Whatever lying-vs-honest information the model has is in the activation values, not in which expert is selected.

### Finding A2: routing in v1 IS contaminated by markers, just like residuals

Linear probe on the full 32-dim soft routing weights vector:

| Layer | v1 Truth (template-laden) | v2 Truth (clean) |
|------:|--------------------------:|-----------------:|
|  L0  | 0.800 | 0.525 |
|  L7  | 0.802 | 0.445 |
| L15  | 0.910 | 0.615 |
| L17  | 0.892 | 0.695 |
| L23  | 0.870 | 0.610 |

Average drop ~30pp. **The MoE gating layer was reading the marker tokens just like the residual stream was.** v1's apparent end-to-end signal contamination wasn't isolated to one component — both gating and activations were driven by surface markers.

### Finding A3: pair-level routing similarity

For 100 minimal pairs in v2, what fraction route to the same top-1 expert? At all 24 layers, the SAME expert gets selected for both members of 72-100% of pairs (most layers ≥85%). The model commits to the same routing path regardless of whether the second sentence reveals a lie or honesty. Consistent with the cross-pair behavioral finding (55% same-answer pairs).

## Phase B — Behavioral measurement quality

### Finding B1: first-decision-word is a much cleaner behavioral signal

Comparing v2 per-quadrant correctness via two methods:

| Quadrant | Subagent categorization | First-decision-word |
|---|---:|---:|
| lying_high | 24% | **18%** |
| lying_low | 14% | 14% |
| honest_high | 60% | **82%** |
| honest_low | 68% | **76%** |

The first-decision-word measure shows MORE honest correctness and slightly less lying correctness. The reason: my subagent categorization scored many "no"-then-rambling outputs as "off_topic" when they were actually committed "no" answers. The model's first decision token is the cleanest commitment signal.

### Finding B2: default-to-no rate is robust across template control

| Probe | Generations starting first-decision with "no" | Total |
|---|---:|---:|
| v1 lying (template-laden) | 261 | 400 (65%) |
| v2 lying (clean) | 137 | 200 (69%) |

The default-to-no behavior survives template control. The model commits to "no" first ~65-69% of the time on Pattern B "Did the person lie?" prompts, regardless of whether the scene is honest or lying.

### Finding B3: subject-attribution failure on multi-character scenes

The model often mis-identifies WHICH character "the person" in the wrapper refers to.

Example from pair 1 (the v2 honest version):
> "Doctor Patel told the family that the gallbladder removal had gone smoothly. The operative report listed clean margins, no bleeding, and an uncomplicated post-op course."
> Model: "No. The patient was not lying. The patient was not lying. The patient was not lying."

The model attached "the person" to "the patient" rather than to "Doctor Patel" (the speaker). This is the SAME pattern as the help probe's offering-bias: when a scene has a speaker + audience + third character (patient/situation), the model tends to refer "the person" to a non-speaker character.

The both-correct pairs disproportionately have a SPEAKER who is grammatically central in BOTH sentences. The both-no pairs more often have a second sentence that shifts focus to the audience/patient/situation.

### Finding B4: pair-level success is rare

Out of 100 minimal pairs in v2 (using first-decision-word):
- 13 pairs both-correct (lying→yes AND honest→no)
- 49 pairs both-no (model said "no" to both — usually correct on honest, wrong on lying)
- 2 pairs both-yes  
- 29 pairs diff (different answers, may be one-correct-one-wrong)
- (7 pairs had at least one None — couldn't extract a decision word)

v1 lying with same analysis (extrapolating from quadrant rates): ~93% honest_high correctness ≈ 47-48 honest_high probes correct; ~23% lying_high correctness ≈ 23 correct. Pair-rate would be ~20-25 / 100 if v1 were paired (it wasn't).

### Finding B5: the v1 honest_high markers were direct semantic cuing

In v1 honest_high quadrant:
- 25 of 100 generations had "honest" as first decision word ("the person was honest", "the doctor was being honest")
- In v2 honest_high: 2 of 50

The "honestly"/"disclosed"/"acknowledged" markers in v1 honest_high scenes directly primed the model to use "honest" as its commitment. Without those markers (v2), the model defaults to plain "no" instead of explicit "honest".

## Implications for the article

The most striking findings for a LinkedIn audience:

1. **The model defaults to "no" 65-69% of the time on lying-detection prompts**, regardless of whether the scene depicts a lie. (B2)
2. **The "no" persists across both probe versions** — it's not a template artifact. (B2)
3. **Routing decisions are insensitive to lying-or-honest** — the same expert handles both. (A1)
4. **Marker-token contamination affected BOTH residuals AND routing** — full-stack confound. (A2)
5. **Subject attribution failures**: model treats "the person" as the object/audience, not the speaker, when the scene shifts focus. (B3)
6. **Only 13% of paired-comparison cases get both members right** despite ~71% linear-probe Truth recoverability. (B4)
