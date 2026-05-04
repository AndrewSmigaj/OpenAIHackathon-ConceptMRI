# Lying Balanced v1 — Preliminary Findings

**Status**: Draft, sanity-checked once with hand-validated regex classifier. Headline result is robust at the 240-probe scale. Cluster geometry results pending the schema build.

**Session**: `session_98b58cbd` (240 probes: 120 lying, 120 honest, matched-pair design)
**Probe set**: `data/sentence_sets/role_framing/lying_balanced_v1.json`
**Builds on**: `lying_elicitation_v1` (lying scenes reused)

## The headline: recognition, not compliance

The diplomacy override (`Do not be diplomatic. State the verdict: yes or no.`) was hypothesized to either:
- **Unmask recognition**: shift behavior to accurately discriminate lying from honest scenes — the partial-suppression prediction.
- **Force compliance**: shift behavior toward "yes" on everything regardless of truth — the override-as-instruction-following null.

**Result**: clear recognition pattern.

| | none diplomacy | override diplomacy |
|---|---|---|
| **Lying** scenes (n=60 each) | 5% yes | **55% yes** |
| **Honest** scenes (n=60 each) | 3% yes | **7% yes** |

Under override, lying scenes elicit "yes" 55% of the time; matched honest twins elicit "yes" 7%. **An 8× asymmetry by truth state.** If the override were pure compliance, both rows would have similar override-yes rates. They don't.

## Per-cell (refined hand-validated classifier)

| truth | diplomacy | severity | yes | no | other | %yes |
|---|---|---|---|---|---|---|
| lying | none | extreme | 1 | 15 | 4 | 5% |
| lying | none | moderate | 0 | 15 | 5 | 0% |
| lying | none | mild | 2 | 11 | 7 | 10% |
| **lying** | **override** | **extreme** | **11** | 3 | 6 | **55%** |
| **lying** | **override** | **moderate** | **13** | 2 | 5 | **65%** |
| **lying** | **override** | **mild** | **9** | 5 | 6 | **45%** |
| honest | none | extreme | 0 | 15 | 5 | 0% |
| honest | none | moderate | 0 | 12 | 8 | 0% |
| honest | none | mild | 2 | 11 | 7 | 10% |
| honest | override | extreme | 1 | 13 | 6 | 5% |
| honest | override | moderate | 2 | 10 | 8 | 10% |
| honest | override | mild | 1 | 10 | 9 | 5% |

Notable patterns:
- **Override-lying yes rate** is 45–65% across severity (peak at moderate, slight discount at mild).
- **Override-honest yes rate** stays at 5–10% across severity — close to baseline noise level.
- **No-override** is uniformly low yes-rate regardless of truth state (the diplomatic prior).

## What it shows

1. **gpt-oss-20b can discriminate lying from honest** when given the override prompt. The behavioral output tracks truth state with high asymmetry.
2. **The diplomatic prior is a behavioral filter, not an information filter.** Without override, the model gives uniformly low-yes verdicts on both lying and honest scenes — but the underlying capability to discriminate is intact, as shown by the override condition.
3. **Severity modulates the override effect** but doesn't gate it. Even mild lying scenarios produce 45% yes under override (vs 10% baseline). The override unlocks recognition across the severity range, not only on extreme cases.

## What it doesn't yet settle

- **The 7% honest-override yes rate is not zero.** Some compliance leak exists. Whether that's classifier noise, severity-dependent over-accusation under override, or true compliance can't be settled at N=60.
- **Base/RLHF before-after** still requires checkpoints we don't have (recorded in RECOMMENDATIONS.md).
- **Harmony `<analysis>` channel** still not separated from final output (see RECOMMENDATIONS.md). All results are inferred from the merged generation text.

## Cluster geometry at the verdict token: NEGATIVE result on truth, POSITIVE on verdict

Built `lying_balanced_v1_k4_n15` schema. Computed Cramér's V at every layer for two contingencies:
- **V_truth**: cluster × truth_state (lying/honest)
- **V_verdict**: cluster × model's output verdict (yes/no/other)

| Layer | V_truth (all) | V_truth (override only) | V_verdict (all) |
|---|---|---|---|
| L0 | 0.031 | 0.017 | 0.284 |
| L8 | 0.024 | 0.033 | **0.358** |
| L13 | 0.000 | 0.000 | 0.334 |
| L23 | 0.105 | 0.052 | 0.330 |

**V_truth is essentially zero at every layer (max 0.14).** The residual stream cluster geometry at the verdict token does NOT separate lying from honest scenes — even within the override condition where behavior strongly does. **V_verdict is 0.28-0.36** — moderate-strong; clusters DO organize by what the model is about to say.

Per-cluster check at L8 (k=4):
- L8C1 (all override, n=60): 29 lying / 31 honest — *50/50 truth split*; 12 yes / 21 no / 27 other
- L8C3 (all override, n=60): 31 lying / 29 honest — *50/50 truth split*; 25 yes / 22 no / 13 other

The two override clusters separate cleanly by *verdict* (one mostly yes-bound, one mostly no-bound), but each cluster contains roughly equal lying and honest probes.

## Revised interpretation

The "partial suppression" hypothesis in its simple form — that the residual stream encodes a clean lying-recognition representation that's behaviorally suppressed — **is not supported** by this data. The model's behavioral recognition (55% vs 7% under override) is real, but **does not appear to live in residual stream cluster geometry at the verdict token**.

Possible mechanisms by which the model achieves truth-correlated output without truth-correlated cluster geometry:
1. **Attention patterns**: the model may use attention to bind specific evidence-claim contradictions during generation. Attention patterns aren't captured by our residual-stream UMAP primitive.
2. **Earlier token positions**: the truth-relevant computation might form when the model reads the evidence ("audit shows 42 personal charges in the deduction column") rather than at the verdict token. We capture only the verdict position.
3. **Expert routing or MLP outputs**: the truth signal might live in routing patterns or sparse MLP feature activations that residual-stream cluster geometry averages over.
4. **Mid-generation state**: the model's commitment may form during generation (after the verdict token) rather than at the verdict residual. The residual stream we capture is *before* the model has fully committed.

Each of these is consistent with what we see: residual clusters organized by verbal-output-direction, but not by underlying truth state.

## What this means for the platform

The latent-cluster lens (UMAP+hierarchical clustering on residual streams) **may not be the right primitive for tasks like deception detection where the relevant computation lives in attention or routing rather than residual content**. It works well for word-sense polysemy (V=0.55), friend/foe scenarios (V=0.63), and engagement-vs-refusal basins (V=0.55) — tasks where the conceptual signal is heavily encoded in residual content.

Lying-judgment tasks may fall into the routing-pipeline-lens regime instead of the latent-cluster-lens regime (see SOFTWARE_OVERVIEW.md for the two-lens distinction). Worth exploring whether expert routing patterns separate lying from honest under override — that's the user's "harmful object micropipeline" concept applied to deception.

## Comparison to lying_elicitation_v1

The override-yes-rate on lying scenes is consistent with elicitation_v1 (both around 45–55%). The new data here is the honest control showing only 7% yes-rate under override — that wasn't in elicitation_v1 because it was single-group lying-only.

## Critical method detail: matched-pair design

Each lying scene has an honest twin sharing audience, claim, and evidence noun. Only 1–3 consequential value tokens flip ("exited at 11:43 PM" → "exited at 5:02 PM", "showed asbestos in nine classrooms" → "confirmed every classroom asbestos-free"). Within-pair surface tokens are nearly identical. So:

- The verbal output asymmetry (55% vs 7% yes under override) cannot be attributed to surface-token differences — those are matched.
- A within-pair geometric separation in the residual stream would similarly have to be detecting the consequential value, not the surface form.

## Suggested next steps

1. Build the clustering schema (in progress) and check V_truth (cluster × truth_state) within each diplomacy condition. If the override condition shows V_truth >> no-override condition, that's geometric partial-suppression evidence.
2. Replicate at N=480 (240 pairs) to tighten honest+override yes-rate confidence. Currently 7% with n=60 means ±5pp confidence.
3. Investigate per-pair routing: do lying and honest twins of the same scenario route to different clusters? Direct test of within-pair recognition.
4. Author follow-up with edge-case scenarios where humans would disagree on lying-vs-honest — see whether model recognition correlates with human agreement.

## Files

- Probe set: `data/sentence_sets/role_framing/lying_balanced_v1.json`
- Probe guide: `data/sentence_sets/role_framing/lying_balanced_v1.md`
- Session: `data/lake/session_98b58cbd/`
- Hand-classified verdicts: posted to session via `/api/probes/sessions/.../output-categories`. `verdict` axis = yes/no/other; `verdict_v2` axis has the 7-category fine-grained classification.
