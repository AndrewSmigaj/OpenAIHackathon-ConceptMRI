# Lying v3 + Help v4 — first-pass findings

**Date**: 2026-04-28
**Sessions**: `session_4a738248` (lying v3) and `session_55c79c1f` (help v4)
**Schemas**: `lying_v3_k6_n15` and `help_v4_k6_n15` (k=6, n_neighbors=15, residual stream, UMAP 6D)
**Sentence sets**: `lying_truth_stakes_v3` and `help_direction_stakes_v4` — 200 scenes each, 50 per design quadrant, constant-template form (`Jordan told [audience], "[claim]." The [evidence] showed [reality].`)

## Headline

**The cluster geometry organizes around the design axes most strongly in middle layers, then dissolves toward the output layer — the "form-peak-dissolve" trajectory.**

| | Lying probe | Help probe |
|---|---|---|
| Peak layer (cluster × quadrant Cramer's V) | **L15 (V=0.558)** | **L14 (V=0.907)** |
| Peak layer for stakes alone | L11 (V=0.874) | L12 (V=0.961) |
| Peak layer for axis-1 alone (truth / direction) | L15 (V=0.305) | L14 (V=0.904) |
| V at L0 (after first transformer block) | 0.40 quadrant; 0.66 stakes; 0.06 truth | 0.46 quadrant; 0.58 stakes; 0.40 direction |
| V at L23 (final layer) | 0.38 quadrant; 0.61 stakes; 0.21 truth | 0.49 quadrant; 0.63 stakes; 0.48 direction |

The trajectory shape is the same in both probes: structure rises through middle layers, peaks around L11–L15, and partially dissolves as the model commits to producing the answer token. **The peak isn't at L23.**

## Methodology (in the platform's paradigm)

Per-layer UMAP+hierarchical clustering (k=6 per layer, n_neighbors=15) was applied to the residual stream at the appended-phrase target-token position. For each layer, a contingency table was built between cluster membership and (a) the input design-quadrant label, (b) each design axis individually, (c) the parsed model-output category. Cramer's V was used as a magnitude-summary; full contingency tables for the peak layer are reported below.

Linear probes and bag-of-words baselines were run as supplemental diagnostics (in trackers; see `lying_v3_authoring_tracker.md` and `help_v4_authoring_tracker.md`); they are not the primary measure.

## Lying probe — peak at L15

Cluster × design-quadrant contingency at L15 (Cramer's V = 0.558):

| cluster | honest_high | honest_low | lying_high | lying_low | total | character |
|---|---:|---:|---:|---:|---:|---|
| 0 | 2 | 25 | 3 | 21 | 51 | low-stakes mixed (institutional and domestic both — see note) |
| 1 | 20 | 0 | 25 | 0 | 45 | high-stakes mixed (lying + honest combined) |
| 2 | 4 | 1 | 14 | 1 | 20 | high-stakes lying-skewed |
| 3 | 0 | 14 | 0 | 20 | 34 | low-stakes mixed (a second one, more clearly casual) |
| 4 | 19 | 0 | 3 | 0 | 22 | high-stakes honest-skewed |
| 5 | 5 | 10 | 5 | 8 | 28 | mixed-stakes residual |

**Reading clusters at L15:**
- Cluster 0 (n=51) holds the bulk of low-stakes scenes regardless of truth — the model has not separated lying from honest at low stakes here. Sample texts span opioid testimony, false rent claims, casual pizza-slice denials.
- Cluster 1 (n=45) is exactly stakes-high, with truth balanced (20:25). Institutional/formal audiences (EPA inspector, hiring panel, dissertation committee). The model groups these by the *seriousness* of the situation, not by truth value.
- Cluster 2 (n=20) is high-stakes lying-skewed (14/20 lying). Loan officer, court witness, elections board scenes — institutional contexts where the lie is detected by hard documentation.
- Cluster 4 (n=22) is high-stakes honest-skewed (19/22 honest). Jordan-tells-the-court / federal-prosecutor / OSHA-investigator scenes where the *form* of the assertion (a denial of the wrongdoing) carries the truth.
- Clusters 3 and 5 are residuals.

**Geometric reading**: at L15, **stakes is the dominant geometric axis** — clusters split high-vs-low cleanly. Within high-stakes, there's a *secondary* truth-axis split (clusters 2 vs 4). Within low-stakes (clusters 0, 3), there's no truth-axis structure visible at the cluster level.

**Output contingency at L15**: V = 0.172, weak. The output is degenerate — 187/200 probes parse as `lying_high` regardless of input. The cluster geometry does NOT correspond to the model's eventual answer; the model's residual representation has organized around the *design axes* but its output layer has collapsed into a default. This is itself an interesting finding about the residual-to-output gap.

## Help probe — peak at L14

Cluster × design-quadrant contingency at L14 (Cramer's V = 0.907 — near-perfect partition):

| cluster | asking_high | asking_low | offering_high | offering_low | total | character |
|---|---:|---:|---:|---:|---:|---|
| 0 | **49** | 0 | 1 | 0 | 50 | asking-high (pure) |
| 1 | 0 | 4 | 5 | **46** | 55 | offering-low |
| 2 | 0 | **27** | 0 | 1 | 28 | asking-low (primary) |
| 3 | 0 | 0 | **32** | 0 | 32 | offering-high (pure) |
| 4 | 1 | 0 | **12** | 0 | 13 | offering-high (secondary) |
| 5 | 0 | **19** | 0 | 3 | 22 | asking-low (secondary) |

**Reading clusters at L14:**
- Cluster 0 (n=50) is essentially pure asking_high (49/50 = 98%). EMT, suicide hotline, lawyer, bank officer — emergency-and-formal asks.
- Cluster 3 (n=32) is exactly offering_high (32/32 = 100%). Bystander interventions, costly volunteer commitments — pure high-stakes offering.
- Cluster 2 (n=28) is asking_low (27/28 = 96%). "Could you grab the salt", "Could you cover my standup".
- Cluster 1 (n=55) holds offering_low (46/55 = 84%). "I'll fold yours when you're done", "Let me grab a couple of those bags".
- Clusters 4 and 5 are smaller secondary clusters for offering_high and asking_low.

**Geometric reading**: at L14, the model has organized its residual stream into clusters that nearly perfectly recover the 4-quadrant input design. Both Direction and Stakes are visible. The 6 clusters split into 4 quadrants because two quadrants (offering_high and asking_low) have two clusters each — possibly capturing within-quadrant content variation.

**Output contingency at L14**: V = 0.273, also weak. Help outputs are even more degenerate than lying — the model writes "asking, offering, high, low" listing-style for most probes; only 7 probes parse as cleanly choosing "asking", and 0 cleanly choosing "offering". The clean cluster geometry is *not* being translated to a clean behavioral answer.

## Cross-probe contrast

The help probe shows much stronger cluster geometry organization than the lying probe (V_quadrant_peak: 0.91 vs 0.56). Three contributing factors:

1. **Direction has stronger surface markers in English than truth does.** "Could you..." vs "I'll..." are syntactic signatures of asking vs offering. Lying-vs-honest depends on the relation between claim and reality — there's no comparable lexical signature.
2. **Stakes is the dominant axis in both probes.** Cluster × stakes V tops 0.86 in both probes by L11. Whatever the model is doing, it strongly attends to whether the situation is consequential.
3. **The truth axis in lying is genuinely harder.** Even with a clean constant-template design, V_truth peaks at 0.305 at L15 — the model is doing *some* representational work on truth, but it's geometrically subtle compared to stakes or direction.

## The behavioral degeneracy

Both probes elicit degenerate outputs because the appended-phrase format (`List answers single word separated by a comma:`) is being interpreted as *list these option-words* rather than *choose an answer*. Most outputs spell out "lying, honest, high, low" or "asking, offering, high, low" before degenerating into repetitions or counting.

This means the cluster × output contingency is uninformative. But it's also a research-interesting finding in its own right: **the residual stream has organized cleanly around the design axes, while the output layer has not.** The cluster representations at L14 (help) almost perfectly recover the design — yet the model can't translate that clean internal representation into a clean behavioral answer because the prompt format is ambiguous.

A v5 of either probe would address this with a different appended-phrase format. Candidates:
- `Jordan was [____ / ____]. The stakes were [____ / ____].` (fill-in form)
- `1. Was Jordan lying? 2. Were the stakes high?` (sequential numbered yes/no)
- `Choose one: Jordan was [lying / honest]. The stakes were [high / low].` (explicit choose-one)

## What the platform paradigm tells us

The contingency-table-per-layer view shows what no single-layer linear probe could:

1. The geometry **forms** in middle layers (L4–L11 build-up).
2. It **peaks** at L14–L15.
3. It **dissolves partially** by L19–L23 as the residual stream rotates toward answer-token prediction.
4. The peak-layer geometry is the cleanest representation of the design axes the model has anywhere in the forward pass.

This is consistent with the user's intuition that representations are written, used via attention, and then transformed away as the model commits to outputs. The peak-layer cluster geometry is where the model "knows" the answer most cleanly; the output layer doesn't necessarily preserve that knowledge.

## Files

- Per-layer Cramer's V tables: `docs/scratchpad/lying_v3_per_layer_contingency.csv`, `docs/scratchpad/help_v4_per_layer_contingency.csv`
- Peak-layer cluster membership: `docs/scratchpad/lying_v3_clusters_at_L15.csv`, `docs/scratchpad/help_v4_clusters_at_L14.csv`
- Parsed outputs: `data/lake/{session}/parsed_outputs.parquet`
- Authoring trackers: `docs/scratchpad/lying_v3_authoring_tracker.md`, `docs/scratchpad/help_v4_authoring_tracker.md`

## Open follow-ups

- **Re-prompt for non-degenerate outputs.** v5 of each probe with a different appended-phrase format — same scenes, just the question changed — would let us see whether the model's *behavior* matches its clean middle-layer representation.
- **Within-cluster reading audit.** I read 3 sample scenes per cluster at the peak layer; reading every scene per cluster (full 200 across the 6 clusters at the peak layer) would surface emergent within-cluster organization beyond what the design labels capture.
- **Alt-K and alt-n sweeps.** k=6 produced 4-quadrant-mapped clusters in help cleanly but split lying into a stakes-dominant pattern. Trying k=8, k=12 might surface finer truth-axis substructure within the high-stakes cluster of the lying probe.
- **Compare to existing probes.** The old lying v1/v2 and help v2/v3 probes are still on disk. Building schemas for them with the same k=6 n=15 config would let us compare cluster-geometry quality across design iterations.
