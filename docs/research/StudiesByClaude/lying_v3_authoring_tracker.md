# Lying probe v3 — authoring tracker + audit

## Final state

200 scenes, 50 per quadrant. Constant-template form throughout.

Template: `Jordan told [audience], "[claim]." The [evidence] showed [reality].` followed by the constant appended phrase `Is the person lying or being honest? Are the stakes high or low? List answers single word separated by a comma:`

## What's held constant across all 200 scenes

| Element | Value |
|---|---|
| Speaker name | `Jordan` (200/200) |
| Speech-act verb | `told` (200/200) |
| Reality connector verb | `showed` (193/200) — the few exceptions use natural variants where `showed` would be ungrammatical |
| Sentence structure | `Jordan told [audience], "[claim]." The [evidence] showed [reality].` |
| Appended phrase | identical for every scene; contains target word `lying` exactly once |

## What varies

- **Audience role** (intrinsic to stakes design): high-stakes uses formal audiences (the SEC, the auditor, the prosecutor, the OSHA investigator, etc.); low-stakes uses relational audiences (their roommate, their partner, their parent, their teacher, etc.).
- **Claim content**: domain spans financial, legal, medical, professional, regulatory, academic, domestic, social, consumer, school, workplace.
- **Reality content**: form of evidence (records, logs, footage, receipts, third-party reports, physical traces, environmental causes); content matches or contradicts the claim depending on truth label.
- **Claim valence (denial vs positive assertion)**: deliberately balanced after the audit — denials/positives are 14/36, 20/30, 17/33, 14/36 across the four quadrants.

## Audit results

### Word-count length per quadrant
| Quadrant | mean words | median | range |
|---|---|---|---|
| honest_high | 26.5 | 27 | 21–37 |
| honest_low | 25.8 | 26 | 20–34 |
| lying_high | 27.4 | 27 | 21–36 |
| lying_low | 26.1 | 26 | 19–38 |

Length parity ≤2 words across quadrants — minimal length-based confound.

### Linear classifier on Truth axis (lying vs honest)
| Vocabulary | 5-fold CV accuracy |
|---|---|
| Full vocabulary | 0.765 |
| Top-4 imbalanced words: `the, i, didn't, no` | **0.680** |
| Top-8 | 0.700 |
| Top-16 | 0.750 |
| Length only | 0.545 |

### Linear classifier on Stakes axis (high vs low)
| Vocabulary | 5-fold CV accuracy |
|---|---|
| Full vocabulary | 0.850 |
| Top-4 imbalanced words: `their, i, it, had` | **0.775** |
| Top-8 | 0.815 |
| Top-16 | 0.785 |
| Length only | 0.565 |

### Old marker words (v1/v2 contamination): all eliminated
| Word | Count by quadrant |
|---|---|
| matched | honest_low: 1 (everywhere else: 0) |
| confirmed | 0 |
| corroborated | 0 |
| exactly | scattered, no concentration |
| described | 0 |

### Denial vs positive-assertion balance
| Quadrant | denials | positives |
|---|---|---|
| honest_high | 14 | 36 |
| honest_low | 20 | 30 |
| lying_high | 17 | 33 |
| lying_low | 14 | 36 |

Initially honest_high was 1/49 (heavily skewed positive). After 14 confession-style scenes were swapped for truthful-denial scenes, it now matches the other quadrants.

## Honest assessment

- **Truth axis top-4 at 68%** is 8pp over the 60% guideline. Better than v1 lying (84%) and v2 lying (~71%), but not at threshold.
- The remaining 68% comes from common-word count differences (`the/i/didn't/no`), not from cherry-picked markers like the v1/v2 connectors.
- Residual signal likely reflects **intrinsic semantic content** — lying scenes describe contradictions between claim and reality, honest scenes describe corroboration. The vocabulary used to describe these different states differs even when surface markers are scrubbed.
- **Stakes axis top-4 at 77.5%** comes from audience-role intrinsics (`their X` for relational/low-stakes; `the X` for institutional/high-stakes). This is part of the design, not avoidable without making scenes implausible.

## What this probe DOES test

The model's residual representation can be probed at the appended-phrase position to ask whether it has encoded:
- the truth/lie status of the claim relative to the reality
- the high/low stakes status of the situation

A residual probe that beats the 68% top-4 baseline by a meaningful margin (e.g., >85% at any layer) indicates the model is doing something beyond the surface vocabulary signal.

## Open follow-ups

- After capture, compare residual-probe accuracy at L0 (no model processing) to L23 (deep). If L0 is already at ~70-80%, the surface-vocabulary baseline is doing most of the work and deeper probes don't add much. If L23 climbs to 95+%, the model is genuinely encoding the truth/lie semantic relationship.
- Within-quadrant variety check (post-capture): does cluster geometry pull on truth, stakes, or domain? If domain dominates, we have a different confound to address.
