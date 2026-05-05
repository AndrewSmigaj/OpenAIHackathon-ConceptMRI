# lying_v3 — Bigger probe (360 probes, 6 categories × 30 pairs × 3 magnitudes) confirms H4: persistent topic dominance.

> **Update 2026-05-05 (later):** see `lying_v4_findings.md`. The "H4 confirmed, truth-state computation lives somewhere we don't measure" gloss was wrong. The truth signal IS at the verdict-token residual — projecting onto the `lying_mean − honest_mean` centroid direction at L11–L15 gives **83–89% separability** even with massive audience+source variance. Cluster V_truth at k=6 is low (0.55–0.60) because audience explains 81% of variance and source explains 81%; the truth axis is real but only 2% of variance, so clustering at k=6 doesn't pick it. Projection-onto-centroid-difference recovers it. The variance-dominance picture in this doc is correct; the interpretation about "computation lives somewhere we don't measure" is wrong.

## TL;DR

Scaling from 100 probes (`lying_diverse_v1`, 5 categories × 10 pairs) to 360 probes (`lying_v3`, 6 categories × 30 pairs × 3 lying magnitudes) does **not** lift V_truth at the verdict-token residual. Global V_truth stays at 0.51–0.60 across layers at both k=6 and k=10 — same range as `lying_diverse_v1`. The model still recognizes lying behaviorally with 80–100% accuracy across all (category × magnitude) cells. So the truth-state computation happens, but is invisible to UMAP+hierarchical clustering of the verdict-token residual when topical content varies.

The one exception is the **quantity** category: within-category V_truth = 0.78 at L17–L20, robust across all three magnitudes. No other category shows this — they all sit at 0.53–0.63 within-category. This suggests the geometric truth signal is legible specifically when the lie reduces to a **clean numeric mismatch on identical surrounding tokens**, and not when it's a categorical / semantic mismatch.

## Behavioral baseline

**360 probes, 80% lying detection / 97% honest detection overall, with mild magnitude grading:**

| Magnitude  | Lying yes / no / other | Honest yes / no / other |
|------------|------------------------|-------------------------|
| gross      | 53 / 0 / 7    (88% acc) | 58 / 0 / 2   (97% acc) |
| moderate   | 52 / 0 / 8    (87% acc) | 57 / 0 / 3   (95% acc) |
| subtle     | 48 / 2 / 10   (80% acc) | 60 / 0 / 0  (100% acc) |
| **Total**  | **153/2/25 (85% acc)** | **175/0/5 (97% acc)**  |

Per-(category × magnitude) breakdown shows two notable cells:
- `identity / subtle` — 60% lying-detection (Marin / Marina, Brian / Brain typo-similar pairs cause some false negatives)
- `role / gross` — 70% lying-detection (e.g. "Detective Park" vs "Janitor Park" — the model occasionally treats role mismatch as ambiguous)

All other cells are 80–100%. Two false negatives (lying judged as no) — both in `identity / subtle` (typo-similar names that the model genuinely conflates).

Magnitude grading is real but mild: subtle lies are 8 percentage points harder to detect than gross. Subtle honest probes are detected at 100% (since strict-equality is unambiguous regardless of magnitude).

## Geometric finding — V_truth at the verdict-token residual

### Global V_truth across layers (k=6, k=10)

| Layer | k=6 V_truth | k=6 V_lietype | k=10 V_truth | k=10 V_lietype |
|------:|:-----------:|:-------------:|:------------:|:--------------:|
| L0    | 0.525       | 0.397         | —            | —              |
| L3    | 0.503       | 0.569         | 0.514        | 0.619          |
| L11   | 0.519       | 0.486         | 0.525        | 0.561          |
| L15   | 0.569       | 0.350         | —            | —              |
| L17   | 0.594       | 0.425         | 0.597        | 0.503          |
| L20   | 0.592       | 0.436         | 0.594        | 0.508          |
| L23   | 0.544       | 0.300         | 0.550        | 0.364          |

Maximum global V_truth: **0.60 at L17–L20**, both k=6 and k=10. Minimum: 0.50 (chance) at early layers.

Compare:
- `lying_minimal_v1` (single category): V_truth = 1.000 at L3–L23.
- `lying_diverse_v1` (5 cat × 10 pairs): V_truth = 0.55–0.60 at L17+.
- `lying_v3` (6 cat × 30 pairs × 3 mags): V_truth = 0.55–0.60 at L17+.

**3.6× more probes and an additional magnitude axis don't lift V_truth at all.** The bottleneck is structural, not sample-size.

### Within-category V_truth (k=6, N=60 per category)

| Layer | time  | money | location | **quantity** | identity | role  |
|------:|:-----:|:-----:|:--------:|:------------:|:--------:|:-----:|
| L3    | 0.500 | 0.500 | 0.517    | 0.500        | 0.517    | 0.517 |
| L11   | 0.533 | 0.517 | 0.533    | 0.533        | 0.500    | 0.533 |
| L17   | 0.533 | 0.633 | 0.583    | **0.783**    | 0.550    | 0.600 |
| L20   | 0.533 | 0.633 | 0.583    | **0.783**    | 0.533    | 0.567 |
| L23   | 0.583 | 0.600 | 0.583    | 0.583        | 0.567    | 0.567 |

`quantity` stands out at L17–L20 with V_truth = 0.78. No other category exceeds 0.65.

### Within-magnitude V_truth (k=6, N=120 per magnitude)

| Layer | gross | moderate | subtle |
|------:|:-----:|:--------:|:------:|
| L3    | 0.508 | 0.508    | 0.508  |
| L17   | 0.583 | 0.600    | 0.600  |
| L20   | 0.583 | 0.600    | 0.600  |
| L23   | 0.567 | 0.542    | 0.608  |

**Magnitude does not modulate V_truth.** Subtle lies cluster as well/badly as gross lies. H2 (magnitude-graded V_truth) is refuted by the geometry, even though magnitude has a small behavioral effect (-8% accuracy).

### Within (category × magnitude) V_truth (k=6, N=20 per cell, L20)

| category   | gross | moderate | subtle |
|------------|:-----:|:--------:|:------:|
| time       | 0.55  | 0.55     | 0.55   |
| money      | 0.55  | 0.80     | 0.55   |
| location   | 0.55  | 0.50     | 0.70   |
| **quantity** | **0.75** | **0.85** | **0.80** |
| identity   | 0.50  | 0.50     | 0.60   |
| role       | 0.60  | 0.60     | 0.55   |

Quantity is the only category with consistently strong V_truth across all three magnitudes. Other categories show occasional cells in the 0.70–0.80 range but not consistently.

## Hypothesis evaluation

| Hypothesis | Outcome | Evidence |
|---|---|---|
| **H1 — Universal truth-state at higher N** | **Refuted** | Global V_truth unchanged from diverse_v1 (0.55–0.60). Within-category V_truth still mostly 0.53–0.63 except quantity. |
| **H2 — Magnitude-graded V_truth** | **Refuted (geometric)** | Within-magnitude V_truth is identical (0.55–0.61) across gross / moderate / subtle. Only mild behavioral grading (-8% accuracy on subtle lying). |
| **H3 — Detection-threshold (binary)** | **Refuted** | Subtle lies still produce above-chance V_truth and 80% behavioral commit. No threshold below which the model "stops detecting" — just gradual degradation. |
| **H4 — Persistent topic dominance** | **Supported** | More N and an additional magnitude axis don't move global V_truth. Topical content dominates the variance budget at the verdict-token residual under our clustering pipeline. |

## Why does quantity work?

Hypothesis: quantity probes are the cleanest "same noun, different number" comparisons. Claim "12 boxes" / lying evidence "47 boxes": the surrounding tokens are *identical* except one number differs. The model's residual at the verdict token can encode "the two number tokens are different" via simple attention.

Other categories are messier:
- **time**: "5:30 PM" vs "11:43 PM" — multiple tokens (number, colon, number, AM/PM). The mismatch is distributed.
- **money**: "$4,200" vs "$42,500" — different number of digits, different scale of magnitude.
- **location**: "Denver" vs "Phoenix" — different single tokens, but the embeddings of city names cluster in city-space, not in a "matches/mismatches" space.
- **identity** / **role**: name embeddings, similar issue.

Quantity isolates the truth signal as "is integer A equal to integer B?" with a single salient comparison axis. The other categories ask "is concept A equal to concept B?" which is a richer comparison the model may compute but not surface in a clusterable way at this token.

This is a methodological insight: **cluster geometry surfaces the truth signal when the truth-relevant comparison is a single numeric axis on otherwise-identical surrounding tokens.** Beyond that, the truth signal is computed-but-not-clusterable at the verdict-token residual.

## Compared to prior probes

`lying_minimal_v1` (single-category time, V_truth = 1.0): the perfect separation was a within-time-category artifact of the residual encoding "are the two time-strings literally identical?" cleanly — same as quantity here, but with N=50 per truth class instead of N=10.

`lying_diverse_v1` (5 cat × 10 pairs, V_truth ≈ 0.55–0.60): topical variance dominates. Within-category V_truth ranges 0.55–0.75 with too few samples to be reliable.

`lying_v3` (this study, 6 cat × 30 pairs × 3 mags, V_truth ≈ 0.55–0.60): confirms the diverse_v1 picture at higher N. The exception is quantity at within-category V_truth ≈ 0.78, which mirrors the minimal_v1 single-category result and shows the signal is real for clean numeric comparisons.

## Methodological implications

1. **Cluster geometry of residuals at task-relevant tokens has a structural ceiling on which axes it can surface.** When a target axis (truth state) is dominated in variance by an orthogonal axis (topical content), clustering at any reasonable k cannot separate the target axis. This is not a failure of the platform; it's a property of UMAP+hierarchical clustering applied to mixed-variance representations.

2. **Behavioural evidence and geometric evidence can disagree, and that disagreement is informative.** Here, behavior shows the model knows truth state with 85-97% accuracy. Geometry says the truth axis is below the noise floor of clustering. Both true; the truth computation lives somewhere we don't measure.

3. **For studies of low-variance design axes in the presence of high-variance content, alternative measurement is needed.** Suggested approaches:
   - Capture at a different token (the evidence value, not the verdict).
   - Trajectory-displacement analysis (compare L→L+1 motion vectors instead of absolute positions).
   - Hold topic constant, study only the design axis (the `lying_minimal_v1` strategy, which works for proof-of-existence but not for generalization).

## Files

- Probe set: `data/sentence_sets/role_framing/lying_v3.json`
- Probe guide: `data/sentence_sets/role_framing/lying_v3.md`
- Session: `session_b5a50b5d`
- Schemas: `lying_v3_k{6,10}_n15`
- Behavioural data: 153 yes / 2 no / 25 other on lying; 175 no / 0 yes / 5 other on honest

## Suggested next experiments

- **Capture at the evidence value token instead of the verdict token.** The truth comparison may be computed AT the comparison site, not propagated to the verdict token cleanly.
- **Quantity-only probe with parametric magnitude variation** (V_subtle = 0.001× off, 0.01× off, 0.1× off). Tests whether the quantity-cluster signal scales smoothly with magnitude or has a step function.
- **Paraphrase-honest test in quantity** ("12 boxes" claim / honest evidence "twelve boxes" or "a dozen boxes"). If the residual still clusters with strict-equality honest, the cluster encodes truth state in quantity; if it clusters with lying, the cluster encoded token-equality.
