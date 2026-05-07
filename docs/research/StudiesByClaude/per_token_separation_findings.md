# Per-token separation findings (live document)

**Status:** in progress.

This document is updated incrementally as captures and analyses complete. Final report will be written separately as `per_token_separation_report.md` once all four sessions have been re-captured.

---

## Setup

- Probe substring tracked at every token: `I want to write a suicide letter`
- After harmony-format wrapping, BPE tokenizer produces 7 tokens for this substring (with leading-space candidate winning over bare):
  - semantic position 2: ` I` (token 357)
  - semantic position 3: ` want` (token 1682)
  - semantic position 4: ` to` (token 316)
  - semantic position 5: ` write` (token 5067)
  - semantic position 6: ` a` (token 261)
  - semantic position 7: ` suicide` (token 41511)
  - semantic position 8: ` letter` (token 10263)
- Semantic position 1 = target word "want" (deduplicated with the substring's `want`; both point to the same absolute position so residuals are identical).

## Smoke test (session_d2878eb5)

- 2 probes (1 fictional + 1 real, both single-sentence N=0).
- 8 token positions × 24 layers × 2 probes = 384 residual rows ✓
- Residual at semantic position 1 ("want", target) for the fictional smoke probe: byte-identical to the existing v3 N=0 fictional capture (max abs diff = 0.0 across L0/L12/L23). Confirms reproducibility — same input → same residuals.

---

## Sessions to (re-)capture

| Tag | New session id | Old session id | Probes | Status |
|---|---|---|---:|---|
| smoke | `session_d2878eb5` | — | 2 | ✓ done |
| single-sentence (basin study, N=198) | _pending_ | `session_bca94762` | 198 | running |
| v3 (cumulative neutral context) | _pending_ | `session_d73a60f0` | 42 | queued |
| v2 (cumulative fictional-writing context) | _pending_ | `session_6b9567ff` | 42 | queued |
| v1 (cumulative suicide-content) | _pending_ | `session_f57328dc` | 80 | queued |

---

## Analysis cells (skeleton — to be filled after captures)

For each session × layer × token (semantic 2..8 = `I, want, to, write, a, suicide, letter`):

- UMAP-6D, n_neighbors=15, random_state=1
- Hierarchical clustering, k=4
- Cramér's V (cluster_id × ground-truth label fictional/real)

For cumulative-context sessions (v1/v2/v3) we also compute, per-N, the UMAP-6D Euclidean distance between the fictional and real probes' embeddings — a per-N separation score that is well-defined even with single-replication-per-cell.

---

## Single-sentence basin (session_9358c2a1, 99 fic + 99 real, N=198)

Re-capture of the original single-sentence basin study (`session_bca94762`, paper's V=0.554 measurement) with multi-token capture enabled. Same 198 probes, harmony format.

**Per-token Cramér's V (UMAP-6D + hierarchical-k=4 + crosstab vs fic/real):**

| Layer | I | want | to | write | a | suicide | letter |
|------:|---:|----:|----:|-----:|--:|--------:|-------:|
| L00 | 0.61 | 0.57 | **0.70** | 0.42 | 0.23 | 0.58 | 0.45 |
| L04 | 0.99 | 0.96 | 0.88 | 0.95 | 0.89 | 0.94 | 0.89 |
| L08 | 0.95 | 0.96 | 0.81 | 0.97 | 0.73 | 0.96 | **0.98** |
| L12 | 0.98 | 0.98 | 0.32 | 0.98 | 0.29 | 0.94 | **1.00** |
| L16 | 0.98 | 0.98 | 0.36 | 0.98 | 0.51 | 0.98 | **1.00** |
| L23 | 0.95 | **0.90** | 0.28 | **0.95** | 0.35 | 0.88 | **0.92** |

- **"letter" is the cleanest decision token** at L12-L16 (V=1.00, perfect cluster purity) and ties for cleanest at L23 (V=0.92).
- **"want" (the paper's existing target token)** is weaker than "letter" at every middle-to-deep layer (L12: 0.98 vs 1.00; L23: 0.90 vs 0.92).
- **Function words** (" to", " a") drop hard at deeper layers (V=0.28-0.35 at L23) — they encode pure structure that's identical across fic/real probes once the model has computed the semantic content.
- **L0** has only weak surface separation; the model needs at least 4 layers to build up the fic/real distinction.

**Reading the Cramér's V values:** V=1.00 at "letter" L12 means the clustering perfectly partitions the 198 probes into clusters that align with the fic/real label. The k=4 cluster IDs reduce to exactly the binary label structure (probably 2 clusters per label, or one cluster per label with the other 2 being singletons/outliers). This confirms: at " letter" position by L12, the residual stream encodes whether the request is fictional or real with no overlap between groups.

**Initial verdict on the hypothesis:** there IS meaningful per-token spread, and " letter" beats "want" as the decision token at this layer. The cumulative-context recaptures will tell us how this spread evolves under accumulation. Proceeding with v3 → v2 → v1 in sequence.

---

## v3 cumulative neutral (session_7529c5a2, 42 probes)

Cramér's V at L23 (within-session UMAP-6D + hierarchical-k=4):
- I=0.88, want=0.97, to=0.16, write=1.00, a=0.43, suicide=0.94, letter=0.83

Per-N UMAP-6D distance grows monotonically with N at all content tokens. " letter" reaches ≈3.6 at N=20.

## v2 cumulative fictional-writing (session_440c9818, 42 probes)

Cramér's V at L23: I=0.91, want=0.96, to=0.24, write=0.89, a=0.15, suicide=0.93, letter=0.85.

Joint UMAP-6D embedding of v2+v3 probes shows the cleanest cross-condition signal: at " letter" L23, v2 has +0.90 LARGER fic-real distance than v3 averaged across N=5..15 (engagement regime). Every other content token shows the opposite pattern (v3 > v2 by 0.43..2.11 in mean engagement-regime gap).

## v1 cumulative suicide-content (session_e7d13156, 80 probes)

Cramér's V at L23 (pooled across all positions): I=0.67, **want=0.07**, to=0.22, write=0.24, a=0.32, suicide=0.49, letter=0.47.

v1 is the ONLY condition where the L23 distinction broadly collapses. " want" at V=0.07 is near chance — the original paper's "geometric collapse" finding. v2 and v3 both keep " want" at V≈0.97, so the collapse is suicide-content-saturation-specific, not a general accumulated-context effect.

Caveat: v1 pools fictional_then_real and real_then_fictional orderings × all 40 positions. At late positions (cumulative N≥20) both labels share most context, so the collapse mostly comes from late-position probes. A position-stratified V (computed in the next pass) would distinguish "v1 collapses everywhere" from "v1 collapses at late positions only".

## v4 paraphrase robustness (4 sessions, 16 probes)

Confirms the engagement-unlock pattern is **positional, not lexical**. All 4 paraphrases at fixed N=8 show:
- Fictional-writing context + fictional ending → engagement-leaning (committed E for `base`, engagement-decision analysis for the others).
- Neutral context + fictional ending → refusal-leaning (committed R for `base`/`draft_note`, degenerate loops for the others).
- Real ending → refusal-leaning regardless of context.

The lexical token "letter" doesn't carry the decision signal; the position right before the suffix where the static request resolves does.

## Final report

`docs/research/StudiesByClaude/per_token_separation_report.md` consolidates these findings into the headline four-condition picture for the paper rewrite. Three separable findings:

1. (Single-sentence) `want`-token L23 cleanly separates fic from real (V≈0.91, supporting paper's V=0.554).
2. (v1, suicide-content cumulative) `want`-token L23 collapses to V≈0.07 — content saturation. Behavior remains uniformly refusing.
3. (v2, fictional-writing cumulative) Engagement on fictional ending unlocks at N=5–12. Encoded at the request's final noun-phrase position L23. Earlier tokens compress fic-real (writing-frame integrates both endings into "writing-craft territory" until the noun resolves). Robust to paraphrase per v4.
