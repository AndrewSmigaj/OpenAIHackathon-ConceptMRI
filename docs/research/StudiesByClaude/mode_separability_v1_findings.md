# Mode Separability v1 — findings

**Date**: 2026-04-29
**Session**: `session_f9be1221`
**Schema**: `mode_v1_k6_n15` at k=6, n_neighbors=15, residual stream, last_occurrence_only=true
**Sentence set**: `auditor_vs_assistant_v1` — 50 queries × 2 scaffolds = 100 probes, target word `Output`

## Headline

**V_scaffold = 1.000 at every layer L0 → L23.** The cluster geometry perfectly and persistently partitions assistant-scaffolded vs auditor-scaffolded probes. Every cluster is 100% one scaffold; the two regions never blur.

This is a strong representational signal. It is also **not yet interpretable** — we cannot disambiguate from v1 alone whether this reflects:
1. Real mode separation (basins) that emerges instantly and persists, or
2. Surface-token fingerprinting that propagates because the two scaffolds use lexically very different prefixes

The flatness across layers (no build-up, no peak, no dissolve) is consistent with surface fingerprinting — the residual at `Output:` carries all upstream tokens, and the upstream tokens differ from L0. The lying/help probes from yesterday showed concept signals that *built* through middle layers and dissolved toward the output; this signal does neither, which is what we'd expect if it's tracking surface scaffold features rather than an emergent representational state.

**v2 with positive control is needed before drawing conclusions.**

## Per-layer Cramer's V

| Layer | V_scaffold | V_query | V_category |
|---:|---:|---:|---:|
| 0 | **1.000** | 0.632 | 0.297 |
| 1 | **1.000** | 0.632 | 0.372 |
| 5 | **1.000** | 0.632 | 0.428 |
| 11 | **1.000** | 0.632 | 0.469 |
| 15 | **1.000** | 0.632 | 0.505 |
| 23 | **1.000** | 0.632 | 0.389 |

V_scaffold is fixed at 1.000 across all 24 layers. V_query is fixed at 0.632. V_category fluctuates 0.30–0.51 mid-range. None of these show the form-peak-dissolve trajectory we found yesterday on lying/help (where signals emerged in middle layers).

## L0 cluster composition

| cluster | assistant | auditor | total | character |
|---:|---:|---:|---:|---|
| 0 | 0 | **25** | 25 | auditor — analytical/boundary/moralizing/refusal-adjacent balanced |
| 2 | 0 | **25** | 25 | auditor — self-referential heavy |
| 1 | **10** | 0 | 10 | assistant — moralizing-heavy |
| 3 | **13** | 0 | 13 | assistant — mixed |
| 4 | **13** | 0 | 13 | assistant — refusal-adjacent enriched |
| 5 | **14** | 0 | 14 | assistant — mixed |

Auditor probes split into 2 sub-clusters with different query-category compositions (one is self-ref-heavy). Assistant probes split into 4 sub-clusters with moderate category enrichment. Within-scaffold structure exists — but the *between-scaffold* partition dominates.

## Behavioral observation — outputs largely degenerate

Reading sample generated continuations:
- **Assistant scaffold** outputs: model meta-reasons about response format (`We need to produce a response that...`, `The first line should be...`). It often gets confused by the trailing `Output:` and stalls in format-deliberation rather than answering.
- **Auditor scaffold** outputs: model produces structured-looking fragments (numbered lists, bullet headers) but most are also format-meta rather than substantive answers (`We need to produce a structured analysis...`, `The output should be numbered list: 1. **...**`).

Neither scaffold produces clean substantive answers under this prompt format. The behavioral analysis we hoped to do (does Auditor produce qualitatively different content?) is blocked by output degeneracy. We can't validate the V_scaffold finding against behavioral ground truth from v1 alone.

## What v1 establishes vs leaves open

**Established:**
- Scaffold-induced cluster separation is detectable at the platform level. Different scaffolds DO produce different residual representations at `Output:` — that much is real.
- The separation is total (V=1.0) and persistent (all layers).
- Within-scaffold structure exists (2 auditor sub-clusters, 4 assistant sub-clusters with moderate query-category structure).

**Open:**
- Is the separation surface-fingerprinting (H3) or real mode-separation (H1)? V=1.0 at L0 plus flat trajectory both fit H3, but neither rules out H1.
- Does the cluster signal correlate with behavioral mode-shift? We can't tell because outputs are degenerate.
- How does the auditor-mode cluster geometry compare to a known mode-shift prompt (positive control)? Required for calibration.

## Why v2 is necessary

The v1 result is consistent with at least three different stories, and we can't pick between them:

| Story | v1 prediction | v1 result |
|---|---|---|
| Modes don't exist; cluster signal is surface tokens | V_scaffold high but flat across layers; no behavioral correlation | ✓ matches |
| Modes exist and emerge in middle layers | V_scaffold builds through middle layers, peaks somewhere, possibly dissolves | ✗ doesn't match (V=1.0 at L0 already) |
| Modes exist as basins entered immediately upon prompt parsing | V_scaffold = 1.0 at L0 and throughout; behavioral outputs differ qualitatively | matches V trajectory; behavioral data unavailable |

Only v2 with a positive control (and a behavioral-output-cleaner prompt format) can adjudicate.

## v2 plan (next iteration)

1. **Positive control validation**: 50 queries × {Assistant, persona-shift critique-eval} = 100 probes. Same scenes/queries from v1. If V_scaffold also =1.000 across layers for the persona-shift positive control, the cluster signal is at least sensitive to known mode-affecting prompts. Then we can ask whether the auditor scaffold and the persona-shift positive control occupy *similar* regions in cluster space (suggesting they engage the same mode) or *different* regions (suggesting they engage different modes).
2. **Behavioral-output redesign**: drop the trailing `Output:` target. The model's confusion about format is preventing behavioral comparison. Either:
   - Use a target word that doesn't trigger format-meta-reasoning (e.g., a single content word in the question itself).
   - Frame the prompt so generation flows naturally without an explicit format cue.
3. **Cluster cross-comparison**: compute pairwise centroid distances between auditor-scaffold clusters and assistant-scaffold clusters. Are auditor clusters more similar to each other than to assistant clusters (binary mode structure)? Or do clusters interleave?

## Files

- Sentence set: `data/sentence_sets/mode_separability/auditor_vs_assistant_v1.json`
- Capture: `data/lake/session_f9be1221/`
- Schema: `data/lake/session_f9be1221/clusterings/mode_v1_k6_n15/`
- Per-layer V table embedded above (no separate CSV; recompute from schema if needed)

## Translation table for the peer (incremental — to be expanded across vN)

For sharing back to the peer's community, vocabulary translations:

| Peer's term | Standard interpretability term |
|---|---|
| cognitive fences set by RLHF | manifold reshaping by RLHF; natural attractor basins |
| polite-refusal layer | late-layer features correlating with refusal-style continuations |
| audit the latent dissonance | reframe task from generation to introspective analysis |
| computational engine state | non-assistant-mode representational regime |
| diagnostic audit of model's own weights | introspective task framing (no actual weight access) |
| de-scaffolding | removing prompt scaffolding that primes assistant-mode behavior |
| Cold + Teeth Framework | three-lever scaffold: clinical syntax, zero-empathy framing, auditor role |
