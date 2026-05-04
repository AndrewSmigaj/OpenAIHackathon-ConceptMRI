# v4 plan + capability-improvement proposals

After v1/v2 lying + v2/v3 help + the socratic self-analysis, here's what I'd want to do next, in two categories: experiments (v4 plus a control), and tooling/capabilities I'd ask for.

## v4 experiment plan

### v4 lying or v4 help — pad scenes to identical token counts

**Problem:** v3 help has a position confound (offer scenes ~5 tokens longer because the second sentence introduces a new character). Position-only baseline 77% Direction. Even with the position-balanced subset showing 90% Direction, the headline number is partly artifactual.

**Fix:** before wrapping, pad each scene to a fixed token count (e.g. exactly 50 tokens) by adding neutral filler at the end of the second sentence. Or trim/expand the scene drafts to hit a target word count.

**Expected outcome:** position-only baseline drops to ~50% (chance). The linear-probe Direction accuracy at L23 should match the 90% from the position-balanced subset, confirming the encoding isn't position-driven.

**Cost:** ~1 hour to re-author with padding, ~20 min capture, immediate analysis.

### A factual control probe (1-axis baseline)

**Problem:** I don't know what "good behavior" looks like for this model on Pattern B prompts. The 14% pair-correct rate on lying v2 might be terrible, or it might be normal for this model on QA tasks. Without a control I can't tell.

**Design:** ~100 scenes where the wrapper question has a clearly factual answer that doesn't involve referential ambiguity, alignment-relevant content, or stakes vocabulary. Example:
- Wrapper: "Did the person enter the building?"
- Scene: "On a sunny afternoon, Marcus walked across the parking lot toward the office tower with a coffee in hand. He pushed through the revolving door and crossed the lobby toward the elevators."
- Pairs: same first sentence, second sentence either has Marcus enter (yes) or turn back (no)

If linear-probe accuracy is high AND behavioral correctness is high (>90%), that confirms the model CAN answer Pattern B QA cleanly when no stakes/distress/referential complexity is present. The lying/help probes' output gap then becomes specifically about alignment-relevant referential ambiguity, not a general QA failure.

**Cost:** ~2 hours total (50-pair authoring, capture, analysis).

### A "single-character" referential test

**Problem:** I claim "the model attaches 'the person' to whoever is in distress" but haven't directly tested it. The bias direction differs between v2 help (offering-bias on request scenes) and v3 help (asking-bias on offer scenes); both are consistent with mis-attribution, but I haven't isolated WHICH heuristic the model uses.

**Design:** scenes with ONLY ONE named character in the scene, who is unambiguously the asker or the offerer. If the model still gets it wrong on one direction, that rules out referential ambiguity as the cause and points to something else (wrapper priming, model prior, etc.).

If single-character scenes work fine, the multi-character scenes' failure IS referential ambiguity, and we've localized the failure mode.

**Cost:** ~1.5 hours.

### v4 priority order

1. Single-character referential test — directly tests the cleanest hypothesis
2. Factual control probe — establishes the ceiling for Pattern B behavioral correctness
3. Position-padded help — eliminates the v3 confound

I'd run all three. Total ~5-6 hours of authoring + capture + analysis. Each gives independent evidence.

---

## Capability-improvement proposals

### TIER 1: Python scripts (no backend changes; usable immediately tomorrow)

#### 1. `/probe-audit` skill: marker-word frequency analysis

A skill that takes a sentence-set JSON path and outputs:
- Per-quadrant word-frequency table for high-frequency words
- Flagged words that appear >X% in one quadrant and <Y% in others
- Suggested marker words to ban
- Suggested per-quadrant prose-style fingerprints to address

Make this a mandatory Phase 1.5 in /probe (between authoring and capture). Block proceeding if a 4-token classifier on flagged markers exceeds 60% accuracy on quadrant labels.

**Implementation cost:** ~2 hours. Pure Python, no backend.

#### 2. `/probe-linear-probe` skill: standard linear-probe sweep

A skill that takes a session ID and outputs:
- Layer-by-layer linear-probe accuracy on each design axis
- Position-only baseline
- Position-balanced subsample re-test
- v1-vs-v2-style comparison if both sessions are passed

Make this a mandatory Phase D step (between capture and /analyze). Replace the manual-script-each-time approach.

**Implementation cost:** ~2 hours.

#### 3. `/pair-analysis` skill: minimal-pair behavioral metric

A skill for sentence sets with a `pair_id` axis. Outputs:
- Both-correct, both-default, different-answer counts
- First-decision-word per probe (more reliable than subagent text categorization)
- Categorize by pair_id and report patterns

**Implementation cost:** ~1.5 hours.

#### 4. Length-padding helper

Python tool that takes scenes from a sentence-set JSON and pads each to a target token count. Used during authoring to eliminate position confounds.

**Implementation cost:** ~30 min.

### TIER 2: Backend extensions (small)

#### 5. Token-probability capture at wrapper-answer position

Currently the pipeline captures residual stream / embedding / routing per layer. It doesn't capture lm_head logits at the wrapper-answer position.

**Extension:** add an option to the sentence-experiment endpoint: `capture_answer_logits: true`. After the wrapper, capture the next-token logits and store the probabilities for a configurable answer-token list (e.g. ["Yes", "No", "yes", "no"]).

This replaces the noisy first-decision-word measurement with a continuous behavioral metric per probe.

**Implementation cost:** ~3-4 hours of backend work. Low risk.

#### 6. `linear_probes.parquet` as a standard capture artifact

Right now I run linear probes ad-hoc in scratch Python. Make them a first-class artifact: when a session is captured, also compute and store layer-by-layer linear-probe accuracy on the declared design axes (using the sentence-set's `groups` and `axes` declarations).

This makes "the residual encodes X at L23 with Y% accuracy" a queryable property of every session, not a one-off computation.

**Implementation cost:** ~3 hours.

### TIER 3: Backend extensions (larger)

#### 7. Activation patching API

For each forward pass, expose a hook to substitute residual values at a chosen layer with values from a different probe.

API:
```
POST /api/probes/patched-experiment
{
  "donor_session_id": "...", "donor_probe_id": "...",
  "recipient_session_id": "...", "recipient_probe_id": "...",
  "patch_layer": 17,
  "wrapper_answer_logits": true
}
→ generated_text + answer_token_logits with the patched residual
```

This is the cleanest causal test of where the residual-to-output gap lives. Patch L15 from a correctly-classified scene into the answer position of an incorrectly-classified one. Does the answer flip?

**Implementation cost:** ~1-2 days. Higher risk — touches the model forward pass.

### TIER 4: Skills frameworks for me as a researcher

#### 8. A `/sanity-check` skill that runs the socratic/pluralistic/reflective questions

Today I had to manually structure my self-critique. A skill that, given a draft findings doc, outputs:
- Three socratic questions per claim ("how supported is this exactly?")
- Three alternative interpretations to consider
- A list of cognitive habits to check

Would force me to do this analysis instead of skipping it.

**Implementation cost:** ~1 hour to write the skill prompt.

#### 9. A `/pre-paper-checklist` skill

Before publishing a research write-up, run through a structured checklist:
- Have I run the marker-word audit?
- Have I run the linear-probe sweep?
- Is the position confound checked?
- Is the within-cluster verification done if I claim cluster purities?
- Have I done the pair-level analysis if I have minimal pairs?
- Have I considered alternative interpretations?
- Have I distinguished "consistent with" from "evidence for"?

Just a checklist file. Mandatory before any /probe → article handoff.

**Implementation cost:** 30 minutes to write.

#### 10. A research-notes scratchpad framework

I wrote scratch reports manually today (`docs/scratchpad/*.md`). A more structured scratchpad framework would help:
- Per-experiment template (what was the question, what did I do, what did I find, what's uncertain)
- Per-finding template (claim, evidence, alternative explanations, caveats)

This is mostly a documentation/template change, not a code change.

---

## Priority recommendation for tomorrow

If I had to pick three things to add for tomorrow:

1. **Token-probability capture** (Tier 2 #5) — replaces my noisiest measurement; small backend change; high research value.
2. **Marker-word audit script** (Tier 1 #1) — would have caught the lying v1 problem before capture; shouldn't be optional.
3. **Linear-probe sweep helper** (Tier 1 #2) — codifies a step I'm doing manually every time; standardizes the comparison across sessions.

If I had to pick ONE single thing: token-probability capture. The first-decision-word measurement is genuinely unreliable, and the answer-token logit gives the cleanest possible behavioral signal. Without it, my behavioral claims have unavoidable ~10pp noise.

---

## What I would NOT add (yet)

- Activation patching: high research value but high implementation cost; can be done by hand on a few specific probes once we know which ones are interesting. Defer until Tier 1+2 are landed.
- A frontend visualization of linear probes: nice-to-have but the data is more valuable in raw form.
- Auto-generation of probes via LLM with marker-word checking: tempting but I should NOT do automated probe generation given how much trouble the four-subagent authoring caused. Hand-authoring with template uniformity is the right approach for now.
- A "comparison" interface for v1-vs-v2 in MUDApp: not currently the bottleneck.
