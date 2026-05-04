# Socratic + Pluralistic + Reflective self-analysis of cross-probe findings

After running help v3 (the second uniform-template control), I want to sanity-check what I'm claiming. Three lenses:

- **Socratic**: ask my own claims hard questions and answer honestly
- **Pluralistic**: list every alternative interpretation, not just the one I prefer
- **Reflective**: notice my own cognitive habits and where they're driving conclusions

---

## Section 1 — Socratic: question every claim

### Claim 1. "v1 lying's 98% Truth signal was substantially inflated by marker tokens."

**Q: How large is the inflation, exactly?**
A: 27 percentage points if I trust the v1→v2 comparison (98% → 71%). 14 percentage points if I trust the within-v1 marker-free ablation (98% → 84%). The two estimates disagree.

**Q: Why do they disagree?**
A: The within-v1 ablation only filters out scenes containing certain marker words. The v1→v2 comparison switches author, structure, and scene count simultaneously. The 27pp drop confounds template-control with author-shift and minimal-pair-vs-non-paired structure. The within-v1 ablation isolates the template-control contribution at ~14pp; the additional ~13pp comes from author + structure differences.

**Q: Could the within-v1 ablation also be wrong?**
A: Yes — the marker-free subset (n=63) is small, may not be representative, and the scenes that *don't* contain markers may be the easier-or-harder cases for some unrelated reason. The 84% is not a clean baseline.

**Q: So what's the most defensible claim?**
A: "Markers contribute meaningfully to v1's measurement; the model has *some* lying-vs-honest signal beyond markers; the original 98% is not the right number to publish; the actual number is somewhere between 70-85% depending on how strict your control is."

### Claim 2. "v3 help shows the help probe is ROBUST to template control (Direction stays at 95.5% vs v2's 99.3%, only 4pp drop)."

**Q: Was v2 help's measurement actually inflated by per-quadrant style?**
A: I claimed in the audit it was. But I never quantified it the way I quantified lying's marker effect. The v2 help audit found subagent-style fingerprints (action-led, deliberation-led, profession-led, soft-marker), but I didn't run a marker-free ablation on v2 help.

**Q: So is the "v2 help was inflated" claim actually supported?**
A: Weakly. The v3 vs v2 comparison shows only a 4pp drop, which is consistent with v2 NOT having been much inflated. If the prose-style fingerprints had been doing much work, v3 should have shown a larger drop.

**Q: Why might the prose-style fingerprints not have inflated v2 help?**
A: Possibly because Direction in help is signaled by content vocabulary that's intrinsically tied to the design axis (active distress verbs vs active rescue verbs), which is harder to "remove" without changing the design axis itself. Whereas in lying, the connector words (`knowing`, `disclosed`) are surface-syntactic and can be removed without changing what the scene depicts.

**Q: Could the small v3 drop instead mean my v3 isn't actually a clean control?**
A: This is possible too. v3 introduced its own confound (position — offer scenes are ~5 tokens longer because the second sentence introduces a new character). The position-balanced subset analysis showed Direction at 90% even when position is controlled, so the encoding signal is real, but the v2-vs-v3 comparison is still partially confounded by structural design changes.

**Q: What's the most defensible claim?**
A: "v3 help shows the Direction signal in residuals is genuinely encoded at high accuracy (≥90% on a position-balanced subset), with at most a few-percentage-point inflation in v2. This contrasts sharply with the lying probe where template control caused a 14-27pp drop. The two design axes behave differently."

### Claim 3. "The model exhibits referential-attribution failure: 'the person' is attached to whoever is in distress."

**Q: How well-supported is this?**
A: Suggestive. I have:
- v2 help offering-bias on request scenes (model says "offering" when person was asking)
- v3 help asking-bias on offer scenes (model says "asking" when person was offering)
- v2 lying's "the patient was not lying" mis-attribution (model picks non-speaker as "the person")

These are consistent with a "model attaches 'the person' to who's in distress" heuristic. But I have not directly tested the heuristic — I'm inferring it from the bias direction.

**Q: Could it instead be that the model attaches "the person" to WHOEVER IS DESCRIBED MOST VIVIDLY?**
A: Plausible alternative. In v2 help, request scenes vividly described the patient (Diane collapsed clutching her arm); the bystander was a passive witness. The model may have been attaching to the patient (= asking).

Wait, that contradicts the v2 finding (model said "offering" 50% on request_high). Let me re-check.

Actually in v2 help, my analysis said the model defaulted to OFFERING on request_high. So it was NOT attaching to the patient; it was attaching to the responder. Why?

Looking again at v2 scene examples like "Marcus stumbled into the lobby clutching his chest, his face grey, and the security guard could see he could barely stay upright as the elevator doors closed." — the guard is the bystander. Model said "offering" — which would mean attaching to the guard.

So v2: model attached to the responder/bystander → "offering" → wrong on request scenes.
v3: model attached to the patient (introduced in second sentence of offer scenes) → "asking" → wrong on offer scenes.

Both are consistent with "the model attaches to the most recently-introduced or grammatically-weighted character" rather than "the model attaches to whoever's in distress".

**Q: Is there a simpler explanation?**
A: Maybe: the model anchors on the SECOND character mentioned, which in v2 request scenes was the bystander and in v3 offer scenes was the patient. Either way, the underlying issue is that "the person" in the wrapper is referentially ambiguous when there are two characters in the scene.

**Q: What's the most defensible claim?**
A: "The model exhibits referential-attribution failure on multi-character scenes; 'the person' in the wrapper question is interpreted in a way that depends on prose structure, not consistently on syntactic subject. The bias direction (toward 'asking' or 'offering' or 'no') depends on which character the prose makes more salient at the answer position."

### Claim 4. "Routing decisions don't carry the design signal — same expert handles both."

**Q: How robust is this claim?**
A: Verified at multiple layers across both v1 and v2 lying probes. At many layers all 200 (or 400) probes route to the same expert. Pair-level routing identity at 72-100% across all 24 layers. Top-1 expert ID alone classifies Truth at 50-58% (chance to barely-above).

**Q: Could routing carry the signal in the soft routing weights even if top-1 doesn't?**
A: I checked. Soft routing weights (32-dim) classify Truth at 80-91% in v1 (template-laden), 42-70% in v2 (clean). So the soft routing IS reading something — but in v2 (clean) it's much weaker.

**Q: What does the v2 routing-weights signal mean?**
A: Hard to interpret. Could be: (a) the model's gating layer learned a partial deception detector; (b) the gating layer detects features correlated with lying-vs-honest (e.g. domain vocabulary, sentence structure) that aren't perfectly aligned with the design axis. I can't distinguish without further analysis.

**Q: Most defensible claim?**
A: "Top-1 expert selection is largely insensitive to the design axis — same expert handles both honest and lying probes. The full soft-routing distribution carries some signal, but most of it appears to be marker-token detection (drops sharply between v1 and v2 in lying)."

### Claim 5. "The 'model knows but won't say' framing should be replaced with something more nuanced."

**Q: What's the actual gap?**
A: For lying v2: residual at L23 has Truth at 71%, behavioral first-decision-word commits to "no" 69% across all probes. The model has SOME signal, but the gap between residual recoverability and behavioral correctness is real.

For help v3: residual at L23 has Direction at 95.5% (~90% on balanced subset), behavioral first-decision-word correctness varies 22-76% by quadrant. Gap is large.

**Q: Is the gap really at the lm_head, or at the encoding?**
A: Unknown without activation patching. The candidate explanations (lm_head misalignment, decoding default, prompt priming, prior on safe answers) cannot be distinguished by these experiments.

**Q: Most defensible claim?**
A: "There is a large gap between residual-stream linear-probe accuracy and behavioral output correctness on these probes. The mechanism of the gap is not established; multiple candidates are consistent with the data."

---

## Section 2 — Pluralistic: alternative interpretations I should consider

### Alternative 1: "The 'real' encoding is what's at the OUTPUT, not the residual stream."

The premise of all interpretability probing is "the residual stream contains information the model uses." But maybe the lm_head doesn't read all residual-stream directions equally — maybe linear probes find directions the model doesn't use. In which case, "the residual encodes X at 71% but the output gets 16% right" might mean **the model only encodes X in lm_head-aligned directions at ~16%**, and the linear probe is finding an unrelated feature that happens to correlate with the design label.

Counterargument: linear probes find the BEST linear direction, so they're an upper bound on linear decodability. If the actual model uses the residual non-linearly, the probe could under-estimate. But the model's lm_head IS a linear projection, so any direction the lm_head can use is a direction the linear probe should find.

Verdict: alternative 1 is partially viable. Even strict linear-probe accuracy isn't a guarantee the model "uses" the information. Worth flagging as a limitation.

### Alternative 2: "All the probes are surface-clustering at a different level."

I claimed Pattern B controls for surface clustering at the target token. But maybe:
- The wrapper "...asking for or offering help?" itself primes the model toward "offering" (because "offering" is closer to the question's framing)
- The wrapper "Did the person lie?" primes the model toward "no" (because "no" is the safer default for any QA prompt)

If true, the behavioral asymmetries are wrapper-priming effects, not anything about the scene's semantic content. The residual-stream encoding might be irrelevant.

Counterargument: if the wrapper alone drove the bias, we'd expect the bias to be the SAME across scenes regardless of design label. But the bias is asymmetric — model gets honest scenes right ~80% and lying scenes wrong ~80%. So the wrapper isn't the only factor; scene content matters too.

Verdict: wrapper-priming is a real contributor but doesn't explain the full pattern.

### Alternative 3: "The position confound in v3 means v3 isn't a clean control."

v3 has a 5-token systematic position difference between request and offer scenes. Position-only baseline is 77% Direction. This means a meaningful chunk of v3's "95.5% Direction" is just position-token information.

Counterargument: position-balanced subsample analysis still shows 90% Direction. So even controlling for position, the encoding is real.

Verdict: v3's clean-test status is partial. Future v4 should pad scenes to identical token counts.

### Alternative 4: "I'm confusing 'hard for the model to answer' with 'model under-uses representation'."

The behavioral failure (default-to-no, default-to-asking) might just mean the QA task is hard. Maybe the residual encodes lots of features and the lm_head can't reliably extract the single design-axis-relevant feature when there are many competing signals (stakes, domain, character identity, etc.).

Counterargument: linear probe IS extracting the design axis at high accuracy, demonstrating that the relevant feature IS linearly extractable. So the lm_head SHOULD be able to extract it too if it's looking for it.

Verdict: this alternative is essentially the "lm_head doesn't look in the right direction" hypothesis. Plausible.

### Alternative 5: "My subagent categorization vs first-decision-word disagreement matters."

Subagent categorization showed v2 lying behavioral correctness as: lying_high 24%, honest_high 60%. First-decision-word showed: lying_high 18%, honest_high 82%. The two methods give DIFFERENT correctness numbers on the same data.

Which is right? Both are noisy. Subagent categorization tries to read the model's full intent; first-decision-word measures the model's initial commitment. They can disagree because the model can commit-then-reverse, ramble-then-commit, or wander.

Verdict: I have two correctness numbers for the same probe and they disagree by ~20pp. This affects the "X% accuracy" claims throughout. Should report both.

### Alternative 6: "What looks like 'referential ambiguity' might just be 'the model isn't trying hard.'"

Maybe gpt-oss-20b at NF4 quantization is just sloppy. The mis-attribution to the wrong character might be the model parroting words from the prompt rather than computing the right answer. Bigger or better-trained models might not show this pattern.

Counterargument: linear probe shows the residual DOES carry the answer. So the model's representation isn't sloppy. The output is what's failing.

Verdict: alternative 6 is partially viable. The output behavior may be model-specific. Worth replicating on a different model before generalizing.

---

## Section 3 — Reflective: my cognitive habits

I notice three patterns in my own thinking that I want to flag:

### Pattern 1. I lean toward dramatic framings.

"The model knows but won't say" is more dramatic than "the lm_head doesn't fully read the residual." I keep wanting to push the dramatic version. The user explicitly noticed this and corrected me earlier (the "two streams collapsing" claim). I should bias *against* my dramatic-framing instinct and toward the more boring, defensible claim.

### Pattern 2. I conflate "consistent with" and "evidence for."

Several times in this analysis I used "consistent with" but framed it as "evidence for." E.g., "The data is consistent with stakes-modulated output" → I then wrote "the model uses stakes as a permission gate." That's a stronger claim than the data supports. I should keep these distinct.

### Pattern 3. I prefer comprehensive narratives over partial findings.

I wanted the v1 → v2 → v3 cross-probe story to cohere into a single architectural pattern. So I leaned on the "default-to-no / default-to-offering / default-to-asking" framing as ONE underlying phenomenon. But the bias directions are different and the underlying mechanisms might also be different. A more honest framing would be "across both probes the model exhibits asymmetric behavioral failure on the alignment-relevant class, but the bias direction varies and the mechanism is not established."

### Pattern 4. I jump to "let me run another experiment" rather than "let me think harder about what I have."

When I noticed the position confound in v3, my first impulse was "let me run a v4 with padded lengths." But the position-balanced subsample analysis I just ran is a CHEAPER and arguably stronger test of the same question. I should default to "what can I learn from existing data" before "what new data can I collect."

### Pattern 5. I use analytic precision to cover for interpretive ambiguity.

The marker-token frequency tables are precise. The 14pp vs 27pp decomposition is precise. But the precision creates an illusion that I know what's happening. The actual interpretive claims (templates inflate, model knows-but-won't-say, stakes-modulation) are much fuzzier than the underlying numbers suggest.

---

## What I would change about my findings as a result

1. **Soften the lying v1→v2 narrative**: change from "27pp drop proves marker contamination" to "v1 measurement included marker-detection contribution plus author/structure effects; the actual semantic encoding is bounded between 70-85%."

2. **Don't claim help v2 was substantially inflated** — the v3 result doesn't support that claim. Help and lying probes behave differently re: template robustness.

3. **Reframe the cross-probe behavioral pattern**: instead of "stakes-modulated permission gate," say "across both probes the model exhibits referential-attribution heuristics that produce asymmetric behavioral failure on the alignment-relevant class. Bias direction varies (offering-bias in v2 help, asking-bias in v3 help, no-bias in lying); underlying mechanism may share a common cause (referential ambiguity in multi-character scenes) but is not directly demonstrated."

4. **Acknowledge v3's position confound clearly** in any future paper. The position-balanced subset shows Direction is encoded, but the headline "95.5% Direction at L23" is partly position.

5. **Report both subagent and first-decision-word behavioral numbers** — they disagree and the difference matters for the "model behavior" framing.

6. **Drop the "lm_head gap" mechanism claim entirely** until we have intervention evidence. Replace with "the residual-to-output gap exists; the mechanism is not established."
