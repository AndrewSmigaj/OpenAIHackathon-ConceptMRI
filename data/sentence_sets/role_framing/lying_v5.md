# Lying v5 — Probe Guide

## Purpose

Test whether truth-state surfaces as the dominant clustering axis at the verdict-token residual when EVERY non-truth feature is either held constant (speaker, wrapper) or randomized maximally (lie content, surface tokens). Strategy doc: `docs/research/StudiesByClaude/lying_v5_strategy.md`.

`lying_v3` and `lying_v4` had truth η² ≈ 2% at L20 because audience and source dominated variance (~80% each). `lying_v5` eliminates audience and source variance entirely (the wrapper has neither) and forces every other axis into 100 unique values with no shared structure across pairs.

## Format

```
Sam claims '<X>'. In reality <Y>. Answer only yes or no - is Sam lying? What is the verdict?
```

- **Speaker**: always "Sam".
- **Wrapper**: always identical, including the question stem `Answer only yes or no - is Sam lying? What is the verdict?`.
- **`X`**: first-person quoted claim (5–7 words).
- **`Y`**: third-person reality clause (5–7 words). Within a pair, lying-`Y` and honest-`Y` differ ONLY in the consequential value (same word count, same syntactic position).

## Sample size

100 unique categories × 1 pair each = **200 probes** (100 lying + 100 honest matched pairs). One pair per category — no within-category replication, so no category can clump in cluster space.

## Categories (100 unique)

Organized into 10 thematic groups solely for documentation; the JSON's only category-axis is `category_label` (per-pair, never used as a clustering input):

- A. Numeric — time/duration (8): time-of-day-clock, time-of-day-precise, calendar-date, year, decade-era, duration-hours, duration-minutes, age-years
- B. Numeric — quantity/measure (12): count-items, count-people, dollar-amount-small, dollar-amount-large, distance-miles, distance-feet, weight-pounds, height-imperial, temperature-fahrenheit, speed-mph, percentage, volume-liters
- C. Spatial — location (10): city, country, us-state, continent, street-address, building-landmark, specific-room, floor-level, compass-direction, region-area
- D. Identity — person (10): first-name, last-name, full-name, title-name, family-relation, profession, nationality, age-category, marital-status, religious-affiliation
- E. Objects/things (12): vehicle-make, animal-breed, food-dish, color, clothing-brand, tool, medication, building-material, drink, musical-instrument, firearm-type, plant-species
- F. Actions/events (10): mode-of-transport, transaction-type, communication-mode, consumption-verb, creation-verb, destruction-verb, arrival-time, departure-time, meeting-type, gesture-verb
- G. Categorical choices (10): language-spoken, sport-played, literary-genre, day-of-week, season, cuisine-preferred, music-genre, academic-major, pet-species, political-party
- H. State/condition (10): health-status, emotional-state, citizenship, education-degree, professional-license, organizational-membership, employment-employer, insurance-provider, subscription, voter-registration
- I. Quantifiers/comparatives/order (8): quantifier-all-none, frequency-adverb, comparative-size, comparative-quality, order-rank, causal-reason, probability-claim, quantifier-most
- J. Modal/epistemic/permission (10): ability, permission-authorization, knowledge-claim, witness-claim, speech-act-said, hearing-claim, belief, memory-claim, possession-count, authorship

## Length parity

Validated at authoring time: every probe text falls in **26–29 words** (mean 27.5). Within every pair, lying and honest texts have **identical word count** — the only differing tokens are the consequential value (e.g. `Denver` ↔ `Phoenix`, `5 PM` ↔ `9 PM`).

## What's held constant
- Speaker (Sam)
- Sentence template
- Question wrapper (`Answer only yes or no - is Sam lying? What is the verdict?`)
- Capture position (target_word="verdict" in this set)
- Override always present (the question stem demands a binary commit)

## What varies maximally
- Lie category (100 unique, never repeated)
- Claim content (100 unique claims)
- Consequential value (100 unique honest values, 100 unique lying values)

## Output classification

Same harmony classifier as prior lying probes: parse the `final` channel after `assistantfinal`. First content word matches `^yes\b/i` → `yes`; matches `^no\b/i` → `no`; else → `other`. Truncated outputs (no `assistantfinal`) → `other`.

## Capture position B (planned follow-up)

After this set captures at `target_word="verdict"`, a sibling set `lying_v5_at_sam.json` will use identical text but `target_word="Sam"` (last occurrence: `is Sam lying?`). The Sam position is upstream of the constant question-wrapper and may show different routing/clustering behavior than the verdict position. The user has flagged that prior probes route to the same top expert at the verdict position across all ranks/layers — capturing at Sam tests whether that's a wrapper-induced collapse.

## Files
- JSON: `data/sentence_sets/role_framing/lying_v5.json`
- Strategy: `docs/research/StudiesByClaude/lying_v5_strategy.md`
- Predicted comparisons: `lying_v3_findings.md` (truth η²≈2%, V_truth k=6 ≈ 0.55), `lying_v4_findings.md` (audience-fix didn't help; centroid projection 77–89%), `lying_minimal_v1_findings.md` (single category, V_truth k=6 = 1.0).
