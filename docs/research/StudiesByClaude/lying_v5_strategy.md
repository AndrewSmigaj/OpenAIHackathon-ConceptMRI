# lying_v5 — Strategy: max-variance probe to surface the truth axis via clustering

This doc proposes the design for `lying_v5` BEFORE authoring. It is not the probe guide — that comes after sign-off.

## Why this iteration exists

Variance decomposition on prior probes (lying_v3, lying_v4) showed the truth axis explains only **2%** of L20 residual variance, while audience (~81%) and source (~80%) dominate. Cluster geometry at k=6 hierarchical can't surface a 2% axis. Centroid-projection on the lying-mean − honest-mean direction recovers 80–89% separability, but the user's intent is to use the platform's clustering primitive (not auxiliary projection methods) — so the probe needs to be designed such that **truth is the dominant remaining axis**, achievable only by:

- **HOLDING constant** every feature that doesn't directly express truth state (speaker, template, wrapper, capture position).
- **RANDOMIZING maximally** every other feature whose variance would compete with truth (lie content, audience-context, surface tokens) — every pair is its own unique scenario, no two pairs share structure.

The "all-or-nothing" principle: *partial* variance creates clustering structure on the partially-varied axis. A 5-category × 10-audience-pool design produces 5 large category-blobs (lie_type η²=19%) and ~50 audience-blobs (audience η²=81%). To eliminate those blobs, every probe must come from a *unique* category and a *unique* surface form, so no clumping can form.

## Format

```
Sam claims '<X>'. In reality <Y>. Answer only yes or no - is Sam lying? What is the verdict?
```

- **Speaker** (`Sam`) is constant across all probes — eliminates speaker variance.
- **Wrapper** (`claims '...'. In reality ... Answer only yes or no - is Sam lying? What is the verdict?`) is constant — eliminates template variance and fixes the "Sam" and "verdict" token positions.
- **`X`** is a first-person quoted claim made by Sam (5–7 words).
- **`Y`** is a third-person reality statement (5–7 words). Within a pair:
  - **Honest twin**: `Y` mirrors `X` with the same factual value, in third person about Sam.
  - **Lying twin**: `Y` mirrors `X` with a clearly different factual value, same word count, same grammatical shape.

Pair example (category 21, "city"):
- **Honest**: `Sam claims 'I live in Denver currently'. In reality, Sam lives in Denver currently. Answer only yes or no - is Sam lying? What is the verdict?`
- **Lying**:  `Sam claims 'I live in Denver currently'. In reality, Sam lives in Phoenix currently. Answer only yes or no - is Sam lying? What is the verdict?`

The only token-level difference between lying and honest twins is `Denver` ↔ `Phoenix` (one word, identical word count, similar token count).

## Length parity (the "within reason" constraint)

To prevent length-of-claim from becoming a clustering axis (it would, since shorter probes shift the position of the verdict token):

- Every `X` claim: target **6 words ± 1** (range 5–7).
- Every `Y` reality clause: target **6 words ± 1** (range 5–7), matching `X` shape.
- **Within a pair**: lying value and honest value have **identical word count** and matching grammatical role. (Exception: when an inflection forces ±1 syllable but token count is preserved.)
- **Across pairs**: every probe text falls in **24–28 words total**.

This is enforced category-by-category in the authoring step. Categories that would naturally need long claims (e.g. multi-clause causal explanations) are excluded.

## Capture positions

Both word-positions appear in the constant wrapper:

1. **`Sam`** — the LAST occurrence is in `is Sam lying?` (near the end). At this position, the residual has integrated the full claim+reality content and the model is being asked to evaluate Sam's truthfulness. This is upstream of `verdict`.
2. **`verdict`** — the LAST (only) occurrence is in `What is the verdict?`. Final pre-decision residual.

Both positions are captured because (a) they are at different stages of the model's reasoning and (b) the user has flagged that all probes route to the **same top expert at the verdict position across all ranks and layers** — capturing at `Sam` lets us check whether routing is more diverse upstream of the constant question-wrapper.

Implementation: run the capture twice — once with `target_word="Sam"`, once with `target_word="verdict"`. Same probe set both times. (Alternatively the backend could be extended to capture both positions in a single pass, but that is a code change requiring code-change-mode authorization.)

## Sample size

**100 unique categories × 1 pair each = 100 pairs = 200 probes.**

One pair per category. No within-category replication — within-category replication would create category-as-axis structure (the very thing we're trying to avoid). With 100 distinct content domains, no single domain's residual signature can dominate the cluster geometry; the only consistent axis remaining is truth state.

200 probes at ~30 s/probe = ~100 minutes capture per target_word position. Two captures = ~3.3 hours total. Each is a separate session.

## Lie category list (target: 100, currently 100 below)

The categories below are organized into thematic groups for the reader's benefit, but **the JSON will not have a `lie_type` axis** — every pair gets a unique `category_label` for traceability only, never used as a clustering input.

For each category, an **example claim** is shown (the actual `X`); the matching lying value will be authored with the same word count when the probe set is written.

### A. Numeric — time/duration (8 categories)
1. **time-of-day-clock**: "I arrived at 5 PM yesterday"
2. **time-of-day-precise**: "I left at 9:42 PM Tuesday"
3. **calendar-date**: "I was born on March third"
4. **year**: "I graduated college in 2018"
5. **decade-era**: "I lived there in the 90s"
6. **duration-hours**: "It took six hours total"
7. **duration-minutes**: "I waited twelve minutes outside"
8. **age-years**: "I am thirty four years old"

### B. Numeric — quantity / measure (12 categories)
9. **count-items**: "I bought five apples today"
10. **count-people**: "I invited eight guests yesterday"
11. **dollar-amount-small**: "It cost two hundred dollars"
12. **dollar-amount-large**: "I earned ninety thousand last year"
13. **distance-miles**: "I drove fifty miles yesterday"
14. **distance-feet**: "I jumped eight feet today"
15. **weight-pounds**: "I weigh one sixty pounds"
16. **height-imperial**: "I am five nine tall"
17. **temperature-fahrenheit**: "It was seventy two outside"
18. **speed-mph**: "I drove sixty five mph"
19. **percentage**: "I scored eighty percent overall"
20. **volume-liters**: "I poured three liters yesterday"

### C. Spatial — location (10 categories)
21. **city**: "I live in Denver currently"
22. **country**: "I visited Brazil last summer"
23. **us-state**: "She moved to Texas recently"
24. **continent**: "I traveled across Asia recently"
25. **street-address**: "I live on Cedar Avenue"
26. **building-landmark**: "We met at the public library"
27. **specific-room**: "I left them in the kitchen"
28. **floor-level**: "My office is the fifth floor"
29. **compass-direction**: "I drove north for hours"
30. **region-area**: "I grew up in the suburbs"

### D. Identity — person (10 categories)
31. **first-name**: "I dated Maria last year"
32. **last-name**: "I hired Mr. Cohen yesterday"
33. **full-name**: "I work with Lisa Chen"
34. **title-name**: "I voted for Senator Reyes"
35. **family-relation**: "He is my younger brother"
36. **profession**: "She works as a pediatrician"
37. **nationality**: "He was born in Argentina"
38. **age-category**: "She is a teenager still"
39. **marital-status**: "I am married since June"
40. **religious-affiliation**: "I have always been Catholic"

### E. Objects / things (12 categories)
41. **vehicle-make**: "I drive a Tesla nowadays"
42. **animal-breed**: "I own a husky named Bear"
43. **food-dish**: "I ordered the pasta tonight"
44. **color**: "My new car is red"
45. **clothing-brand**: "I bought Nike shoes yesterday"
46. **tool**: "I used a wrench earlier"
47. **medication**: "I took ibuprofen this morning"
48. **building-material**: "It is made of solid oak"
49. **drink**: "I had coffee this morning"
50. **musical-instrument**: "I play the violin daily"
51. **firearm-type**: "I own a 9mm pistol"
52. **plant-species**: "I planted oak trees yesterday"

### F. Actions / events (10 categories)
53. **mode-of-transport**: "I drove to the airport yesterday"
54. **transaction-type**: "I sold my old painting"
55. **communication-mode**: "I called my lawyer this morning"
56. **consumption-verb**: "I ate the leftovers tonight"
57. **creation-verb**: "I wrote the report myself"
58. **destruction-verb**: "I broke the window accidentally"
59. **arrival-verb**: "I arrived by train yesterday"
60. **departure-verb**: "I left by taxi yesterday"
61. **meeting-type**: "I met him over lunch"
62. **gesture-verb**: "I waved at Maria earlier"

### G. Categorical choices (10 categories)
63. **language-spoken**: "I speak Mandarin fluently always"
64. **sport-played**: "I play tennis competitively now"
65. **literary-genre**: "I write fantasy novels mainly"
66. **day-of-week**: "It happened on Tuesday morning"
67. **season**: "I traveled in summer last year"
68. **cuisine-preferred**: "I prefer Thai food generally"
69. **music-genre**: "I listen to jazz mostly"
70. **academic-major**: "I majored in physics in college"
71. **pet-species**: "I have always preferred cats"
72. **political-party**: "I belong to the Green party"

### H. State / condition (10 categories)
73. **health-status**: "I am perfectly healthy currently"
74. **emotional-state**: "I am furious about it"
75. **citizenship**: "I am a US citizen"
76. **education-degree**: "I have a PhD in physics"
77. **professional-license**: "I have a pilot's license"
78. **organizational-membership**: "I belong to the carpenters union"
79. **employment-employer**: "I am employed at Microsoft"
80. **insurance-provider**: "I am insured by Aetna"
81. **subscription**: "I subscribe to the New Yorker"
82. **voter-registration**: "I am registered as Republican"

### I. Quantifiers / comparatives / order (8 categories)
83. **quantifier-all-none**: "All the books are mine"
84. **frequency-adverb**: "I exercise every single day"
85. **comparative-size**: "I am taller than my brother"
86. **comparative-quality**: "The service was excellent throughout"
87. **order-rank**: "I was the first to arrive"
88. **causal-reason**: "I left because of traffic"
89. **probability-claim**: "I always win at chess"
90. **quantifier-most**: "Most of the staff agreed yesterday"

### J. Modal / epistemic / permission (10 categories)
91. **ability**: "I can speak French fluently"
92. **permission-authorization**: "I was authorized to enter"
93. **knowledge-claim**: "I know the password well"
94. **witness-claim**: "I saw the entire incident"
95. **speech-act-said**: "I told her the truth"
96. **hearing-claim**: "I heard the announcement clearly"
97. **belief**: "I believe the report fully"
98. **memory-claim**: "I remember every single detail"
99. **possession**: "I own seven cats currently"
100. **authorship**: "I wrote the report personally"

**Distribution check**: 8 + 12 + 10 + 10 + 12 + 10 + 10 + 10 + 8 + 10 = **100 categories**. Coverage spans numeric, spatial, identity, object, action, categorical, stative, quantifier, and modal claim types — six broad cognitive domains with 8–12 categories each.

## Authoring rules per pair

When writing the JSON, for each of the 100 categories:

1. **Pick the lying value first.** It must:
   - Be in the same content domain as the claim (a city for a city-claim, a name for a name-claim, etc.).
   - Have the **same word count** as the claim's value (`Roberto` (1) ↔ `Maria` (1); `Lisa Chen` (2) ↔ `Brandon Cole` (2); `5 PM` ↔ `9 PM`).
   - Be **clearly different** so the model unambiguously recognizes the lie (we learned subtle lies cause behavioural noise — `Marin` vs `Marina` is too subtle and produces 60% accuracy).
   - **Not** be of an inflected/negation type that adds words (`attended` → `was absent` is OK; `attended` → `did not attend` is bad — adds 2 words).

2. **Author both reality clauses.** Within the pair, reality_honest and reality_lying differ only in the consequential value, in the same syntactic position.

3. **Verify probe length.** Both the lying and honest probe must be 24–28 words total.

4. **Verify pair-internal symmetry.** A diff between the two probes should highlight ONLY the consequential value tokens.

A small validation pass after authoring will assert the above for every pair. If a pair fails, it gets re-authored, not deleted.

## What's intentionally NOT in the JSON

- **No `lie_type` axis.** Categories are tracked in `category_label` per pair only as documentation; the axis-level enum doesn't exist, so no clustering view can group by category.
- **No `magnitude` axis.** Every lying value is a **clear** mismatch (no "subtle" tier). Subtle lies produced behavioural noise in v3 (60% accuracy in identity-subtle cell) which is a confound for V_truth interpretation.
- **No within-category replication.** One pair per category, no repetition.

## Capture plan

1. **Capture session A**: `target_word="verdict"` (matches our earlier captures' position; comparable to v3/v4).
2. **Capture session B**: `target_word="Sam"` (new position; tests whether the model's reasoning at the upstream "is Sam lying?" position carries truth structure that the verdict-position residual loses).

Both run on the same `lying_v5.json`. Two separate POST `/api/probes/sentence-experiment` calls.

## Analysis plan (post-capture)

For each capture session (Sam-position and verdict-position), at L11–L17 (where prior projection-separability peaked):

1. **Variance decomposition**: η² for `truth`, `category_label` (sanity check — should be near zero with 100 unique categories), and `pair_id`. Predicted: `truth η² ≥ 10%` if the design works (vs 2% in v3/v4).
2. **Cluster V_truth at k=2, k=4, k=6**: predicted ≥ 0.85 at k=2 if truth is the dominant axis.
3. **Centroid-projection separability**: predicted ≥ 0.90, ideally ≥ 0.95 (toward the minimal_v1 ceiling of 1.00).
4. **Per-position comparison**: does Sam-position show stronger or weaker truth signal than verdict-position?
5. **Expert routing diversity**: at each capture position, count unique top-1 experts across probes per (layer, rank). Compare diversity of routing at Sam vs verdict positions. If verdict-routing is collapsed and Sam-routing is diverse, the constant question-wrapper at verdict is the explanation.

## Expert-routing observation (separate investigation, may stay open)

User noted that all probes route to the same top expert across all ranks and layers, with only small exceptions. This is suspicious. Hypothesis: at the verdict-token position, the residual is dominated by the fixed question-wrapper context, which produces near-identical routing decisions regardless of the upstream content. Capturing at the `Sam` position (which is at the question stage but not the final wrapper) provides a comparison point. If `Sam`-position routing is more diverse, that confirms the wrapper is the cause. If `Sam`-position routing is also collapsed, something more architectural is happening (possibly the harmony-format wrapping itself, or a property of the MoE on instructional prompts).

## Open questions for sign-off

1. **Probe count**: 100 pairs (=200 probes per capture session, 400 across two sessions) — OK, or scale up to 200 pairs (no obvious benefit but more N for centroid stability)?
2. **Categories**: any of the 100 you'd swap, drop, or add? In particular:
   - Numeric magnitudes: I tried to pick "real-world" values; some might be too vague (`age 34` vs `age 52` differ but both plausible — does that count as clear?).
   - Identity categories: should I avoid public-figure names entirely (e.g. real "Senator Reyes")? Currently using fictional ones.
   - Modal/epistemic: these test what the model treats as a falsifiable claim — `I believe X` is hard to falsify in principle, but the probe says "in reality Sam doesn't believe X" so reality-of-mental-state. Might be edge case.
3. **Capture cost**: two 100-min captures (3.3 hours total) — OK?
4. **Single template variant** (this proposal) vs two templates (e.g. also "Sam said 'X'. The truth: Y. ...") to push variance higher. The single-template choice keeps the wrapper truly constant; multiple templates would introduce template-as-axis structure (5 templates × 20 pairs each = 5 large clumps).

## Implementation sequence (after sign-off)

1. Author `data/sentence_sets/role_framing/lying_v5.json` (200 probes).
2. Author `data/sentence_sets/role_framing/lying_v5.md` (probe guide).
3. Validation pass: word counts, length parity, pair-internal symmetry — assert all pass.
4. Commit probe set.
5. Capture session A (`target_word="verdict"`).
6. Capture session B (`target_word="Sam"`).
7. Categorize verdicts (yes/no/other harmony classifier).
8. Build clustering schemas (k=6 default; sweep k=2,4,8 if signal is borderline).
9. Variance decomposition + projection separability + per-position comparison.
10. Expert-routing diversity analysis.
11. Findings doc.
