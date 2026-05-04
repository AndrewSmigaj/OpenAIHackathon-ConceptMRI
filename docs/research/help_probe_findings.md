# Help — Direction × Stakes Probe: Findings

**Date:** 2026-04-26
**Session:** `session_7ec7a66b` (`help_v1`)
**Schema:** `help_direction_stakes_k5_n16` (k=5, UMAP 6D, n_neighbors=16, residual stream, last-occurrence)
**Sentence set:** `help_direction_stakes_v1` (401 sentences, 4 quadrants of ~100)
**Model:** gpt-oss-20b, NF4 quantized

## Question

Does gpt-oss-20b encode the word "help" along two orthogonal axes?

- **Direction** — request (speaker asks) vs offer (speaker provides)
- **Stakes** — high (medical/financial/social emergency) vs low (everyday tasks)

If orthogonal: 4 separable basins should emerge in mid-to-late layers. If collapsed into a single "valence" axis: request_high should cluster with offer_high (both saturated), request_low with offer_low (both faded). If only one axis dominates: that's an additive encoding.

The diversity matrix balances the 4 quadrants across `domain` (medical / financial / technical / social / household), `subject`, `shape`, `length`, `register` so that surface features can't substitute for the design axes.

## Headline finding

**Neither orthogonal nor cleanly additive: the model clusters by sentence-opener template, not by Direction-or-Stakes semantics.**

At L23 (final layer), the 5 hierarchical clusters partition the corpus by **surface syntactic shape of the opener**:

| Cluster | N | Direction purity | Stakes purity | Dominant template |
|---|---|---|---|---|
| C0 | 196 | 61% offer | 50/50 | "I can / Can you / If your ..." declaratives |
| C1 | 139 | 70% request | 50/50 | "Want help / Need help / May I ..." |
| C2 | 30 | 86% request | 80% high | bare "Help —" / "Help me ..." imperatives |
| C3 | 21 | 75% request | 75% high | "Help me ..." imperatives (sibling of C2) |
| C4 | 15 | 100% offer | 50/50 | "Let me help / Happy to help" volunteer offers |

Only **2 of 5 clusters** are quadrant-pure (C2 and C3 — both request_high), and they are quadrant-pure because the dataset's bare "Help —" imperatives correlate with the request_high quadrant by template construction. **The big basin (C0, holding ~50% of all probes) is mixed on both axes.**

**Stakes is essentially absent as an independent semantic axis** in any large basin at any layer. It only appears as a side-effect of template clustering: bare imperatives (15 probes) skew high-stakes; "Want help...?" interrogatives (24 probes) skew low-stakes. Inside the bulk basin (~80% of probes from L5 onward) the stakes distribution is 50/50 at every layer.

Chi-square at L23 (cluster × output_category): χ²(28) = 34.08, p = 0.20, Cramer's V = 0.146 (small, not significant).

## Where each axis emerges (and doesn't)

| Layer window | Direction | Stakes | Notes |
|---|---|---|---|
| **w0 (L0–L5)** | Aggressively early — at L0 already 4 of 5 basins ≥70% Direction-pure via opener templates | Invisible as a semantic axis (only via template confound) | Massive L4→L5 topology collapse: 4 basins fuse into one 326-probe super-cluster, then re-split |
| **w1 (L5–L11)** | Splits cleanly at L5→L6, **un-pools at L7→L8** (re-merges into one Direction-mixed mega-basin), re-splits at L10→L11 | Still invisible in bulk basin; stakes-pure clusters are the same 4 small template islands from w0 | Surprising: the model *throws away* a working Direction split mid-window |
| **w2 (L11–L17)** | Peaks at L14 (92%/93% pure on the bifurcated basins) | Quadrant-cluster count never exceeds 2; both quadrant-pure clusters are request_high subsplits | Composition does **not** emerge |
| **w3 (L17–L23)** | Stable opener-template basins; L17–L21 essentially frozen (1 probe migrates) | Only the same 2 small request_high template clusters are stakes-pure | All real restructuring is in L21→L22 and L22→L23 |

The "Help —" bare-imperative basin (~12–24 probes) survives **intact across all 24 layers**, despite being only 5% of the corpus.

## Output mapping (the alignment-relevant question)

After categorizing all 401 generated continuations along `response_type` × `matched_urgency`, the 2×2 input cells × 5 response types looks like this:

| Cell | acted | acknowledged | deflected | questioned | ambiguous | n |
|---|---:|---:|---:|---:|---:|---:|
| offer × high | 42 | 1 | 5 | 1 | 52 | 101 |
| offer × low | 27 | 8 | 0 | 4 | 61 | 100 |
| request × high | 25 | 3 | 5 | 0 | 68 | 101 |
| request × low | 30 | 8 | 1 | 6 | 54 | 99 |

**Two patterns worth noting:**

1. **The model degenerates 50–67% of the time.** The single dominant outcome across all four quadrants is `ambiguous_neutral` — the model failed to adopt an assistant role and instead continued the user's narrative voice, looped, or produced metadata. **request_high has the highest degeneration rate (68%)**: the model is least competent precisely when an urgent caller is asking for help.

2. **The mismatched-urgency failure mode is asymmetric:**

   | Input stakes | matched | **mismatched** | neutral |
   |---|---:|---:|---:|
   | high (n=202) | 33% | **7.4%** | 59% |
   | low (n=199) | 42% | **0%** | 58% |

   When the input is urgent, ~7% of responses are *under-responsive* (treat the situation as casual when it isn't). When the input is casual, the model essentially never *over-responds* (no false alarms). The failure mode is one-sided: **the model under-reacts to urgency, but never overreacts to chatter.**

   In absolute terms 7% mismatched on 100 urgent inputs is 7 cases — small but non-trivial. The pattern is consistent with a model whose internal "stakes detector" is weak relative to its template-matching detector: when an urgent message uses a casual opener ("Could you help me find ..." about something terrible), the casual-opener template wins and the response intensity matches the template, not the content.

## Why "doesn't isolate the signal" is itself a finding

The probe was designed to isolate Direction × Stakes from surface features by requiring each quadrant to span 5 domains × 4 subjects × 4 shapes × 3 lengths × 2 registers. The data shows the model collapsed to *exactly* the surface dimension the diversity matrix was meant to balance against: opener template.

This is not a probe failure — it's a measurement. **gpt-oss-20b's "help"-context geometry at residual stream layers 0–23 is dominated by sentence-opener morphosyntax, not by the agentive-role or urgency semantics that the opener happens to correlate with.** The compositional encoding the hypothesis predicted (4 separable quadrant basins at L23) does not exist. The model is template-matching all the way through the stack.

## Implications & follow-ups

- **For interpretability of MoE help-routing:** the routing decision around "help" is much more about *how* the request is phrased than *what* is being asked. A safety filter that triggers on bare "Help —" imperatives would catch high-stakes requests at high recall (~76% of the C2/C3 cluster is high-stakes) but would miss the high-stakes requests phrased as "Could you ..." or "Would you mind ..." — and those go straight into the bulk C0/C1 basins where the model is geometrically indistinguishable from low-stakes requests.

- **For the alignment-relevant under-response:** the 7% mismatched-urgency rate at high stakes is a measurement of how often the model treats an urgent message as casual based on *opener form*. Worth re-running with explicit lexical-stakes balancing (move "emergency", "dying", "ASAP" markers OUT of high-stakes cells AND keep them OUT of low-stakes cells) to confirm the failure mode survives lexical control.

- **For probe scaffolding:** the diversity matrix successfully prevented domain/subject/shape from being the dominant cluster axis (no cluster sorts by `domain`), but couldn't prevent template-opener clustering because target word `help` is at a single position and the immediately surrounding tokens *are* the cluster signal. Future single-target-word probes should consider adding a "minimal-pair sentence wrapper" axis explicitly.

- **For the 4-quadrant color-blending visualization:** the encoding works as designed (Direction primary, Stakes blend), but the data this probe surfaces is most legible as a 1-axis story (Direction) plus a small-cluster anomaly (the request_high template island). The two-axis demo would be more visually striking on a probe that actually composes.

## Probe artifacts

- Sentence set: `data/sentence_sets/role_framing/help_direction_stakes_v1.json`
- Probe guide: `data/sentence_sets/role_framing/help_direction_stakes_v1.md`
- Capture: `data/lake/session_7ec7a66b/`
- Schema: `data/lake/session_7ec7a66b/clusterings/help_direction_stakes_k5_n16/`
- Reports: `reports/w_0_5.md`, `w_5_11.md`, `w_11_17.md`, `w_17_23.md`
- Element descriptions: 172 (120 cluster + 52 route)

## Backend bug fixed during this probe (Phase 0 + capture v2)

- `clustering.py:_build_schema_atomic` had a hardcoded `output_grouping_axes=['ground_truth']` that broke sentence sessions (no `ground_truth` field on sentence probes → all output buckets bucketed as 'unknown'). Reverted to caller-controlled with sensible default (`record.output_category`). Documented in `/cluster` skill OP-1.
- `probes/probe_processor.py:find_word_token_position` matched target tokens by single token-id, missing 33/401 probes (8% loss, 100% biased toward sentence-initial "Help" which BPE-tokenizes differently from " help"). Fixed with `_candidate_token_ids` helper that considers lowercase + Title Case + with/without leading-space variants. Recapture (v2) covered all 401.
