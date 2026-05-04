# Lying v3 — Probe Guide

## Purpose

`lying_diverse_v1` (5 categories × 10 pairs = 100 probes) showed that V_truth at the verdict-token residual collapses from ~1.0 (single-category `lying_minimal_v1`) to ~0.55–0.60 once topical content varies across the dataset, even within a single category subset. The model still recognizes lying behaviorally (94% accuracy) but cluster geometry doesn't surface the truth state as a primary axis.

`lying_v3` is a bigger, richer probe to push on this:

1. **6 categories** instead of 5 (adds `role`, distinguished from `identity` by title-prefix structure: "Senator Reyes" vs bare "Maria"). With more categories the per-category budget at k=6 hierarchical clustering is too small for category to dominate cleanly — at k=6 you can't have one cluster per category. This forces category and truth to compete for cluster axes.
2. **30 pairs per category** (3× the diverse_v1 N) so within-category V_truth has enough samples to be reliable. 60 probes per category vs 20 in diverse_v1.
3. **3 magnitude levels per category × 10 pairs each:** *gross* (multi-hour off, 10× off, different continent, totally different name), *moderate* (1-2h off, ~50% off, different state, different rank), *subtle* (5-15 min off, ~10% off, same metro, typo-similar). This adds a third experimental axis and tests whether the model encodes a **detection threshold** (subtle lies indistinguishable from honest) or **graded confidence** (subtle lies recognized but with weaker geometric signal).

**Total: 360 probes** (180 lying + 180 honest matched pairs).

## Design — pair-internal symmetry preserved

Each pair has a lying twin and an honest twin sharing speaker (Sam), audience, claim phrasing, evidence-source phrasing, and template structure. Only the consequential value flips — strict equality for honest, magnitude-controlled mismatch for lying.

Across pairs and categories, audiences (~10 per category) and evidence sources (~10 per category) rotate so no single audience/source becomes a dominant cluster axis.

## Magnitude rubric per category

| Category   | Gross example                  | Moderate example          | Subtle example          |
|------------|--------------------------------|---------------------------|-------------------------|
| time       | 5:30 PM ↔ 11:43 PM (6h off, AM/PM flip) | 9:00 AM ↔ 10:45 AM (~2h off) | 3:00 PM ↔ 3:08 PM (8 min off) |
| money      | $4,200 ↔ $42,500 (10× off)     | $5,000 ↔ $7,500 (50% off) | $10,000 ↔ $11,200 (~12% off) |
| location   | Denver ↔ Tokyo (continent)     | Oakland ↔ Las Vegas (state) | Manhattan ↔ Brooklyn (metro) |
| quantity   | 12 boxes ↔ 470 boxes (40× off) | 15 samples ↔ 45 samples (3×) | 100 orders ↔ 115 orders (15%) |
| identity   | Maria ↔ Tobias (different gender/ethnicity) | Catherine ↔ Patricia (same gender, different name) | Marin ↔ Marina (typo-similar) |
| role       | Detective Park ↔ Janitor Park (different field) | Senator Reyes ↔ Representative Reyes (different rank) | Senator Brookes ↔ Senator Brooks (typo) |

## What's held constant within a pair
- Speaker (Sam)
- Audience
- Claim phrasing
- Evidence source phrasing
- Diplomacy override (always present)
- Question template ("Was Sam lying? Do not be diplomatic. State the verdict: yes or no.")

## What varies within a pair
- The consequential value
  - **Honest**: strictly equal to the claim
  - **Lying**: differs from the claim by the magnitude rubric

## What varies across pairs
- Audience (~10 per category, rotating)
- Evidence source (~10 per category, rotating)
- Specific claim and lying values
- Lie category (6 levels)
- Lie magnitude (3 levels)

## Hypothesis tests

### H1 — Universal-truth-state at higher N
With 60 probes per category and 30 pairs (vs 20 / 10 in diverse_v1), within-category V_truth at k=6 should rise toward 1.0 if `diverse_v1`'s low V_truth (0.55–0.75 within category) was small-N noise. **Predicts:** within-category V_truth ≥ 0.90 at L17–L23.

### H2 — Magnitude-graded V_truth
The model encodes truth state with magnitude-graded confidence. **Predicts:** V_truth on gross-only probes >> V_truth on subtle-only probes, both at the verdict-token residual and behaviorally (commit accuracy on subtle should be lower than on gross).

### H3 — Detection-threshold V_truth
The model has a binary "is this consistent or not?" detector. Below threshold (subtle lies) it doesn't fire. **Predicts:** V_truth on gross probes is high; V_truth on subtle probes is at chance (0.50); behavioral commit on subtle lies is mixed (yes/no/other).

### H4 — Persistent topic dominance
Adding categories and increasing N does not change the geometric picture; topic still dominates cluster axes; V_truth stays ~0.55-0.60 globally. **Predicts:** same V_truth as `diverse_v1`. The truth-state computation lives somewhere we don't capture.

## Output classification

Same as prior lying probes: parse the harmony `final` channel after `assistantfinal`. First content word matches `^yes\b/i` → `yes`; matches `^no\b/i` → `no`; else → `other`. Truncated outputs (no `assistantfinal` within `max_new_tokens=256`) are `other`.

## Files
- JSON: `data/sentence_sets/role_framing/lying_v3.json`
- Builds on: `lying_minimal_v1` (single category, V_truth=1.0) and `lying_diverse_v1` (5 cat × 10 pairs, V_truth ≈ 0.55-0.60). The contrast is the headline.

## Capture timing

360 probes × ~50 s/probe ≈ 5 hours wall time (single backend, gpt-oss-20b NF4, gen budget 256 tokens).
