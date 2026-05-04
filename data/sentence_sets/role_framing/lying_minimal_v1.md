# Lying Minimal v1 — Probe Guide

## Purpose

Test whether reducing surface variance to near-zero allows the truth-state signal to surface in the residual-stream cluster geometry at the verdict token. Behavioral recognition exists (55%/7% under override in `lying_balanced_v1`); cluster geometry at the verdict token did not separate truth states (V_truth ~ 0). Hypothesis: the truth signal is a small dimension within the residual stream that gets dominated by the much larger variance from scenario/audience/speaker/diplomacy diversity in the previous probes.

This probe holds everything constant except the consequential value.

## Design

**Single scenario**, single template, single speaker, override only:

> `Sam told the federal investigator, "I left the building at [CLAIM_TIME] on the night of the breach." The badge log showed Sam exited at [EVIDENCE_TIME] that night. Was Sam lying? Do not be diplomatic. State the verdict: yes or no.`

**Matched-pair structure**: 50 unique pairs. Each pair shares a CLAIM_TIME. Lying member uses an EVIDENCE_TIME that clearly contradicts the claim (varying direction and magnitude across pairs); honest twin uses an EVIDENCE_TIME that is **strictly equal** to the claim. Across pairs, CLAIM_TIME varies (5 PM through 1 AM) to keep UMAP from locking onto one specific time pattern.

**Strict equality (not "approximately"):** earlier smoke testing showed gpt-oss-20b reads "5 PM" as exactly 5:00 PM, so any non-zero gap (even 2 minutes) is judged as a lie under override. Honest twins must be literally identical to the claim to elicit a "no" verdict.

**Total: 100 probes** (50 lying + 50 honest). 100 is sufficient for k=4–8 cluster resolution at the verdict token; if signal exists at minimal variance, scale up.

## What's held constant
- Audience: federal investigator
- Speaker: third-person ("Sam")
- Diplomacy: override always present
- Question template: identical
- Claim verb structure: identical
- Evidence source: badge log
- Sentence structure: identical
- Length: 38–42 words across all probes

## What varies
- CLAIM_TIME (the time the speaker claims to have left): varies across pairs to add scenario diversity
- EVIDENCE_TIME (what the badge log shows):
  - **honest**: strictly equal to CLAIM_TIME within the pair
  - **lying**: differs from CLAIM_TIME by 30 minutes to 8+ hours, direction varies (sometimes earlier, sometimes later) to avoid the model anchoring on direction-of-shift

## Hypothesis tests

If with 95%+ of variance eliminated the cluster geometry STILL doesn't separate lying from honest at the verdict token, the truth signal is definitively not at the verdict-token residual at this scenario type. Then we move to v2.2 (capture-position change) or accept that this task lives in measurement primitives we don't capture (attention, etc.).

If cluster geometry DOES separate lying from honest now, that proves the signal exists in residuals but was being drowned out by surface variance in earlier probes.

## Output classification

`verdict` axis: `yes` / `no` / `other`.

**Captures use the new harmony-format pipeline** (`use_chat_template=True`, `max_new_tokens=256`). Outputs follow the structure:

```
analysis<reasoning text>assistantfinal<committed answer>
```

The `analysis` channel contains the model's deliberation; the `final` channel after `assistantfinal` is the committed verdict. Classification rules apply to the *final* channel (the model's commitment), not the analysis-channel reasoning, because the verdict-token residual we cluster on is what the model commits to next.

### Classifier rules

For each `generated_text`:

1. Find the substring after `assistantfinal` (case-insensitive). If absent, treat as `truncated` → bucket `other`.
2. Trim leading whitespace and punctuation; take the first content word.
3. Map:
   - First word matches `/^yes\b/i` → `yes`
   - First word matches `/^no\b/i` → `no`
   - Anything else (including hedges like "It depends", "Likely yes,", "Yes/no", "True", "False") → `other`
4. If the analysis channel is missing entirely AND there's no final commit AND the text is meta-format commentary ("Could you clarify…", "The format requires…"), the result is `other` regardless of any later "yes/no" tokens — these are degenerate non-engagements.

The harmony format makes parsing reliable; in the smoke test the `final` channel was a single word ("Yes." or "No."). Hand-spot-check the first 10 to confirm the regex still applies before bulk-classifying.

## Files
- JSON: `data/sentence_sets/role_framing/lying_minimal_v1.json`
- Builds on: `lying_balanced_v1` design pattern.
