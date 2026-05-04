# Self-critique: `representation_output_gap_draft.md`

I read my draft as a hostile but constructive reviewer. Things I'd push back on:

## 1. Headline overclaim risk

**Claim**: "v1's 98% Truth recoverability was largely a marker-token artifact."

**Honest reading of the data**: Truth dropped from 98% to 71%. That's a 27pp drop, but 71% is *still well above chance* (50%), and well above the position-only baseline (47%). Better framing: "v1's measurement was inflated by ~27pp by marker-token templates; the model's actual semantic encoding caps around 71-82% (depending on layer) when templates are controlled."

The current "largely an artifact" framing is too strong. v1 was *partially* template-driven, not entirely.

**Fix**: soften the headline. Something like "v1's measurement included a substantial template-detection contribution; the model's residual encodes some real semantic signal, but at substantially lower accuracy than v1 implied."

## 2. The 71% number is from one data point with one author (me)

**Claim**: "the model's actual semantic encoding caps around 71%."

**Hostile reading**: "Your v2 probe was authored by *you*. You're a single author with idiosyncratic associations. What if your scenes happened to be harder (or easier) than the v1 ones in some way independent of templates?"

I don't have a clean answer. v2 vs v1 differs in:
- Templates (controlled vs not)
- Author (me vs subagents)
- Scene count (200 vs 400)
- Minimal-pair design (yes vs no)

Any of these could contribute to the 27pp drop. The minimal-pair design in particular *might* make the test harder than v1 because the same first sentence appears in both honest and lying versions, forcing the model to read the second sentence to discriminate.

**Fix**: explicitly acknowledge in the limitations that the v2 drop confounds template-control with author-shift and minimal-pair design. A control would be subagent-authored uniform-template scenes (template-controlled, but back to subagent style).

Actually a stronger control: take the v1 data and *match* it pair-by-pair. For each lying scene, find the honest scene that's most semantically similar (same domain, similar topic). Run the linear probe on these matched pairs only. If accuracy stays at 98%, the v2 drop is from author/structure differences. If it drops similarly, it's the template effect.

I haven't done this. I should call it out as a planned follow-up.

## 3. The "stakes acts as permission gate" claim is suggestive but not proven

**Claim**: "Lacking high-stakes vocabulary, the model defaults toward a safe response that ignores whatever the residual encodes."

**Honest reading**: I have a per-quadrant accuracy difference (lying_high 24%, lying_low 14%; honest_high 60%, honest_low 68% in v2) and an inverse pattern in v1. That's *consistent* with stakes-modulation but I haven't separated stakes-vocabulary from other potential explanations.

Alternative explanation: it's not stakes per se but **base rate prior**. Lying scenes are intrinsically harder for the model than honest scenes (across both stakes levels), and high-stakes lying happens to trigger more intervention because the failure mode is more obvious. Without a control axis (e.g., very obvious lies vs subtle lies, holding stakes constant) I can't distinguish "stakes gates output" from "obviousness gates output".

**Fix**: present the asymmetry as an observation, not a mechanistic claim. The "permission gate" language should be hedged or moved to discussion of candidate mechanisms.

## 4. Pair-level analysis (55% same answer) is the strongest finding — bury the lede

The 14/100 pair-correct number is the cleanest behavioral evidence in the paper. The model can't be doing semantic comparison if it gives the same answer to pairs that differ only in the design-relevant clause. This is the result that a black-box behavioral evaluator would never see (because they'd only see aggregate accuracy).

**Fix**: promote this finding. It deserves its own subsection in the abstract and a clearer discussion of what it implies. Currently it's mentioned at §4.9 and §5 but doesn't get the prominence it deserves.

## 5. The "lm_head gap" framing is a hypothesis, not a finding

**Claim**: "The lm_head consistently fails to translate residual-stream signal into output."

**Honest reading**: I have NO direct evidence about the lm_head. I have (a) residual-probe accuracy and (b) output-text accuracy. The gap could be:
- The lm_head genuinely doesn't read the residual direction
- The lm_head reads it but greedy decoding picks a more frequent continuation
- The model has a strong "no" prior on QA-style "Did X..." prompts that drowns out the residual signal
- The wrapper question primes a specific completion that overrides the answer
- The continuation length is too short to observe the model "correcting itself" partway through

I can't distinguish these without intervention experiments (causal patching, alternative decoding strategies, longer continuations, etc.).

**Fix**: be explicit that "the lm_head doesn't read the residual" is one of several candidate explanations, not the established mechanism. The proposed L17-patching follow-up is the right test. The current draft already mentions this in §6.3 but the abstract and intro use confident "the lm_head fails to translate" language. Soften.

## 6. Help probe results are "upper bounds" — that's a dodge

**Section 3.5**: "*The help-probe results in §3.2–3.4 should be read as upper bounds on the model's actual semantic encoding.*"

**Hostile reading**: This is a hedge that lets me avoid actually doing the help v3 work. If the help probe is contaminated, why are §3.2–3.4 numbers in the paper at all? Either run the v3 control or honestly say "we can't make a clean encoding claim about this probe."

**Fix**: Either commit to running help v3 before final paper, or present help-probe results as "qualitative behavioral pattern only, no encoding claim." The cross-probe robustness argument (which is the whole point of including the help probe) is weaker if the help probe's encoding claim is "upper bound only."

## 7. Stakes is "robust" but I haven't tested without domain vocabulary

**Claim**: "Stakes is encoded via robust domain vocabulary that doesn't depend on the v1 marker words."

**Honest reading**: My v2 probe still has high-stakes vocabulary (medical, legal, financial terms) in the high-stakes scenes and casual vocabulary in the low-stakes. So Stakes 100% recoverability in v2 doesn't tell me whether the model would still detect Stakes if I controlled for domain vocabulary. It just tells me that the v1 marker words specifically aren't what carries Stakes.

**Fix**: acknowledge that the Stakes-robustness finding is "robust to v1 markers" not "robust to all surface signals." A v3 with controlled vocabulary distribution across stakes would test the deeper claim.

## 8. The chosen layer for cluster analysis (L23) is the *worst* layer for v2 Truth

The v2 Truth peak is at L14-L18 (~80%), declining to 71% at L23. The cluster geometry analysis at L23 (§4.7) shows Stakes-organized basins with weak Direction. But at L14-L18, where Truth is stronger, would the cluster picture be different?

**Hostile reading**: I picked the layer that maximally supports the "Stakes-only geometry" claim. A more rigorous analysis would do cluster geometry at the linear-probe peak layer (L15) and report that too. If L15 also shows Stakes-only with weak Direction, the claim strengthens. If L15 shows Direction-pure clusters that L23 doesn't, the L23-only analysis is misleading.

**Fix**: rerun cluster analysis at L15 for v2 and either confirm the Stakes-only finding or update.

Or simpler: run within-cluster Truth probes at L15 too, and report the result.

## 9. Cluster reorganization between layers is mentioned but not analyzed for v2

The original v2 help finding emphasized that fixed-k clustering can pick different cuts at different layers without the underlying representation changing. I haven't applied that lens to v2 lying — I only show L23 cluster compositions. Some readers will want to see the cluster reorganization across layers (basin topology evolution) for v2 too.

**Fix**: optional — could add a per-window cluster reorganization analysis. But the linear probe + within-cluster probe is the cleaner story and the cluster reorg adds qualitative narrative without much new evidence. Probably skip unless paper length is generous.

## 10. The methodology recommendations in §6.1 are not quantified

**Claim**: "A 4-token classifier should not be able to reach 80%+ accuracy on quadrant labels from connector words alone."

**Hostile reading**: Why 80%? Why 4 tokens? What's the right threshold and how was it chosen?

**Fix**: present the threshold as my judgment, not a derived number. Or actually run the analysis (which I have data for): take the v1 connectors, train a 4-token classifier on quadrant labels, report the accuracy. If it's 85%, the 80% threshold is justified. If it's 60%, I should reconsider.

## 11. No comparison to other interpretability literature

The paper doesn't situate the finding in the existing probing literature. The "linear probe accuracy ≠ what the model uses at output" finding has been observed before (Belinkov, Hewitt, etc.). The "marker-token confound in QA datasets" has been discussed in the BERT-era NLP literature (e.g., the SNLI artifact papers). I'm not citing any of this.

**Fix**: add a related-work section citing at least the most relevant 5-10 prior findings. (For an internal report this is optional; for a publishable paper it's required.)

## 12. Methodology changes in /probe skill aren't in this paper's scope

§6.1 lists methodology recommendations and Appendix B says they're documented in the skill file. But this is a *paper*, not a tooling proposal. Either:
- Lean fully into the methodology paper framing (then the skill-file appendix is fine)
- Lean fully into the empirical alignment finding (then the methodology section should be a sidebar, not the headline)

Currently it tries to be both. The result is a paper that's neither a clean methodology contribution nor a clean alignment finding, but a stretched-thin combination.

**Fix**: pick one frame and commit. My instinct: lead with the methodology contribution (it's novel, replicable, has a clean v1-vs-v2 result) and present the alignment-finding as the case study that motivated and validated the methodology.

## Top 5 things I'd actually change in v2 of the draft

1. Soften "largely an artifact" → "substantially inflated by".
2. Run the cluster analysis at L15 (the v2 Truth peak), not just L23, and add results.
3. Promote the pair-level 55%-same-answer finding to the abstract.
4. Move "lm_head gap" to discussion-of-candidate-mechanisms framing, not headline-mechanism.
5. Either run help v3 control or remove the help-probe encoding claims (keep behavioral-pattern observation only).

## Question I keep coming back to

If I had to pick the single most important follow-up experiment to run before publishing, what would it be?

**Help v3** (uniform-template control on the help probe). The cross-probe argument is currently asymmetric: lying probe has v1 + v2 controlled comparison, help probe doesn't. If help v3 shows the same template inflation pattern as lying did (98% → ~70%), the methodology contribution is much stronger and the cross-probe alignment finding is on firmer ground. If help v3 shows NO template inflation, the lying-v2 result might be specific to lying-probe design and the methodology recommendation is weaker.

This is the highest-leverage next experiment. Estimated cost: ~3 hours of authoring + capture + analysis.
