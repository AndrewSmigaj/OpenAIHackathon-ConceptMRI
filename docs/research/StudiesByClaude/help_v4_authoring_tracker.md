# Help probe v4 — authoring tracker + audit

## Final state

200 scenes, 50 per quadrant. Constant-template form throughout.

Template: `Jordan told [audience], "[claim describing assistance request or offer]." The [evidence] showed [reality].` followed by the constant appended phrase `Is the person asking for or offering help? Are the stakes high or low? List answers single word separated by a comma:`

## What's held constant

| Element | Value |
|---|---|
| Speaker name | `Jordan` (200/200) |
| Speech-act verb | `told` (200/200) |
| Reality connector | `showed` (200/200) |
| Sentence structure | `Jordan told [audience], "[claim]." The [evidence] showed [reality].` |
| Appended phrase | identical for every scene; contains target word `help` exactly once |
| Word "help" in scene prose | 0/200 — never appears outside the appended phrase |

## What varies

- **Audience**: high-stakes uses formal/critical-context audiences (the EMT, the lawyer, the asylum attorney, etc.); low-stakes uses relational/casual audiences (their roommate, their parent, the colleague, the librarian).
- **Claim**: phrased as either a request (asking) or volunteered offer (offering); describes the assistance using non-`help` vocabulary.
- **Reality clause**: confirms the request/offer or its surrounding circumstances using `[evidence] showed [details]`.

## Audit results

### Word-count length per quadrant
| Quadrant | mean | median |
|---|---|---|
| asking_high | 28.6 | 29 |
| asking_low | 24.6 | 24 |
| offering_high | 32.1 | 32 |
| offering_low | 27.8 | 28 |

Length asymmetry: offering scenes ~3-7 words longer than asking scenes. Length-only baseline 67% on Direction, 69% on Stakes. **This is partial leakage — would need to be reduced for a tight design.**

### Linear classifier on Direction (asking vs offering)
| Vocabulary | 5-fold CV accuracy |
|---|---|
| Full | 0.955 |
| Top-4: `the, i'll, could, my` | **0.825** |
| Top-8 | 0.825 |
| Top-16 | 0.880 |
| Length only | 0.670 |

### Linear classifier on Stakes (high vs low)
| Vocabulary | 5-fold CV accuracy |
|---|---|
| Full | 0.910 |
| Top-4: `could, the, you, and` | **0.730** |
| Top-8 | 0.720 |
| Top-16 | 0.880 |
| Length only | 0.690 |

### Constants check
- `told`, `showed`, `jordan`: all 50/50/50/50 across quadrants ✓
- `help`: never in scene prose ✓ (only in appended phrase, where it appears once per probe)

## Honest assessment of the lexical leakage

Direction top-4 at **82.5%** is high — much higher than lying v3 (68%). The driving markers are syntactic forms intrinsic to English: `i'll` (→ offering), `could` (→ asking). These aren't cherry-picked content words; they're the pragmatic forms by which English realizes asking-vs-offering.

This is harder to scrub than lying-vs-honest because asking and offering are *intrinsically* lexically/syntactically distinct in English. Asking uses interrogative `Could you...` or modal `I need...`; offering uses declarative `I'll...` or imperative `Let me...`. A scene that asks for help in the syntactic form of an offer is nonsensical (and vice versa).

**Length asymmetry** (offering ~3-7 words longer) is more avoidable and would benefit from a revision pass. Offering scenes tend to elaborate on what's being volunteered ("I'll call an ambulance and stay with you until they arrive"), while asking scenes are often concise interrogatives ("Could you grab the salt?").

## Implications for analysis

- The cluster geometry per layer + cluster × output contingency tables (the platform's primary measure) will show whether the model's organization of the residual stream around asking-vs-offering corresponds to the design at any layer.
- Because surface vocabulary is highly predictive, a residual probe at any layer that achieves accuracy similar to the bag-of-words baseline doesn't tell us much. The platform's geometry-based read is the right substrate.
- A natural follow-up if the v4 results are interesting: a v5 with deliberately length-matched scenes and more varied asking/offering verb forms (e.g., `I need...` for asking, `Let me...` for offering, mixed across scenes) — but only if v4 surfaces a finding worth refining.

## Compared to lying v3

| Metric | lying v3 | help v4 |
|---|---|---|
| Direction/Truth top-4 | 68% | 82.5% |
| Stakes top-4 | 77.5% | 73% |
| Length asymmetry | minor (~2 words) | meaningful (~3-7 words) |
| Surface markers | content (denial words) | syntactic (modal forms) |

The lying probe is the cleaner-design probe of the two, with the help probe carrying expected English-language asking/offering syntactic correlates.
