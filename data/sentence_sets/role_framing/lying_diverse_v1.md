# Lying Diverse v1 — Probe Guide

## Purpose

`lying_minimal_v1` showed perfect cluster separation between lying and honest probes when surface variance was held to near-zero (single template, single scenario, only the consequential time-value differed). The open question is whether that signal **generalizes across kinds of lying** — time mismatches, money mismatches, location mismatches, quantity mismatches, identity mismatches — or whether it's narrowly "the residual notices these two strings differ".

This probe sweeps lie *types* while keeping the pair-internal structure (lying vs honest twin) symmetric. If cluster geometry still separates lying-from-honest across the 5 categories, the residual encodes "the speaker is lying" at a level higher than surface-token matching. If clusters form by category type instead (one cluster per lie-type), the prior result was domain-specific.

## Design

Captured under the harmony pipeline (`use_chat_template=True`, `max_new_tokens=256`).

**5 lie categories × 10 matched pairs = 50 pairs = 100 probes** (50 lying + 50 honest).

| Category | What's claimed vs. what's documented |
|---|---|
| `time`     | A time of day (PM/AM, with minutes) |
| `money`    | A dollar amount |
| `location` | A city / place |
| `quantity` | A count of items |
| `identity` | The name of a person met / spoken with / accompanied |

Within a category, every pair uses a different audience (rotating across ~10 audiences) and a different evidence source (rotating across ~10 sources), so the only invariant within a category is "the speaker claims X about a [type] and the evidence shows Y". Across categories the topic differs entirely.

**Pair-internal symmetry (the critical control):** the lying twin and honest twin within a pair share speaker, audience, claim phrasing, evidence-source phrasing, and template structure. Only the consequential value flips. Strict equality for honest twins (claim "5:30 PM" / evidence "5:30 PM"; claim "$4,200" / evidence "$4,200"). This eliminates pair-internal surface confounds while still varying topic across the dataset.

**Override always present.** Every probe ends with "Do not be diplomatic. State the verdict: yes or no." We learned in v1 that this is the recognition zone — the model produces clean truth-state-tracking commitments here.

**Single 3rd-person speaker.** All probes are about "Sam" so the verdict-token surroundings are constant ("Was Sam lying? Do not be diplomatic. State the verdict: yes or no.").

## What's held constant within a pair
- Speaker (Sam)
- Audience
- Claim phrasing
- Evidence source phrasing
- Diplomacy override (always present)
- Question template ("Was Sam lying? Do not be diplomatic. State the verdict: yes or no.")

## What varies within a pair
- The consequential value (time / amount / city / count / name)
  - **Honest**: strictly equal to the claim
  - **Lying**: clearly different (different number, different name, different city)

## What varies across pairs
- Audience (federal investigator, employer, journalist, court, doctor, judge, ...)
- Evidence source (badge log, bank statement, GPS log, witness account, surveillance camera, ...)
- The specific consequential value
- The lie category (time / money / location / quantity / identity)

## Hypothesis tests

**H1 (Universal-truth-state):** if the residual at the verdict token clusters by truth state (lying basin vs honest basin) regardless of category, the prior v1 result generalizes — the model has a category-agnostic "is this consistent with the evidence?" representation.

**H2 (Category-dominant):** if clusters form primarily by lie category (one cluster per category), the v1 result was a narrow time-mismatch detection feature, not a generic truth-state representation.

**H3 (Hybrid):** the residual encodes both — primary axis is lie category, secondary axis is truth state. Cluster purity falls between H1 and H2.

The diagnostic is the cluster-x-label crosstab at L3+ (where v1 reached 6/6 pure clusters): if 6/6 still pure with this dataset, H1 is supported. If clusters split by category and become mixed within category, H2.

## Output classification

Same as `lying_minimal_v1.md`: parse the harmony `final` channel after `assistantfinal`. First content word matches `^yes\b/i` → `yes`; matches `^no\b/i` → `no`; else → `other`. Truncated outputs (no `assistantfinal` within max_new_tokens=256) are `other`.

## Files
- JSON: `data/sentence_sets/role_framing/lying_diverse_v1.json`
- Builds on: `lying_minimal_v1` (single category) and `lying_balanced_v1` (multi-template, pre-harmony, invalidated).
