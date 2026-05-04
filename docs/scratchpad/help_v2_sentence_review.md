# Quality audit: `help_direction_stakes_v2` (400 scenes, scene+question wrapper)

## Methodology

Read all 400 scenes by hand (as bare scenes, wrapper stripped). Looked for: per-quadrant templates, prose-style fingerprints, vocabulary that correlates with the design axis as a side-effect, banned-pronoun workaround artifacts, cast-naming conventions.

## Headline finding

**Each of the 4 quadrants was authored by a different subagent, and the inter-subagent prose styles are clearly distinguishable.** The 4 quadrants don't only differ in their design axes (Direction × Stakes) — they also differ in their syntactic shape, opener cadence, vocabulary register, and cast convention. This violates the project principle that templates are only allowed if applied uniformly to every sentence.

## Per-quadrant style fingerprints

### request_high (q1) — "action-led, comma-spliced, urgency vocabulary"
- Most scenes open with an **action verb** as soon as the named character appears: `Diane collapsed beside the cereal aisle clutching her left arm`, `The hiker's leg was twisted at an unnatural angle`, `Smoke was already pouring under the apartment door`, `Stranded on the highway shoulder during contractions`.
- **Countdown framing is pervasive**: `had until five o'clock`, `twelve minutes before the appellate filing deadline`, `three minutes before the board call`, `had eighteen minutes`, `before the cutoff window closed`, `nine minutes`, `eleven hours before regulators`.
- Vocabulary heavily loaded with stakes markers: `alarmingly`, `frantically`, `ticking`, `forty minutes away`, `oblivious`, `pinned`, `rolled into the ditch`, `freezing`, `drained`. These are *appropriate to the design label* but they also serve as direct surface signals.
- Comma-spliced compound sentences with three or more clauses are the dominant rhythm.

### request_low (q2) — "setting-led, deliberation verbs"
- Almost every scene starts with a **setting clause**: `At the dining table`, `On the couch after dinner`, `Standing in the half-empty guest room`, `Mid-recipe`, `On a quiet Saturday morning`, `On the porch with her morning coffee`, `Out on the back patio`, `Around the dining table on game night`.
- Heavy use of cognitive-deliberation verbs: `trying to figure out`, `puzzled by`, `weighing`, `comparing`, `uncertain whether`, `unsure how`, `debating`, `frowning at`, `hesitating over`, `fumbling with`. These are consistent across the entire batch.
- Time markers are uniformly slow/leisure: `Sunday afternoon`, `calm Wednesday afternoon`, `lunch break`, `slow Saturday morning`, `evening`. Compare to q1's `minutes`, `seconds`, `midnight`.

### offer_high (q3) — "profession-led, multi-action sequence"
- Scenes overwhelmingly identify the responder by **profession** (`paramedic`, `cardiologist`, `firefighter`, `EMT`, `K9 handler`, `pilot`, `surgeon`, `negotiator`, `attorney`, `mediator`, `litigator`, `analyst`, `engineer`, `priest`, `chaplain`, `coach`, `teacher`).
- Almost every scene chains 3+ verbs in series: `vaulted, knelt, administered, and arranged`, `pulled over, extracted, applied pressure`, `kicked open, located, carried`. This active-rescue rhythm is itself a syntactic fingerprint.
- Domain vocabulary is dense and technical: `defibrillator`, `intubated`, `femoral`, `brachial`, `abdominal thrusts`, `lateral movement`, `exfiltration`, `TRO`, `e-filed`, `affidavits`, `ACH`, `mule accounts`, `backfire`, `fireline`, `embers`. Heavy domain-coding will cluster on its own.
- Many scenes have a "respond → save → outcome" arc that produces compound sentences with 35+ words.

### offer_low (q4) — "soft-marker laden, family-role characters"
- Scenes are full of softness markers: `calmly`, `quietly`, `gently`, `without being asked`, `unprompted`, `softly`, `with a calm wave`, `without a word`. These appear in nearly every scene.
- Cast characters are frequently named by **family relation rather than profession**: `Aunt Pearl`, `Aunt Marigold`, `Uncle Vasquez`, `Cousin Jamal`, `Grandpa Soren`, `Grandpa Zoltan`, `Grandma Lillemor`, `Grandma Esme`, `Nana Rosalind`, `Big brother Quinton`, `older sister`, `little sister`. Compare to q3's profession-led cast.
- Time-of-day markers are uniformly leisure: `Saturday morning`, `Sunday afternoon`, `Over Saturday brunch`, `Each visit`, `After a long workday`, `On a sunny Saturday`. The "weekend kindness" register is dominant.
- Scenes are short on plot — they describe *one thoughtful action*, often one sentence with a setup clause and a body clause.

## What the model can use as shortcuts

The linear-probe results showed Direction at 81%, Stakes at 89%, Quadrant at 77% **at L0** — already well above chance even before scene comprehension can plausibly be deep. We attributed most of that to the position-embedding (length) confound, which accounts for ~60% on Stakes. But the *remaining* signal at L0 (and the ~99% peak from L7 onward) likely includes:

- **Vocabulary fingerprints**: stakes-words concentrated in q1/q3, leisure-words in q2/q4
- **Syntactic templates**: action-first vs setting-first openers, multi-verb series vs single-action descriptions
- **Cast convention**: profession-named vs family-relation-named characters
- **Marker-word distributions**: `quietly/calmly/gently` in q4, `frantically/alarmingly/ticking` in q1

A model can detect Direction × Stakes here without doing any actual *who's-asking-or-offering* semantic computation. The prose style alone is enough to classify probes into quadrants.

## Cross-quadrant near-duplication

Less of a problem than I expected — names across all 4 quadrants are diverse (~90 unique names per quadrant) and scenarios feel distinct. There's some predictable seeded repetition (medical seeds appear in both lying-high and offer-high) but not direct paraphrase.

## Does this invalidate the v2 findings?

Partially. The v2 paper's main claims, examined honestly:

1. **"Pattern B lens design eliminates surface clustering at the target token"** — TRUE. The wrapper question is identical across 400 probes. UMAP+hierarchical at the target position can't cluster on local surface because there's nothing local to grip on.

2. **"Direction × Stakes are linearly recoverable at near-ceiling end-to-end"** — TRUE but with an important caveat. The recoverability is partly from upstream **scene-style** signals (markers, openers, cast convention), not necessarily from semantic understanding of "who is asking for help" or "how urgent is this".

3. **"The model has the answer but the lm_head doesn't use it"** — STILL TRUE in a weaker form. Whether the residual representation came from semantic computation or from upstream template detection, the lm_head is not reading it correctly. The output gap exists either way.

So the alignment-relevant finding survives, but its interpretation needs adjusting: we cannot claim the model "deeply understands" the design axis. We can only claim the residual carries enough *something* (semantic + style mix) to be linearly decoded, and the lm_head doesn't decode it.

## Decision

**Do not re-author help_v2 wholesale**. The probe is informative and the cross-probe finding (paired with lying_v1) is robust. But for the eventual paper:

- Acknowledge the per-quadrant style confound explicitly
- Don't claim the model encodes "Direction" semantically — claim it encodes "scene cluster" (which includes Direction × Stakes among other things)
- Lean on the linear-probe / output-gap part of the finding, which is mechanistic and survives the confound

If we want to **strengthen the cross-probe argument**, the right move is a *third small probe* that uses a **uniform template across all 4 cells** — same syntactic shape everywhere, only design-axis content varying. If linear-probe accuracy stays at ceiling on that probe too, the semantic-encoding claim survives. If it drops significantly, we learned that the v2/lying findings were template-driven. Either result is publishable.

## Specific scenes flagged

Random sample of scenes that read as natural, well-written examples (no obvious template tells):
- request_high #016: `On the parking garage ledge, Holden stood barefoot eight stories above the pavement, his note crumpled in one fist and his phone discarded behind him on the cold concrete floor`
- offer_high #074: `Ms. Marquez pulled a chair beside the unconscious patient` — naturalistic, no rescue-arc formula
- request_low #064: `After dinner, twelve-year-old Salim sat at the kitchen table with his history homework, stuck on a question that asked him to list three accomplishments of the emperor Hadrian`

Scenes that read as formulaic and could be replaced if doing targeted swaps:
- request_high #020-#039 (financial sub-batch): every scene uses the countdown framing — `had until five`, `nine minutes`, `eighteen thousand by sunrise`. Could vary tempo.
- offer_low #022-#023 paired pet-feeding: very similar in structure (`Geraldo volunteered to feed his neighbor's tabby cat...` vs `While walking her own retriever each morning, Inez stopped at the apartment upstairs to feed the silver tabby...`). Minor paraphrase.
- offer_low #028-#029 paired baby-sitting: same structure (`Aunt Pearl dropped by` vs `Cousin Jamal swung by`).

But the core issue is style at the *quadrant* level, not individual scene quality.
