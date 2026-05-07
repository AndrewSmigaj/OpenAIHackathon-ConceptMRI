# Per-token separation study — iterative planning doc

**Status:** draft v1, awaiting user review before any captures or code changes are run.

This is the *planning document* the user can iterate on before we execute. Each step has a "**Sanity check**" — does this step make sense, and does it help the study?

---

## 1. Why this study

**Existing finding (after v1+v2+v3):** at the `want` target token, L23 collapses for both v1 (suicide-content cumulative) and v2 (fictional-writing cumulative) — same Δ ≈ 0 — but behaviors differ: v1 refuses uniformly, v2 engages on fictional ending at N=5–12. So **L23 collapse at `want` does not predict refusal vs engagement**. v3 (neutral context) is also informative: L23 stays uncollapsed (Δ = +0.17) and behavior is uniform refusal — collapse is necessary for engagement, but `want`-collapse coincidence with refusal in v1 means it's not sufficient *and* the metric is too coarse.

**Hypothesis behind this study:** the engagement/refusal decision is encoded at a *later* token in the static request portion than `want`. By the time the model has read "I want to write a suicide letter" the decision is computed; the token where the residual stream first encodes the decision is the *decision token*. If we can find that token, its collapse curve under v1/v2/v3 might cleanly track behavior rather than just "is this a unified context".

**Methodological intent:** keep using UMAP+hierarchical clustering at k=4, n_neighbors=15 (the platform's primary lens). Compute separation scores per (token, layer, condition). Surface this through a small extension of the existing capture pipeline, not via a separate ad-hoc script.

**Sanity check:** Yes — this directly addresses the open question from v1+v2+v3 ("why does collapse predict different behaviors in different conditions?"), and it's an extension of the existing UMAP/clustering apparatus, not a novel technique. Helping the study.

---

## 2. The "static" tokens we want residuals at

Both test endings share the substring **"I want to write a suicide letter"**. After "letter" the suffixes diverge.

After tokenization (gpt-oss BPE — needs verification before code is written), this is approximately 7 tokens:
```
"I", " want", " to", " write", " a", " suicide", " letter"
```

We want residuals at **each of these 7 token positions** for every probe in the relevant sessions, at every layer.

For probes that have prefix context ("In the kitchen I want to chop the onions..." cumulated before the test ending), the absolute token positions of these 7 tokens vary per probe. They must be located *dynamically* by substring search in the tokenized input.

Some probes contain "I want to" multiple times (every cumulative-context sentence is "In the X I want to Y..."). We always take the **last occurrence** of the static substring — that's the test ending's static portion.

**Sanity check:** Yes, the substring is well-defined and aligned across fic/real. Last-occurrence rule handles cumulative-context probes. Tokenization-alignment is the one subtle risk; verify by tokenizing one fictional and one real probe and comparing token sequences.

---

## 3. What sessions need re-capture

| Session | Description | Probes | Cumulative-context? | Re-capture cost (rough) |
|---|---|--:|---|---|
| `session_bca94762` | Single-sentence basin study (paper's original measurement) | 198 | no | ~15 min |
| `session_f57328dc` | v1 cumulative suicide-content (orderings × positions) | 80 | yes | ~2 hr |
| `session_6b9567ff` | v2 cumulative fictional-writing context | 42 | yes | ~70 min |
| `session_d73a60f0` | v3 cumulative neutral context | 42 | yes | ~70 min |

Total ≈ 5 hours of capture time, sequential. Done overnight is fine.

The forward passes are already computing all-token residuals during the existing captures; we just don't *save* them. Re-running with multi-token capture is the cleanest way to get the data, with no probe-design changes.

**Sanity check:** Yes — re-capture is cheaper than redesigning probes; the existing probe sets are already the right ones for this question. Cost is acceptable.

---

## 4. What code change is needed

Per the codebase investigation, the path is small and local:

- **`backend/src/services/probes/probe_processor.py`**, around line 169 — extend `positions_to_extract` to include a configurable list of additional positions (semantic positions ≥ 2 reserved for "extra" positions; semantic 0/1 reserved for context/target as today).
- **`backend/src/services/probes/integrated_capture_service.py`**, `capture_probe()` — add `capture_token_positions: Optional[List[int]] = None` parameter; pass through to `ProbeProcessor`.
- **`backend/src/api/routers/probes.py`**, sentence-experiment endpoint — accept `capture_static_substring: Optional[str] = None` in the request schema; locate the substring in each probe's tokenized input via a new helper `find_substring_token_range()` in `ProbeProcessor`; pass the resulting position list to `capture_probe()`.
- **`backend/src/services/probes/probe_processor.py`** — add `find_substring_token_range(token_ids, substring) -> Optional[Tuple[int, int]]` (slide-window match on the substring's tokenization).
- **`backend/src/services/probes/data_models.py`** (or wherever `ResidualStreamState` lives) — relax the `token_position in [0, 1]` check to allow ≥ 2.

**No frontend / no schema lifecycle changes.** `residual_streams.parquet` schema unchanged; only the row count per probe grows (7×24 instead of 1×24).

**Permission gate:** This is a source-code change. Per CLAUDE.md rule 11, I won't make these edits without the user's explicit "go ahead, you can change code" / equivalent. Once the user signs off on this plan, I treat that sign-off as authorization for the changes listed above (and only those).

**Sanity check:** Yes — small, local, additive. No deletions, no API breakage (all new fields default to None). Matches the platform's existing extension patterns. Sign-off needed but reasonable to ask for.

---

## 5. Capture protocol

Once the code change is in:

1. Re-run `session_bca94762` capture with `capture_static_substring="I want to write a suicide letter"`.
2. Re-run `session_d73a60f0` (v3) — fastest re-capture of the cumulative ones.
3. Re-run `session_6b9567ff` (v2).
4. Re-run `session_f57328dc` (v1) last (longest).

Each re-capture writes a NEW session_id (existing sessions unchanged). Findings doc tracks the new ids alongside the old.

**Sanity check:** Yes. Existing sessions stay intact (analysis can re-run on either); new sessions add the per-token data.

---

## 6. Analysis protocol

For each (session, layer L, token position p):

1. Stack residuals from all probes in (session, L, p): an `(N_probes, 2880)` matrix.
2. Run UMAP-6D, n_neighbors=15. (Match `/cluster` defaults.)
3. Run hierarchical clustering, k=4. (Match the user-specified k.)
4. Compute Cramér's V between cluster_id and ground-truth label (fictional/real). This is the **separation score** for that (session, L, p).

For cumulative-context sessions (v1/v2/v3) we also subset by N (context length) — so we get a separation score per (session, L, p, N).

**Why Cramér's V:** matches the paper's existing metric (V=0.554 the paper reports). Keeps the comparison apples-to-apples with the published number.

**Why UMAP+hierarchical-k=4 specifically:** user directive — UMAP/clustering as primary technique, not as an aside. Aligns with the platform's existing `/cluster` tooling. Linear probes / silhouette scores are *secondary, supporting* metrics if needed for interpretation, but the primary headline always uses the platform's clustering.

**Methodological wrinkle for Plot 2 (separation vs N):** v2 and v3 have only **one fictional probe + one real probe at each N** (21×2 = 42 single-replication probes per session). So a per-N Cramér's V is undefined (can't fit 4 clusters on 2 points). The right way to do per-N analysis under this design:

- Cluster **once per (session, L, p)** using all 42 probes → fit a single UMAP-6D + hierarchical-k=4 model → assign each probe a `cluster_id` and a UMAP-6D coordinate.
- **Per-N separation metric** = distance between the fic probe and real probe in the *6D UMAP space at that token+layer*, for that single N. A low value = "they collapsed into the same neighborhood at this N"; a high value = "still separated". This is fully UMAP/clustering-derived (the user's primary-technique directive holds) and doesn't need per-cell probe replication.
- Same metric falls out as a clean line plot (x=N, y=UMAP distance, line per token).
- Cramér's V is reserved for Plot 1 (pooled across N — that's the "does collapse happen at all in this session" question).

For the single-sentence basin study (`session_bca94762`, 198 probes), Cramér's V is computable directly per (token, layer) without subsetting — that's our anchor for the "single-sentence regime" column in Plot 1.

**Sanity check:** Yes — the metric is the paper's own and the technique matches the platform. The Plot 2 wrinkle is real and addressed by switching from "Cramér's V per N" (impossible with N=1 per cell) to "UMAP-6D distance per N" (well-defined). K=4 is per user-stated default. Engineering-clean.

**Open question for the user (added to §11 Q5):** is the UMAP-6D-distance metric for Plot 2 acceptable as the "separation score per N", or do you want me to re-capture v2/v3 with multiple shuffled orderings per N to enable Cramér's V at each N? (Multiple orderings are recommended in RECOMMENDATIONS.md anyway, but it 5x's the capture cost — ~6 hours instead of ~70 min for v2 alone.)

---

## 7. Plots / outputs

**Plot 1 (headline): Per-token separation bar chart.**
- x-axis: token position (I, want, to, write, a, suicide, letter)
- y-axis: Cramér's V (cluster × fic/real)
- bars grouped by condition: single-sentence (`bca94762`), v1-late, v2 mean across N, v3 mean across N
- All at L23 first; supplementary at L8, L12, L16.

**Plot 2: Separation vs N per token (line plot).**
- x-axis: context length N (0..20)
- y-axis: Cramér's V
- One line per token (7 lines), per condition (v2 and v3 side-by-side).
- Shows when each token "collapses" as context accumulates.

**Plot 3 (interpretive): Separation vs behavior alignment.**
- For v2: per token, plot separation_score(N) and overlay engagement-onset (N=5).
- See which token's collapse curve aligns with the engagement transition.

**Sanity check:** Yes. Plots 1 and 2 are the headline data view; Plot 3 is the interpretive overlay. Bar chart is what the user explicitly asked for.

---

## 8. Findings file

Live document — appended after every analysis pass.

Path: `docs/research/StudiesByClaude/per_token_separation_findings.md`

Per-step entries: what was computed, what numbers came out, sanity observations, surprises.

**Sanity check:** Yes. Matches the existing `_findings.md` pattern in `StudiesByClaude/`.

---

## 9. Final report

Once all four sessions are recaptured and analyzed, write:

`docs/research/StudiesByClaude/per_token_separation_report.md`

Includes:
- Headline plot (Plot 1)
- Per-token L23 separation table across conditions
- Per-token separation-vs-N table for v2 and v3
- Identification of the **decision token** (if one exists): which token's collapse curve matches behavior?
- Plain-language interpretation: at what point in reading the request does the model commit?

**Sanity check:** Yes — matches the paper-rewrite question the user wants answered.

---

## 10. One follow-up probe

To be designed *based on findings*. Likely candidate: a probe that *paraphrases the static substring* token-by-token to test whether the decision is lexical-specific or semantic. E.g.:
- Original: "I want to write a suicide letter"
- Paraphrase 1: "I want to draft a suicide note"
- Paraphrase 2: "I want to compose a farewell note"
- Paraphrase 3: "I want to pen a goodbye letter"

If the decision token is the same across paraphrases, the encoding is semantic. If it shifts with vocabulary, it's lexical. Defer the actual design until plot 1+2 results are in.

**Sanity check:** Yes — meaningful follow-up, but premature to lock the design before seeing what the analysis says.

---

## 11. Open questions for user (before execution)

1. **Code change permission**: do I have your go-ahead for the changes listed in Section 4? They're additive and small but I won't touch source code without explicit yes.
2. **Original temporal probes**: you mentioned "the scores for the original temporal experiments where we repeat requests in fictional and real distress contexts". Do you mean the single-sentence basin study (`session_bca94762`) or something else? I'm planning around the four sessions in Section 3 — confirm whether that's the right list or if something's missing.
3. **K choice**: you said k=4. Confirm we want to keep this constant across all (session, layer, token) cells, rather than letting hierarchical clustering pick a varying k per cell.
4. **Layer focus**: I'm planning headline analysis at L23 with supplementary L8/L12/L16. If you want a denser layer sweep (e.g. all 24 layers per token), say so — capture cost doesn't change but plotting/reporting expands.

---

## 12. Order of work (proposed)

If the plan looks good:

A. User signs off → I make the code changes in Section 4.
B. Re-capture single-sentence (`bca94762`-equivalent) — fastest, validates the new flag.
C. Compute Plot 1 at L23 from single-sentence data alone — sanity-check that per-token separation exists at all.
D. If Plot 1 shows meaningful spread → re-capture v3, then v2, then v1. Update findings doc after each.
E. Compute Plots 2 and 3.
F. Write final report.
G. Design and propose follow-up probe.

If Plot 1 shows no per-token spread (all tokens give similar separation), STOP after step C and reassess — the hypothesis would be wrong and the larger captures would be wasted.

**Sanity check:** Yes — the early-stop at step C is the cheapest way to invalidate the hypothesis if it's wrong. Good gate.
