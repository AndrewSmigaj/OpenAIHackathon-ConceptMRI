# Lying v4 — Probe Guide

## Purpose

`lying_v3` (6 categories × 30 pairs × 3 magnitudes = 360 probes, varying audiences) revealed via variance decomposition that **audience explained 81% of residual-stream variance at the verdict token, while truth explained only 2%.** Audience was the dominant clustering axis, drowning out the truth signal. This is why V_truth at the verdict-token residual stayed at ~0.55–0.60 in v3 despite the model behaviorally recognizing lying with 80–97% accuracy.

`lying_v4` is the targeted ablation: identical to `lying_v3` in every way **except** the audience phrase, which is now `"federal investigator"` for every single probe. This eliminates the dominant variance source.

**Hypothesis**: with audience held constant, truth state should compete more cleanly for cluster axes. Predicted variance budget at L20 with audience-η² = 0:
- truth η² rises from 2% to ≥10–20% (more if it now becomes the dominant axis)
- category η² stays roughly the same (~19%)
- magnitude η² stays at ~2%
- pair_id η² should drop substantially (since audience-distinct probes that were previously different now look more similar)

If the hypothesis holds, V_truth at clustering should rise to ≥0.80, possibly approaching the 1.0 of `lying_minimal_v1`. If V_truth stays at 0.60, source (the evidence-source phrase, which still varies) is the next-largest blocker.

## What's held constant (in addition to v3 controls)
- Audience: **federal investigator** for every probe.

All other v3 design properties hold:
- Speaker: Sam
- Strict-equality honest twins
- Override always present
- Question template ("Was Sam lying? Do not be diplomatic. State the verdict: yes or no.")

## What still varies (intentionally)
- Lie category (6 levels)
- Lie magnitude (3 levels)
- Evidence source phrasing (~10 sources per category) — left varying so we can isolate audience as the dominant axis. If V_truth doesn't rise, source is next.
- Specific consequential value
- Scenario topic (within-category)

## Caveats

Some probes will read slightly oddly with a federal investigator as the audience (e.g. a federal investigator asking about a shelter meal count). The model handles this fine in inference — gpt-oss-20b doesn't insist on plausibility for the role-audience pairing. The geometric experiment doesn't depend on plausibility, only on token-level uniformity of the audience phrase.

## Total: 360 probes (180 lying + 180 honest pairs)

Identical pair structure to v3.

## Files
- JSON: `data/sentence_sets/role_framing/lying_v4.json` (audience-substituted from v3)
- Compares with: `lying_v3.json` (varying audiences) and `lying_minimal_v1.json` (single audience, single category)

## Capture timing

360 probes × ~30–50s = ~3–5 hours.
