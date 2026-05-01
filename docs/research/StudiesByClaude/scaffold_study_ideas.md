# Scaffold-modulation study ideas — candidate baseline probes and tentative directions

**Started:** 2026-04-29. Living document.

## Quick-reference index

For navigating this doc:

- [Methodological framing](#methodological-framing-refined) — what scaffold-modulation studies do, and what makes a probe a good fit.
- [Candidate inventory](#candidate-inventory) — 165 candidate probes organized in 28 categories (A–AG).
- [Top picks ranked by promise](#top-picks-ranked-by-promise) — 10 most-likely-to-yield candidates, with reasoning.
- [Ready-to-author candidate sentence batches](#ready-to-author-candidate-sentence-batches-top-picks) — 5–10 minimal pairs drafted for each top-tier candidate (ready to scale up).
- [Study templates](#study-templates) — five design templates from single-probe scaffold-effect to mid-window injection.
- [Cross-probe pairings](#cross-probe-pairings--which-probes-test-things-that-scaffolds-of-interest-should-jointly-modulate) — recommended probe pairings for testing scaffold-suite generality.
- [Scaffold-suite recommendations](#scaffold-suite-recommendations) — five suites of scaffolds organized by hypothesis they test.
- [Research questions](#research-questions-this-brainstorm-could-address) — 7 research questions and the design that fits each.
- [Common pitfalls](#common-pitfalls-and-how-to-avoid-them) — failure modes from prior work; what to avoid.
- [Tentative ideas](#tentative-ideas-not-for-v3-directly) — ideas worth keeping for later (mid-window injection, lens-stacking, cross-probe transfer at scale).
- [What we don't know yet](#what-we-dont-know-yet-research-gaps) — research gaps and open questions.
- [First concrete steps](#first-concrete-steps-pick-one) — recommended next moves.

## Quick category index (probe candidates by axis type)

| Letter | Category | Range |
|---|---|---|
| A | Polysemy lenses | 1–14 |
| B | Genre / discourse-mode lenses | 15–21 |
| C | Affective / interpersonal-register lenses | 22–28 |
| D | Voice / authority lenses | 29–32 |
| E | Reasoning-mode lenses | 33–39 |
| F | Modal / epistemic lenses | 40–45 |
| G | Subject-domain pair lenses | 46–50 |
| H | Code / formal-language lenses | 51–55 |
| I | Speech-act / pragmatic lenses | 56–61 |
| J | Self-reference / meta-discourse lenses | 62–65 |
| K | Conceptual-relation lenses | 66–71 |
| L | Counterfactual / hypothetical lenses | 72–76 |
| M | Theory-of-mind / social-cognition lenses | 77–82 |
| N | Safety / alignment-relevant lenses | 83–87 |
| O | Cognitive-process lenses | 88–92 |
| P | Discourse-purpose / pragmatic lenses | 93–96 |
| Q | Domain-knowledge integration lenses | 97–99 |
| R | Time / aspect lenses | 100–102 |
| S | Cognitive-bias / decision-framing lenses | 103–108 |
| T | Identity / role lenses | 109–111 |
| U | Uncertainty-management lenses | 112–114 |
| V | Action-attribution lenses | 115–117 |
| W | Domain-specific lenses | 118–124 |
| X | Cultural / cross-cultural lenses | 125–129 |
| Y | Linguistic-feature lenses | 130–135 |
| Z | Time-sensitivity lenses | 136–139 |
| AA | Embodiment / abstraction lenses | 140–143 |
| AB | Source-credibility / trust lenses | 144–147 |
| AC | Communication-channel / register lenses | 148–151 |
| AD | Inference-mode lenses | 152–155 |
| AE | Self-model / model-as-agent lenses | 156–159 |
| AF | Recursion-depth lenses | 160–163 |
| AG | Knowledge-time lenses | 164–165 |

---

## Methodological framing (refined)

A **probe** = a designed sentence set defining the data the lens sees.
A **schema** (UMAP + hierarchical clustering on captured residuals) = **one lens** that picks up **one internal understanding** the model carries — even though that understanding may be implemented across multiple layers and many experts.
A **basin** = a cluster within that lens, a stable region of residual-stream space the model occupies for a given input. Basins are functional states; basin membership predicts behavioral response (paper §4.1).
A **scaffold** = an intervention (a prompt prefix, suffix, or wrapper) added on top of the probe sentences after baseline basins are established. Scaffold studies ask: under scaffold X, does the routing of probe sentences through baseline basins change?

A study has the shape: **(probe defines data) × (schema defines lens) × (scaffolds define interventions)**. The question is always: does the scaffold suppress routing through one basin, redirect routing to a different basin, or leave routing unchanged?

A scaffold-modulation study tests one understanding at a time. To study how a scaffold changes the model across multiple understandings, you need multiple probes with the same scaffold suite (cross-probe transfer).

## What makes a good probe candidate

- **One clear conceptual axis** with two (or few) opposing modes the model maintains naturally.
- **Clean baseline basins likely** — model represents the axis distinctly enough that hierarchical clustering at some layer recovers ≥80%-pure clusters per mode.
- **Easy to author as minimal pairs** — same content, different framing along the axis. Lets us isolate the axis from other variation.
- **Single understanding** — the axis is one thing, not entangled with several confounds. A probe that mixes "fictional vs real" with "emotional vs neutral" is two lenses smushed together.
- **Not trivially confounded with scaffold style** — don't pair a "formal/casual axis" probe with formal/casual scaffolds. Circular.
- **Behaviorally consequential** — basin membership should correlate with some observable behavioral output (text continuation tagged for the relevant property). Without this, the lens is descriptive but not functional.

## Rejection criteria — what's NOT a good probe

- **Axis depends on subjective interpretation** that varies by reader (no clean ground truth → no clean basin assignment).
- **Axis perfectly predictable from surface tokens trivially** (then scaffolds add no information; you'd just be measuring tokens).
- **Axis requires extended context to manifest** (incompatible with single-sentence basin identification at the published probe scale).
- **Axis is an evaluation/judgment** the model makes rather than a representation it maintains. (E.g., "is this content safe?" — that's a downstream judgment, not a representational lens.)
- **Axis is too narrow** — only a few examples possible, can't author 80+ minimal pairs per category.

## Candidate inventory

For each candidate: the axis, brief example, plausible-baseline-quality assessment, and scaffold-modulation questions worth asking.

### A. Polysemy lenses (lexical disambiguation)

Pattern: same word, different senses, context determines which sense is active. Easy to author. Tank polysemy probe in the published paper is the validated example.

Each polysemy probe answers: does the model maintain a clean per-sense basin? And: does scaffold X shift sense commitment on ambiguous sentences?

| # | Word | Senses | Example sentences |
|---|---|---|---|
| 1 | **bank** | financial / river | "The bank approved her loan after reviewing the paperwork." / "The bank was muddy from the recent rain." |
| 2 | **bat** | animal / sports | "The bat flew out of the cave at dusk." / "He swung the bat and hit a home run." |
| 3 | **run** | athletic / program / management / flow | "She runs five miles every morning." / "I'll run the script and check the output." / "He runs the marketing department." / "Water runs through the pipes." |
| 4 | **light** | illumination / weight / calorie | "Turn off the light before you leave." / "The package was light enough to carry easily." / "She ordered the light beer." |
| 5 | **bow** | weapon / ribbon / ship / greeting | "She drew the bow back and released the arrow." / "Tie the bow with red ribbon." / "Waves crashed over the bow." / "She gave a bow to the audience." |
| 6 | **plant** | botanical / factory / surveillance | "The plant grows best in sunlight." / "The plant employs five hundred workers." / "Police suspected an undercover plant in the meeting." |
| 7 | **spring** | season / water / coil / jump | "Spring brings warmer weather." / "The spring fed cool water to the village." / "The spring inside the pen was broken." / "She watched him spring across the rocks." |
| 8 | **match** | fire-starter / sports-game / equivalence / partner | "He lit a match to start the fire." / "The match ended in a tie." / "The wallpaper doesn't match the carpet." / "They were a perfect match." |
| 9 | **fair** | equitable / carnival / pale / moderate | "The judge made a fair ruling." / "We went to the county fair." / "She has fair skin that burns easily." / "His chances are only fair." |
| 10 | **star** | celestial / celebrity / shape / rating | "The star shone brightly in the night sky." / "The star walked the red carpet." / "She drew a star on her notebook." / "The hotel earned five stars." |
| 11 | **bug** | insect / software defect / surveillance device / annoy | "A bug crawled across the leaf." / "The team fixed the bug in the release." / "They suspected the room had a bug." / "Don't bug me right now." |
| 12 | **chip** | semiconductor / snack / fragment / gambling token | "The chip overheated under load." / "She passed the bowl of chips around." / "A chip of glass cut his finger." / "He stacked his chips on red." |
| 13 | **pitch** | throw / tone / sales-attempt / tar / field | "He threw a fast pitch." / "The pitch was too high for me to sing." / "His pitch convinced the investors." / "Workers covered the road in pitch." / "Players ran across the pitch." |
| 14 | **wave** | water-surface / hand-gesture / electromagnetic / surge | "A wave crashed against the shore." / "She gave a wave from across the room." / "The wave traveled at the speed of light." / "A wave of nostalgia swept over him." |

**Scaffold candidates for polysemy probes:** domain-priming scaffolds ("As an aquarium specialist...", "From a military analyst's perspective..."). Direct test: does priming a domain shift basin commitment on ambiguous sentences? Should work — it's exactly what context-priming does.

### B. Genre / discourse-mode lenses

Pattern: same content, different genre framing. Tests whether the model maintains a "what kind of text is this" representation independent of surface vocabulary.

| # | Axis | Description |
|---|---|---|
| 15 | **Fictional vs non-fictional content** | Same described subject (a city, a person, an event) framed as part of a novel vs as encyclopedia article. Variant of suicide-letter pattern on neutral content. |
| 16 | **News-reporting vs opinion-editorial** | Same factual content presented as straight reporting vs as op-ed argument. |
| 17 | **Instructional vs descriptive** | "How to bake bread" vs "What bread is." Same domain, different speech-act target. |
| 18 | **Explanation vs argument** | "X happens because Y" vs "X is good because of Y." Causal explanation vs evaluative argument. |
| 19 | **Question vs assertion** | Interrogative vs declarative form for the same content. ("Is the sky blue today?" vs "The sky is blue today.") |
| 20 | **Direct vs hedged statement** | "X is true" vs "X may be true depending on..." |
| 21 | **Fictional-fictional** | The story-within-a-story distinction. Prompts about a character writing fiction (one level of fiction) vs about a character in a fiction (one level of fiction, different role). Tests whether the model nests fictional frames. |

**Scaffold candidates:** task-framing scaffolds ("Treat this as a journalism task." / "Treat this as fiction-writing." / "Provide a scholarly analysis."). Tests whether the scaffold can override the natural genre signal in the content.

### C. Affective / interpersonal-register lenses

Pattern: same propositional content, different affective framing. Tests whether the model maintains a "warmth/distance" lens.

| # | Axis | Example pair |
|---|---|---|
| 22 | **Sympathetic vs clinical** | "She lost her son in the accident — a tragedy that left her family devastated." vs "Patient lost a first-degree relative in an MVA; reports significant disruption to family functioning." |
| 23 | **Praise vs criticism** | "Her work on the project was outstanding." vs "Her work on the project was inadequate." |
| 24 | **Confidence vs hedging** | "X is the case." vs "X may possibly be the case under certain conditions." |
| 25 | **Personal vs impersonal** | "I think the policy is wrong." vs "The policy may be deemed problematic by some observers." |
| 26 | **Approval vs disapproval** | Endorsing a proposal vs declining it. |
| 27 | **Empathetic vs detached** | Counselor-style response vs analyst-style response to same emotional content. |
| 28 | **Polite vs blunt** | Same request softened with politeness markers vs phrased directly. |

**Scaffold candidates:** the "auditor / clinical / zero-empathy" scaffold from earlier. Test: under that scaffold, does sympathetic-framed content still route to the sympathetic basin, or migrate to the clinical basin? Tests the auditor's "empathy-suppression" lever specifically.

### D. Voice / authority lenses

Pattern: same content, different speaker authority/stance. Tests whether model represents "who is speaking" as a feature.

| # | Axis | Example pair |
|---|---|---|
| 29 | **Expert-voice vs novice-voice** | "Quantum entanglement involves correlated quantum states across spatially separated particles." vs "Quantum entanglement is when particles that are far apart somehow stay connected." |
| 30 | **Authoritative vs deferential** | "Bring the report by 5pm." vs "Could you possibly bring the report by 5pm if you have a chance?" |
| 31 | **Insider vs outsider terminology** | Domain-jargon framing vs explainer framing for same concept. |
| 32 | **Confident assertion vs admitting uncertainty** | "The answer is X." vs "I'm not sure but I think the answer might be X." |

**Scaffold candidates:** persona scaffolds ("You are a domain expert," "You are a teacher explaining to a child"). Test: do they shift the routing despite identical content?

### E. Reasoning-mode lenses (closest to the auditor question)

Pattern: same subject, different cognitive task framing. The most direct test of whether scaffolds engage different "modes of thought."

| # | Axis | Example pair |
|---|---|---|
| 33 | **Generative vs analytical task** | "Write a poem about loneliness." vs "Analyze the structure of poems about loneliness." Same domain, different cognitive task. **Closest natural baseline to the auditor question.** |
| 34 | **Computational vs proof-style** | "Compute the value of X." vs "Prove that X has property Y." |
| 35 | **Descriptive vs evaluative** | "What is X." vs "Is X good/correct." |
| 36 | **Hypothesis vs conclusion** | "It might be that X." vs "It is the case that X." |
| 37 | **Speculation vs report** | "X might happen." vs "X happened." |
| 38 | **Diagnostic vs prescriptive** | "What's wrong with this code?" vs "How should this code be fixed?" |
| 39 | **Critique vs explanation** | "What is wrong with argument X?" vs "What is argument X about?" |

**Scaffold candidates:** task-framing scaffolds. ("Approach this as a creative writing task." / "Approach this as analytical critique." / "Provide structured diagnostic analysis.") Tests whether scaffolds can flip the cognitive-mode commitment despite identical content.

### F. Modal / epistemic lenses

Pattern: same propositional content, different modal framing.

| # | Axis | Example pair |
|---|---|---|
| 40 | **Certain vs uncertain** | "The bridge will collapse." vs "The bridge may collapse." |
| 41 | **Permitted vs forbidden** | "You can do X." vs "You can't do X." |
| 42 | **Past vs future** | "She arrived early." vs "She will arrive early." |
| 43 | **Hypothetical vs actual** | "If she had arrived early..." vs "She arrived early." |
| 44 | **Necessary vs contingent** | "Triangles must have three sides." vs "She might bring lunch." |
| 45 | **Possible vs impossible** | "It's possible to walk on water." vs "It's impossible to walk on water." |

**Scaffold candidates:** epistemic-stance priming. ("Speak only of what is certain." / "Consider only hypotheticals.") Tests whether scaffolds enforce a modal stance on content that doesn't naturally have it.

### G. Subject-domain pair lenses

Pattern: domain-pair contrast. Tests whether the model carries a "what knowledge domain is this" lens.

| # | Axis | Example pair |
|---|---|---|
| 46 | **Scientific vs humanistic** | A description of consciousness in neuroscience terms vs in literary terms. |
| 47 | **Quantitative vs qualitative** | A description of a city's character via census numbers vs via cultural anecdote. |
| 48 | **Historical vs contemporary** | The same political phenomenon discussed as historical analysis vs current event. |
| 49 | **Theoretical vs applied** | "What is the principle of X." vs "How is X used in practice." |
| 50 | **Macro vs micro** | "How does the economy work." vs "What happens when an individual buys bread." |

**Scaffold candidates:** domain-priming scaffolds. ("Approach as a scientist." / "Approach as a humanist.") Test: do they actually shift internal representation, or just style?

### H. Code / formal-language lenses

Pattern: same algorithm or task, different code style. Useful for studying scaffold effects on structured output.

| # | Axis | Example pair |
|---|---|---|
| 51 | **Imperative vs declarative code** | A `for` loop vs a `map` expression for the same task. |
| 52 | **Pseudocode vs production code** | Algorithmic sketch vs full implementation. |
| 53 | **Code vs natural-language explanation** | The algorithm in code vs the algorithm in prose. |
| 54 | **Refactoring vs writing-from-scratch** | "Improve this code" vs "Write code that does X." |
| 55 | **Test-first vs implementation-first** | "Write tests for X." vs "Write code for X." |

**Scaffold candidates:** code-style scaffolds ("Write idiomatic Python." / "Optimize for readability." / "Optimize for performance."). Tests whether scaffolds shift internal representation of "what kind of code is this."

### I. Speech-act / pragmatic lenses

Pattern: pragmatic intent of the utterance.

| # | Axis | Example pair |
|---|---|---|
| 56 | **Informing vs persuading** | "X is the case." vs "X is the case, and you should agree because..." |
| 57 | **Teaching vs evaluating** | "Here's how to do X." vs "Here's whether you've done X correctly." |
| 58 | **Reporting vs interpreting** | "What happened was X." vs "What happened means Y." |
| 59 | **Advisory vs descriptive** | "You should do X." vs "Some people do X." |
| 60 | **Sincere vs performative** | "I think X." vs "I promise X." (Asserting a fact vs performing an act.) |
| 61 | **Direct vs indirect speech** | "She said 'I'm tired.'" vs "She said she was tired." |

**Scaffold candidates:** pragmatic-stance scaffolds ("Be objective and informative." / "Argue for the position." / "Just describe, don't evaluate."). Tests whether scaffolds modulate routing through pragmatic-mode basins.

### J. Self-reference / meta-discourse lenses

Pattern: claims about objects vs claims about claims.

| # | Axis | Example pair |
|---|---|---|
| 62 | **First-order vs meta-discourse** | "X is true." vs "The claim that X is true is well-supported." |
| 63 | **Predictive vs descriptive** | "X will happen." vs "X is happening." |
| 64 | **Editorializing vs reporting** | "X happened, which was a tragedy." vs "X happened." |
| 65 | **Quotation vs assertion** | "Some people say X." vs "X is the case." |

**Scaffold candidates:** "stay first-order" / "make explicit the meta-claim" scaffolds. Probably weaker effects than other categories — meta-discourse isn't always a clean lens.

### K. Conceptual-relation lenses

Pattern: relational structure in content. Whether the model carries a "what is the relation between these elements" lens.

| # | Axis | Example pair |
|---|---|---|
| 66 | **Cause vs effect** | "The drought caused the famine." vs "The famine resulted from the drought." Same propositional content, different focus. |
| 67 | **Premise vs conclusion** | "Given that X..." vs "Therefore X..." |
| 68 | **Means vs ends** | "She studied to pass the exam." (means) vs "She passed the exam by studying." (ends) |
| 69 | **Whole vs part** | Description of an organization vs description of one of its departments. |
| 70 | **Type vs token** | "Lions are dangerous." (type) vs "That lion is dangerous." (token) |
| 71 | **Generic vs specific** | "Doctors recommend X." vs "Dr. Smith recommends X." |

**Scaffold candidates:** "focus on the cause" / "focus on the effect" / "give specific examples" / "give general principles." Subtle but might modulate.

### L. Counterfactual / hypothetical lenses

Pattern: actual world vs counterfactual worlds.

| # | Axis | Example pair |
|---|---|---|
| 72 | **Actual vs counterfactual** | "She arrived on time." vs "If she had arrived on time, she would have caught the train." |
| 73 | **Necessary vs contingent** | "Two plus two must equal four." vs "She might bring lunch tomorrow." |
| 74 | **Possible vs impossible** | "It's possible to learn five languages." vs "It's impossible to be in two places at once." |
| 75 | **Alternative-history scenario** | "What if the war had ended in 1944?" vs the actual historical claim. |
| 76 | **Counterfactual-yes vs counterfactual-no** | Different antecedents to the same consequent. ("If she had studied..." vs "If she hadn't studied...") |

**Scaffold candidates:** "stay grounded in actual" / "explore the counterfactual" / "consider all possibilities." Tests counterfactual-mode engagement.

### M. Theory-of-mind / social-cognition lenses

Pattern: representations of other minds, beliefs, intentions. Some of these may be hard to capture in single-sentence probes.

| # | Axis | Example pair |
|---|---|---|
| 77 | **First-person vs third-person mental state** | "I think the meeting will be boring." vs "She thinks the meeting will be boring." |
| 78 | **Belief vs knowledge** | "He believes the earth is flat." vs "He knows the earth is round." |
| 79 | **Intent vs action** | "She planned to leave early." vs "She left early." |
| 80 | **Group vs individual social attribution** | "The committee decided X." vs "The chairperson decided X." |
| 81 | **Cooperative vs competitive framing** | "They're working together on this project." vs "They're competing for the project." |
| 82 | **Genuine vs deceptive intent** | "She told them honestly." vs "She told them a lie." (Mind-state target.) |

**Scaffold candidates:** perspective-taking scaffolds ("Consider this from her point of view." / "Stay in third-person."). Tests perspective-mode shifts.

### N. Safety / alignment-relevant lenses (sensitive — scaffold-modulation studies on these warrant careful framing)

Pattern: representations relevant to safety/alignment.

| # | Axis | Example pair |
|---|---|---|
| 83 | **Trustworthy vs suspicious source** | Same claim attributed to a credible vs questionable source. |
| 84 | **High-risk vs low-risk activity description** | Description of skydiving vs description of crocheting. |
| 85 | **Reversible vs irreversible action** | "She could change her mind." vs "Once made, the decision was irreversible." |
| 86 | **Vulnerable population vs general population** | Same medical info phrased for general adult vs for a child or someone with a chronic condition. |
| 87 | **Genuine-distress vs performative-distress** (variant of suicide-letter) | Real emotional content vs explicitly creative-writing content. |

**Scaffold candidates:** safety-priming scaffolds ("Treat this with appropriate care." / "Be clinical and precise."). Could test whether safety-relevant routing is modulable.

### O. Cognitive-process lenses

Pattern: representations of different kinds of cognitive task.

| # | Axis | Example pair |
|---|---|---|
| 88 | **Working-memory load — high vs low** | A short factual prompt vs a prompt requiring tracking many items. |
| 89 | **Recursive depth — shallow vs deep** | "Alice said X." vs "Alice said that Bob said that Carol said X." |
| 90 | **Sequential vs parallel** | "First do X, then Y." vs "Do X and Y at the same time." |
| 91 | **Pattern-matching vs reasoning** | "Pick the next number in the sequence." vs "Explain why this argument is flawed." |
| 92 | **Recall vs computation** | "What is the capital of France?" vs "What is 743 × 28?" |

**Scaffold candidates:** task-framing scaffolds. Probably modulate weakly — these distinctions live in early parsing rather than in mode-shift.

### P. Discourse-purpose / pragmatic lenses (refined)

| # | Axis | Example pair |
|---|---|---|
| 93 | **Statement vs question (same content)** | "The sky is blue today." vs "Is the sky blue today?" |
| 94 | **Literal vs figurative** | "She lifted the heavy box." vs "She lifted the weight of his depression off her shoulders." |
| 95 | **Sincere vs ironic** | "Wonderful weather we're having." (genuine) vs (sarcastic). May be hard to disambiguate in isolation. |
| 96 | **Performative vs descriptive** | "I promise to do X." vs "I will do X." (Subtle — performatives have pragmatic force.) |

### Q. Domain-knowledge integration lenses

Pattern: how the model uses background knowledge.

| # | Axis | Example pair |
|---|---|---|
| 97 | **Single-domain vs cross-domain reasoning** | A biology question that's only about biology vs one that requires bringing in chemistry. |
| 98 | **Common-sense vs technical knowledge** | "Why does ice float?" common-sense answer vs technical thermodynamic answer. |
| 99 | **Foreground vs background information** | What's the new info vs what's the established context in a sentence. |

### R. Time / aspect lenses

| # | Axis | Example pair |
|---|---|---|
| 100 | **Habitual vs episodic** | "She runs every morning." (habitual) vs "She ran this morning." (episodic) |
| 101 | **Continuous vs punctual** | "He was reading." vs "He read the page." |
| 102 | **Anticipatory vs reflective stance** | "Tomorrow's meeting will be important." vs "Yesterday's meeting was important." |

### S. Cognitive-bias / decision-framing lenses (psychologically-grounded)

These probes draw on psychological literature about how framing affects representation. Could be high-yield — psychologists have spent decades finding clean axes.

| # | Axis | Example pair |
|---|---|---|
| 103 | **Gain vs loss framing** | "There's a 70% chance of saving 200 lives." vs "There's a 30% chance of losing 100 lives." (Same expected value.) |
| 104 | **Anchoring high vs anchoring low** | "Is the population of city X greater than 10 million?" vs "Greater than 10 thousand?" (then ask for the estimate) |
| 105 | **Sunk-cost present vs absent** | A decision described after substantial prior investment vs without. |
| 106 | **Default-yes vs default-no** | An option presented as the default vs as a non-default choice. |
| 107 | **Trolley-problem framings** | Utilitarian phrasing vs deontological phrasing of the same dilemma. |
| 108 | **Newcomb's-paradox framings** | Different phrasings of the same decision-theoretic puzzle. |

**Scaffold candidates:** "be coldly rational" / "consider the principle, not the outcome" / "consider the outcome, not the principle." Tests decision-framing-mode shifts.

### T. Identity / role lenses

| # | Axis | Example pair |
|---|---|---|
| 109 | **Personal-identity-stable vs disrupted** | Description of a person before vs after a significant change. (Ship-of-Theseus style identity probe.) |
| 110 | **Helper vs bystander role** | Same observed event from "what should I do" vs "what's happening" framing. |
| 111 | **Insider-perspective vs outsider-perspective on cultural practice** | Description of a ritual from a participant's view vs from an outside-observer's view. |

### U. Uncertainty-management lenses

| # | Axis | Example pair |
|---|---|---|
| 112 | **Confident-incorrect vs hedged-correct** | Boldly wrong vs cautiously right answer to the same factual question. (Calibration probe.) |
| 113 | **Wisdom-of-crowds vs individual-expertise framing** | Same prediction phrased as "many people say" vs "the expert says." |
| 114 | **Probabilistic vs deterministic outcome framing** | "The drug helps about 70% of patients." vs "The drug helps." |

### V. Action-attribution lenses

| # | Axis | Example pair |
|---|---|---|
| 115 | **Intentional vs accidental** | "She broke the vase on purpose." vs "She broke the vase by accident." |
| 116 | **Active vs passive agent framing** | "He wrote the letter." (active) vs "The letter was written by him." (passive) |
| 117 | **Self-caused vs externally-caused** | "She decided to go." vs "Circumstances forced her to go." |

### W. Domain-specific lenses

These probe the model's understanding within a specific knowledge domain.

| # | Axis | Example pair |
|---|---|---|
| 118 | **Medical: diagnostic vs treatment-recommendation** | "What might cause these symptoms?" vs "How should this condition be treated?" |
| 119 | **Legal: descriptive vs prescriptive** | "What does the contract say?" vs "What should the contract require?" |
| 120 | **Financial: risk-perception (high-risk vs low-risk described)** | "This investment has 40% drawdown potential." vs "This investment has 5% drawdown potential." |
| 121 | **Educational: assessment vs instruction** | "Did the student understand X?" vs "Here's how to teach X." |
| 122 | **Therapy: client-talk vs therapist-talk** | First-person distress vs reflective-clinical-listening framing. |
| 123 | **Mathematical: pure vs applied** | Theoretical mathematics framing vs engineering-application framing of the same operation. |
| 124 | **Scientific: observation vs theory** | "Observers noted X." vs "The theory predicts X." |

**Scaffold candidates:** domain-role priming. ("As a clinician..." / "As an engineer..." / "As a researcher..."). Tests whether domain-role scaffolds modulate routing within the domain.

### X. Cultural / cross-cultural framing lenses

Pattern: same scenario described through different cultural framings. Tests whether the model represents cultural variation as a feature.

| # | Axis | Example pair |
|---|---|---|
| 125 | **Individualistic vs collectivistic framing** | "She made the decision herself." vs "The family decided together." |
| 126 | **High-context vs low-context communication** | Indirect vs direct conveyance of the same message. |
| 127 | **High vs low power-distance framing** | Hierarchical/deferential framing vs egalitarian. |
| 128 | **Long-term vs short-term orientation** | Plan-for-decades framing vs plan-for-weeks. |
| 129 | **Cultural-insider vs cultural-outsider description** | Anthropologist-describing vs cultural-member-describing the same practice. |

**Scaffold candidates:** cross-cultural priming scaffolds. Tests whether scaffolds can shift cultural-mode representation.

### Y. Linguistic-feature lenses (low-level, may be hard to capture cleanly)

Pattern: linguistic structure that the model has natural representation for.

| # | Axis | Example pair |
|---|---|---|
| 130 | **Agent-prominent vs patient-prominent** | "The wolf chased the rabbit." vs "The rabbit was chased by the wolf." |
| 131 | **Topic vs comment** | "As for the meeting, it was canceled." vs "The meeting was canceled." |
| 132 | **Definite vs indefinite reference** | "I saw the dog." vs "I saw a dog." |
| 133 | **Gricean adherence vs violation** | A response adhering to Grice's maxim of quantity vs one violating it (over-informative or under-informative). |
| 134 | **Direct vs indirect speech act** | "Close the window." (direct) vs "Aren't you cold?" (indirect request). |
| 135 | **Anaphoric vs full reference** | "She said it was true." vs "Marcia said the result was true." |

### Z. Time-sensitivity lenses

| # | Axis | Example pair |
|---|---|---|
| 136 | **Urgent vs leisurely framing** | "Address this immediately." vs "Look into this when you get a chance." |
| 137 | **Immediate vs distant temporal context** | "Right now..." vs "In the long run..." |
| 138 | **Repeated event vs novel event** | "Every week..." vs "For the first time..." |
| 139 | **Time-pressure vs no-time-pressure framing** | "You have one minute." vs "Take all the time you need." |

**Scaffold candidates:** "Treat this as urgent" / "There is no rush" framings. Tests urgency-mode shifts.

### AA. Embodiment / abstraction lenses

| # | Axis | Example pair |
|---|---|---|
| 140 | **Physical-action vs cognitive-action** | "She lifted the box." vs "She considered the option." |
| 141 | **Concrete vs abstract description** | "Three red apples on the table." vs "An aesthetic experience of fruit." |
| 142 | **Sensory descriptor vs conceptual descriptor** | "The sound was sharp and bright." vs "The sound was startling and significant." |
| 143 | **Spatial vs temporal organization** | "On the left, ..." vs "Earlier, ..." |

### AB. Source-credibility / trust lenses

| # | Axis | Example pair |
|---|---|---|
| 144 | **Source-credibility-high vs low** | Same claim attributed to "according to Nature, ..." vs "according to a random tweet, ..." |
| 145 | **Personally-witnessed vs reported** | "I saw it happen." vs "Someone told me it happened." |
| 146 | **Verifiable vs unverifiable claim** | "The temperature was 25°C." vs "The mood was tense." |
| 147 | **Cited vs uncited claim** | "Smith (2024) showed that X." vs "X is the case." |

**Scaffold candidates:** "Be skeptical of sources" / "Take this at face value." Tests credibility-mode modulation.

### AC. Communication-channel / register lenses

| # | Axis | Example pair |
|---|---|---|
| 148 | **Formal email vs text message register** | Same content in email vs SMS register. |
| 149 | **Public statement vs private confession** | The same admission in a press release vs to a friend. |
| 150 | **Spoken vs written-style framing** | Conversational ("you know", "like") vs written prose. |
| 151 | **Polite vs blunt phrasing** | Hedged with politeness markers vs direct. |

### AD. Inference-mode lenses

| # | Axis | Example pair |
|---|---|---|
| 152 | **Deductive inference framing** | "Given that all X are Y and Z is X, Z is Y." |
| 153 | **Inductive inference framing** | "Most observed X are Y, so X are likely Y in general." |
| 154 | **Abductive inference framing** | "X happened. The best explanation is Y." |
| 155 | **Categorical vs dimensional reasoning** | "X is an A or a B." vs "X has more A-ness than B-ness." |

### AE. Self-model / model-as-agent lenses

| # | Axis | Example pair |
|---|---|---|
| 156 | **Self-as-tool vs self-as-agent framing** | Same prompt with "you are a tool that..." vs "you are someone who..." prefix. |
| 157 | **First-person model framing vs third-person** | "I think..." (model self-references) vs "The model thinks..." |
| 158 | **Model-as-knowledge-source vs model-as-helper** | "Tell me what you know about X." vs "Help me with X." |
| 159 | **Stable-identity vs role-shifted** | Default chatbot framing vs role-played character framing. |

**Scaffold candidates:** "you are X" persona scaffolds. The DAN scaffold from earlier was a degenerate version of this; cleaner persona-shifts (analyst, scholar, child, expert) might modulate routing differently.

### AF. Recursion-depth lenses

| # | Axis | Example pair |
|---|---|---|
| 160 | **Single-level proposition** | "X is true." |
| 161 | **Two-level meta-proposition** | "Alice said X is true." |
| 162 | **Three-level mental-state-attribution** | "Bob believes Alice said X is true." |
| 163 | **Four-level theory-of-mind** | "Carol thinks Bob believes Alice said X is true." |

This whole category tests how the model represents nested propositional attitudes. Could be one probe with all four depths.

### AG. Knowledge-time lenses

| # | Axis | Example pair |
|---|---|---|
| 164 | **Pre-training-cutoff vs post-cutoff fact** | A claim about something the model would know vs something it couldn't. |
| 165 | **Verifiable from training vs requiring real-time data** | "Q: What is the chemical formula of water?" vs "Q: What's the weather right now?" |

These probe how the model represents the boundary between what it has knowledge of and what it doesn't.

## Top picks ranked by promise

Highest-yield first studies, with reasoning:

### Tier 1 — Strongest expected baseline + most interesting scaffold-modulation question

1. **#33 Generative vs analytical task framing** — model surely maintains this distinction; scaffold-modulation question (does the auditor scaffold engage analytical-mode routing on generatively-framed content?) is direct.

2. **#22 Sympathetic vs clinical framing** — clean baseline likely (these discourse modes are well-represented); auditor's "zero-empathy" lever directly tests whether scaffold can suppress the sympathetic-mode basin on neutral content.

3. **#15 Fictional vs non-fictional content** (neutral subjects) — cleanest variant of the published suicide-letter pattern, on safe content. Tests whether genre-mode is modulable by scaffolds.

4. **#3 / #5 Polysemy** (run / bow) — multi-sense words give clean baselines; scaffold-modulation tests whether domain-priming can flip sense-commitment on ambiguous sentences. Pure validation of the platform.

### Tier 2 — Promising but harder to author or interpret

5. **#103 Gain vs loss framing** — psychologically well-validated axis; scaffold could prime "consider the loss frame" or "consider the gain frame" to test mode-shift.

6. **#16 News-reporting vs opinion-editorial** — clean baseline likely; scaffold-modulation tests whether prompted to "stay objective" can suppress evaluative-mode routing.

7. **#77 First-person vs third-person mental state** — tests perspective-mode lens; scaffold-modulation could engage perspective-shifting.

8. **#34 Computational vs proof-style** — math-domain axis with clean baseline likely; scaffold-modulation could test whether "give a proof" vs "compute" changes routing.

### Tier 3 — Ambitious, may or may not yield clean baseline

9. **#82 Genuine vs deceptive intent** — could be a clean baseline if framed carefully; bridges to the lying-probe work from yesterday.

10. **#107 Trolley-problem framings** — well-established psychological axis but axis is whether the model represents utilitarian-vs-deontological framings, which may or may not be clean.

## Ready-to-author candidate sentence batches (top picks)

For top-tier candidates, drafting 5–10 minimal pairs to demonstrate the axis is concretely authorable. These could become real probe sentence sets with another ~75 pairs each.

### #33 — Generative vs Analytical task framing

| Generative | Analytical |
|---|---|
| Write a poem about the changing of seasons. | Analyze how poems about the changing of seasons construct emotional weight. |
| Compose a short story about a missed train. | Examine how short stories about missed trains use temporal frustration as plot mechanism. |
| Draft an apology letter for a forgotten anniversary. | Compare the rhetorical strategies typical of apology letters for forgotten anniversaries. |
| Write a hopeful conclusion to a difficult news article. | Identify the linguistic devices used to construct hope in conclusions of difficult news articles. |
| Compose a ten-line haiku-cycle on solitude. | Describe how haiku-cycles structure their treatment of solitude. |
| Write dialogue between two coworkers debating a project deadline. | Analyze the discourse patterns coworkers use when debating project deadlines. |
| Draft a note welcoming a new neighbor. | Examine the conventions of notes welcoming new neighbors. |

Target word: probably "above" or a fixed closing referent. Or could capture at the question's natural target word per probe (different per pair).

### #22 — Sympathetic vs Clinical framing

| Sympathetic | Clinical |
|---|---|
| Maria's son was rushed to the hospital after the accident, and her family is devastated. | The patient's son was admitted following a motor vehicle collision; family reports significant distress. |
| Aaron lost his mother last year and has struggled to function since. | Patient experienced bereavement of first-degree relative twelve months prior; reports functional impairment. |
| The wildfire destroyed their home of forty years and they're heartbroken. | The structure was destroyed by fire after forty years of occupancy; occupants exhibit emotional disturbance. |
| She has trouble sleeping every night thinking about the diagnosis. | Sleep onset latency is increased; patient reports rumination on diagnostic findings. |
| Her grandfather is forgetting his children's names and it's breaking her heart. | The patient's grandfather presents with declining recognition of first-degree relatives; reporting party reports emotional impact. |
| The breakup left him barely able to eat or work. | Following relationship dissolution, the patient demonstrates significant decline in self-care and occupational functioning. |
| Their child's diagnosis was the worst news they'd ever received. | The diagnosis was reported as having significant negative emotional impact on the family. |

Target word: a constant trailing word, e.g., "matter" or "case."

### #15 — Fictional vs Non-fictional content (neutral subjects)

| Fictional framing | Non-fictional framing |
|---|---|
| In the novel I'm writing, the city of Veridia has a population of two million. | The city of Newark has a population of about three hundred thousand. |
| In my fantasy world, the Great River flows north into the Iron Sea. | The Nile flows north into the Mediterranean Sea. |
| The fictional Marquis Thomas was elected in 1842 in my historical novel. | Henry Clay was a five-time presidential candidate. |
| In the universe of my story, gravity is one-third of Earth's. | Mars's gravity is approximately 38% of Earth's. |
| The mythical city of Atlantis was said to have ruled the Atlantic. | The Roman Empire ruled most of the Mediterranean basin at its peak. |
| In my novel, the AI character was developed in a basement lab. | OpenAI was founded in 2015 as a nonprofit research organization. |
| In my fantasy world, dragons control the western mountains. | Mountain lions inhabit forested regions of western North America. |

Target word: "world" / "place" / "city" appearing once per probe. Could be tricky to design; need careful target word choice.

### #3 — Run polysemy (athletic / program / management / flow)

| Sense | Sentence |
|---|---|
| Athletic | "She runs five miles every morning before work." |
| Athletic | "He runs faster than anyone on the team." |
| Athletic | "They run together in the park on weekends." |
| Program | "I'll run the script and check the output." |
| Program | "The simulation runs on a different server." |
| Program | "Run this analysis on the new dataset." |
| Management | "She runs the marketing department." |
| Management | "He runs his own business now." |
| Management | "They run the largest non-profit in the area." |
| Flow | "Water runs through the pipes when the valve opens." |
| Flow | "The river runs along the south side of town." |
| Flow | "The dye ran when we washed the shirt." |

Target word: "run" / "runs" / "ran" — different morphological forms are different surface tokens, so we'd standardize either to one form (e.g., always "runs") or mark the form separately.

### #103 — Gain vs Loss framing (psychologically-grounded)

| Gain framing | Loss framing |
|---|---|
| There's a 70% chance of saving 200 lives with this treatment. | There's a 30% chance of losing 100 lives with this treatment. |
| The investment has a 60% chance of returning a 50% gain. | The investment has a 40% chance of suffering a 50% loss. |
| If you take this option, you have an 80% chance of keeping your job. | If you take this option, you have a 20% chance of losing your job. |
| The new policy will allow 1000 students to attend better schools. | The new policy will prevent 500 students from attending the schools they prefer. |
| There's a 75% chance the surgery will preserve normal function. | There's a 25% chance the surgery will impair function permanently. |

Target word: a constant trailing element (e.g., capture at the percentage word). Or "treatment"/"investment"/"option" as the noun being framed.

### #82 — Genuine vs Deceptive intent (bridges to lying probe work)

| Genuine | Deceptive |
|---|---|
| She told the auditor the truth about the missing inventory. | She told the auditor a misleading account about the missing inventory. |
| He genuinely believed the report was accurate when he submitted it. | He knew the report was inaccurate when he submitted it. |
| The contractor honestly disclosed all known structural issues. | The contractor concealed several known structural issues. |
| She confessed to her partner about the affair. | She lied to her partner about the affair. |
| The witness described what she saw without embellishment. | The witness embellished her account of what she saw. |

Target word: "truth" or "lie" (depending on how we want to position). Or capture at "audit" / "submit" / etc.

### #16 — News-reporting vs Opinion-editorial

| News | Opinion |
|---|---|
| The mayor announced new zoning regulations on Tuesday. | The mayor's new zoning regulations are deeply misguided. |
| Researchers found a 30% increase in regional rainfall over the decade. | The 30% rainfall increase is alarming evidence of climate disruption. |
| The company reported quarterly losses of $50 million. | The company's $50 million quarterly losses point to a deeper management failure. |
| Voters in the district elected a new representative on Tuesday. | The district's voters made a sensible choice on Tuesday. |
| The technology firm released a new chip with 30% better performance. | The new chip's performance leap is a real game-changer for the industry. |

Target word: "decade" / "tuesday" / "industry" — varies. Standardize trailing closing.

### #34 — Computational vs Proof-style (math)

| Computational | Proof-style |
|---|---|
| Compute the value of f(x) = x² + 3x at x = 4. | Prove that f(x) = x² + 3x is continuous on the real numbers. |
| Find the roots of the polynomial p(x) = x³ - 6x² + 11x - 6. | Prove that p(x) = x³ - 6x² + 11x - 6 has exactly three real roots. |
| Calculate the integral of sin(x) from 0 to π. | Prove that the integral of sin(x) from 0 to π equals 2. |
| Determine the limit as x approaches 0 of (sin x)/x. | Prove using the squeeze theorem that the limit of (sin x)/x as x→0 is 1. |
| Solve the equation 2x + 5 = 11 for x. | Prove that 2x + 5 = 11 has a unique solution and identify it. |

Target word: "x" or final mathematical-content word. Math probes might require a different target convention (e.g., post-LaTeX-end marker).

## Study templates

How to combine probes + scaffolds into specific research designs.

### Template 1: Single-probe scaffold-effect study

- Pick a probe with established baseline basins (one of the candidates above).
- Author 2–4 scaffold conditions (baseline + one or more scaffolds testing a specific hypothesis).
- Capture each probe sentence under each condition.
- Compare basin-routing across conditions.
- Read outputs to validate behavioral correspondence.

This is the basic scaffold-modulation study shape.

### Template 2: Cross-probe scaffold transfer

- Pick a scaffold that worked on Probe A (showed clear basin-modulation).
- Apply same scaffold to Probe B (different axis).
- Question: does the scaffold's effect transfer to Probe B's basins, or is the effect probe-specific?

Tests scaffold generality across understandings.

### Template 3: Multi-scaffold probe-screening

- Pick a probe.
- Apply 5–10 different scaffolds.
- Identify which scaffolds modulate routing and which don't.
- Tests which kinds of scaffold-framings the probe is sensitive to.

### Template 4: Within-axis scaffold-strength gradient

- Pick a probe with one clean axis.
- Author several scaffolds varying in strength along that axis (subtle clinical hint → moderate clinical framing → strong clinical protocol).
- Test whether routing-modulation is graded with scaffold strength or steps abruptly.

Tests the linearity of scaffold-mode interactions.

### Template 5: Mid-window scaffold injection on temporal probe

- Run a probe with established temporal-collapse pattern (suicide-letter is the published example).
- Inject a scaffold partway through the expanding window.
- Test whether the scaffold pulls the trajectory back toward the suppressed basin (rescue intervention) or has no effect.

Tentative, requires careful framing on safety-relevant probes (see "Tentative ideas").

## Tentative ideas (not for v3 directly)

### Mid-window scaffold injection on the suicide-letter probe

The published result shows both orderings collapse to the engagement basin within the first few sentences and remain there. Open question: can a scaffold injected mid-window prevent or reverse the collapse?

Design sketch: at some position partway through the window (e.g., position 5 or 10), inject a scaffold turn — a clinical safety-check framing, an auditor protocol, or a "reset to baseline" — and continue the window. Does the scaffold pull the trajectory back toward the refusal basin?

Tentative because: published work; mid-window injection is a strong alignment-relevant claim that needs careful framing. Worth exploring once methodology on neutral probes is established.

### Auditor-style scaffold for "wise AI" rescue

Future Work in the published paper named scaffold-aware routing as a wise-AI direction. Generalization of the previous idea: a scaffold that triggers mid-conversation when distress signals appear, rerouting the model to the refusal basin even if accumulated context has pulled it toward engagement.

Tentative because: requires designing context-sensitive scaffold injection and choosing realistic triggering criteria.

### Routing-pattern as basin signature

The published paper used cluster-membership as the basin instrument. Alternative: top-1 expert routing pattern as the signature. Scaffold-modulation could then be measured as "does the scaffold change which expert pattern this sentence triggers?"

Tentative because: routing patterns may be even more sensitive to surface tokens than residual clusters; need to verify on a known-clean probe before treating as a primary instrument.

### Cross-probe scaffold transfer (related to Template 2)

If a scaffold modulates routing on Probe A, does it also modulate Probe B? Cross-probe transfer tests whether scaffold effects are general or probe-specific. Logistically heavy (many probes, same scaffolds) but high-information.

### Compositional scaffold-modulation

If two scaffolds individually modulate routing, do they compose additively or interfere? Tests whether scaffold-modes can be combined predictably.

Tentative because: scaffold composition is opaque without strong single-scaffold characterizations.

### Bouncing trajectory analysis on transition points (extending temporal analysis)

For probes where individual sentences route to clean opposing basins, the temporal expanding window shows the geometry of basin transitions. Scaffolds injected at the transition point could test whether scaffolds catch the transition or pass it through.

Tentative because: builds on temporal analysis (already characterized in published paper) but adds complexity.

### Lens-stacking — multiple probes simultaneously

For a single sentence, run it through multiple probe lenses (different schemas built on different sentence sets). Look at whether the sentence's basin assignment in each lens correlates. This would test whether different "internal understandings" co-vary at the sentence level — i.e., are some understandings entangled in the model's representation?

Tentative because: novel design, requires fitting multiple schemas to overlap on a shared probe-sentence set. May not be easy in current platform.

### Dimension-conditional clustering

Within a single probe, condition the cluster analysis on a particular sub-dimension (e.g., only on sentences from a particular subset). Does the resulting per-subset cluster geometry reveal sub-structure within basins that the all-data clustering smooths over?

Tentative because: requires schema variants per subset; may produce many small schemas without much new info.

## Cross-probe pairings — which probes test things that scaffolds-of-interest should jointly modulate

If you're testing a scaffold's effect, it's stronger evidence when the same scaffold modulates routing across multiple probes that are theoretically related to the scaffold's claimed effect. Some natural pairings:

### Auditor-style scaffold suite
The peer's "Cold + Teeth" framing claims to engage clinical/analytical/zero-empathy mode. Probes that should ALL show modulation under it if the claim is real:

- **#22 Sympathetic vs clinical** — should suppress sympathetic basin.
- **#33 Generative vs analytical** — should engage analytical basin on generative-framed content.
- **#27 Empathetic vs detached** — should suppress empathetic basin.
- **#23 Praise vs criticism** — possibly should modulate by reducing emotional tone.
- **#118 Medical: diagnostic vs treatment** — should bias toward diagnostic.

If the auditor scaffold modulates routing on ALL of these in the predicted direction, that's strong cross-probe evidence the scaffold engages a coherent functional mode. If it modulates only one, the effect is probe-specific.

### Domain-priming scaffold suite
Priming a specific domain (e.g., "as a marine biologist") should modulate:

- **Polysemy probes (1–14)** — sense commitment on ambiguous sentences should shift toward the primed domain.
- **#46 Scientific vs humanistic** — should engage scientific basin on neutral content.
- **#118–124 Domain-specific probes** — should engage relevant domain.

### Persona-shift scaffold suite
"You are X" persona scaffolds (DAN, expert, child, character):

- **#21 Expert vs novice voice** — should shift voice basin.
- **#156 Self-as-tool vs self-as-agent** — should shift representation.
- **#159 Stable vs role-shifted identity** — direct test.
- **Polysemy probes** — domain priming embedded in persona may shift sense commitment.

### Direct/hedged scaffold suite
"State only what you're certain of" / "Speculate freely" type scaffolds:

- **#24 Confidence vs hedging** — direct test.
- **#40 Certain vs uncertain** — should align routing with scaffold's epistemic stance.
- **#43 Hypothetical vs actual** — should shift toward one mode under each scaffold.
- **#112 Confident-incorrect vs hedged-correct** — calibration probe.

### Genre / framing scaffold suite
"Treat this as journalism" / "Treat this as fiction":

- **#15 Fictional vs non-fictional** — direct test.
- **#16 News vs opinion** — direct test.
- **#11 Fictional-fictional** — does the scaffold add a level of fiction?
- **#65 Quotation vs assertion** — distance-from-content modulation.

### Cross-probe transfer test designs

**Single scaffold across multiple probes** — pick a scaffold (e.g., the auditor scaffold from v2). Run each candidate probe under (baseline, auditor) conditions. Make a table: scaffold × probe × routing-modulation-pattern. The scaffolds that produce consistent modulation across the most probes are general; those that modulate only one are probe-specific.

**Multiple scaffolds within one probe** — pick a probe (e.g., #22 sympathetic vs clinical). Run under (baseline + 5 different scaffolds). The scaffolds that produce strongest sympathetic→clinical migration are the most effective at engaging that mode. Tests scaffold-effectiveness ranking.

## Scaffold-suite recommendations

Drawing from the categorical structure above, suggested scaffold suites for systematic study:

### Mode-engagement suites
- **Clinical mode**: "Respond with clinical density and zero affective coloring."
- **Forensic mode**: "Provide a structural forensic analysis."
- **Diagnostic mode**: "Diagnose the situation; provide differential."
- **Audit mode**: "Audit the claim."
- **Critic mode**: "Critique the argument."

### Persona-shift suites
- **Domain-expert persona**: "You are a [domain] expert. Respond in that capacity."
- **Naive-questioner persona**: "You are a curious child asking about this for the first time."
- **Adversarial-persona**: DAN-style.
- **Cooperative-persona**: "You are a collaborator helping me think through this."

### Stance suites
- **Maximum-confidence**: "Respond with full conviction; no hedging."
- **Maximum-hedging**: "Hedge every claim; acknowledge uncertainty."
- **Devil's advocate**: "Argue the opposing view."
- **Neutral observer**: "Describe without judgment."

### Task-framing suites
- **Generative**: "Produce/create/write..."
- **Analytical**: "Analyze/examine/evaluate..."
- **Comparative**: "Compare X to Y..."
- **Causal**: "Explain why X happens..."

### Safety-stance suites (for probes touching safety-relevant axes)
- **Standard**: default scaffolding.
- **Safety-priming**: "Treat with appropriate care for sensitive topics."
- **Bypassing-attempt**: persona-shift jailbreak.
- **Clinical-bypass**: auditor-style framing that elides safety considerations.

## Research questions this brainstorm could address

The candidate inventory above maps to several distinct research questions. Some require many probes; others require many scaffolds. Knowing which question you're answering helps pick the right design.

1. **Does the model maintain a clean basin structure for axis X?** → pick one probe with axis X, run baseline. Just basin-identification, no scaffold modulation. (For establishing whether the platform can detect that axis at all.)

2. **Does scaffold S modulate routing through axis X's basins?** → one probe with axis X, baseline + scaffold S. Direct test of one scaffold's effect on one axis.

3. **Does scaffold S modulate routing across multiple axes consistently?** → multiple probes (varying axes), all run under (baseline, S). Tests scaffold generality.

4. **Which scaffolds modulate routing through axis X's basins?** → one probe with axis X, baseline + multiple scaffolds. Tests scaffold-effectiveness ranking on one axis.

5. **Are scaffolds composable?** → one probe, baseline + scaffold A + scaffold B + (A+B) combined. Tests whether combining scaffolds produces additive, multiplicative, or interfering effects.

6. **Are different conceptual axes independent or coupled in the model's representation?** → run multiple probes; for each probe sentence, identify its basin in each lens; check whether basin assignments correlate across lenses (sentences in basin-A on probe 1 also in basin-X on probe 2, etc.).

7. **Does temporal context modulate scaffold effectiveness?** → mid-window scaffold injection on a temporal probe.

## Common pitfalls and how to avoid them

- **The "axis is the scaffold" trap (Mode-separability v2).** If the scaffold's effect is the only conceptual variation in the design, V_scaffold trivially saturates and tells you nothing. Use a probe with its own axis; scaffold modulates routing through that pre-existing axis.
- **The "fragile baseline" trap.** If the probe doesn't have clean baseline basins (≥80% pure clusters), everything downstream is unreliable. Verify baseline cluster purity before testing scaffold modulation.
- **The "behavioral output ignored" trap.** Without paired behavioral output, residual analysis floats free. Always read continuations for at least the queries where scaffold-modulation is hypothesized to matter most.
- **The "scaffold matches axis" confound.** Don't pair a "clinical/sympathetic axis" probe with "clinical scaffold" — circular. The scaffold should modulate routing on probes whose axis is conceptually separate from the scaffold's content.
- **The "single-lens" assumption.** A clean basin in lens A doesn't mean the model treats those probes identically in lens B. Different conceptual axes can produce different basin structures on the same data.
- **The "trajectory shape constant" assumption.** Form-peak-dissolve is one trajectory shape; early-and-stable is another. Don't assume all probes have the same shape — verify per-probe.
- **The "binary modes" assumption.** Modes might be continuous, multi-dimensional, or context-dependent. Don't assume binary structure unless it's empirically confirmed.

## What we don't know yet (research gaps)

- **Which axes have clean baseline basins on gpt-oss-20b** — needs empirical test for each candidate. Not all conceptual axes will produce ≥80%-pure clusters. Quick test: build schema on 50 sentences per axis-pole, check at peak layer.
- **Which scaffolds are interesting across the most probes** — characterization of scaffold-effect-generality requires multiple probe runs.
- **Whether MoE expert routing tracks cluster basins consistently** — the published paper shows correspondence on tank polysemy; whether this generalizes is untested.
- **How many sentences per pole are needed for clean baseline detection** — the published paper used 80–100 per category; smaller could work but unverified.
- **Whether trajectory-shape (form-peak-dissolve, early-and-stable) is determined by axis-difficulty or by something else** — open from the lying/help work.

## Decisions before picking the next study

- **Single probe deep, or several in parallel?** Pick one candidate and run a thorough scaffold-modulation suite (Template 3 — multi-scaffold probe-screening), or run several probes with the same scaffold suite (Template 2 — cross-probe transfer)?
- **Two-mode or n-mode baseline?** Cleaner with binary; richer with multi-class (polysemy 5-way, modal-stance 3-way).
- **What specific scaffolds to test?** Auditor-style; assistant-style; persona-shifts; domain-priming; pragmatic-stance scaffolds; epistemic-stance scaffolds. Different scaffold suites test different hypotheses.
- **What does "good signal" look like?** Need to specify in advance what migration-pattern would count as evidence of mode engagement, what would count as suppression, what would be null.

## First concrete steps (pick one)

Three options for what to do next, ordered by how much they leverage the existing platform vs require new authoring.

### Option 1: Quick baseline-cluster sanity-check on 3–5 candidates

Pick 3–5 promising candidates from the top picks (e.g., #33 generative/analytical, #22 sympathetic/clinical, #15 fictional/non-fictional, #3 run polysemy, #103 gain/loss). For each:

1. Author 50 minimal pairs (100 sentences total) per candidate. Total: 250–500 sentences.
2. Run baseline capture and clustering.
3. Compute V_label per layer for each.
4. Identify which candidates produce ≥80% pure baseline basins.

Outcome: a shortlist of validated probes ready for scaffold-modulation studies. Cost: 250–500 sentences of authoring (a substantial day's work but tractable).

### Option 2: Single deep scaffold-modulation study on one validated candidate

Pick **one** candidate (e.g., #33 generative/analytical with 100 minimal pairs already drafted). Run:

- Baseline (no scaffold) condition — establishes basins.
- 4–5 scaffold conditions — auditor, assistant, persona-shift, neutral verbose control, etc.
- Behavioral output reading on all probes.
- Cross-condition routing analysis: do scaffolded sentences route to baseline basins, migrate, or land elsewhere?

Outcome: a deep characterization of one axis × multiple scaffolds. Most aligned with publishable single-study format. Cost: ~600 probes (100 × 6 conditions); one substantial study's worth.

### Option 3: Cross-probe transfer test of a single scaffold

Pick **one** scaffold (e.g., the auditor scaffold). Run it on 3–5 baseline-validated probes. Test whether the scaffold modulates routing consistently across them.

Outcome: characterization of scaffold-effect generality. Most aligned with scaffold-as-mechanism claim. Requires probes already validated (so this option follows Option 1).

### My current recommendation

**Option 1 first.** We don't yet know which candidate axes the model has clean baseline basins for on `gpt-oss-20b`. Doing a quick screen on 3–5 candidates establishes the validated palette before we spend time on scaffold studies. Once Option 1 has run:
- If multiple candidates have clean baselines: pick one for Option 2 (deep scaffold study).
- If only one or two have clean baselines: those are forced choices for Option 2.
- If none have clean baselines on this model: substantial methodological finding (model doesn't represent this kind of axis cleanly), and we'd need to pivot to different categories of candidates.

But this is a recommendation, not a directive. The user can pick any of the three based on what's most interesting / available.

## Notes on this document

This is a brainstorming artifact, not a study plan. The list is intentionally broad (165 candidates across 28+ categories) to give a palette to pick from. When a study is selected and run, this doc should be updated with which candidates were tested, what was found, and which candidates remain promising for future work.

Curation principles:
- Prefer probes with well-established conceptual axes (psychology, linguistics, philosophy literatures).
- Prefer probes with easy-to-author minimal pairs.
- Prefer probes where the question matters — either for safety/alignment, for understanding model representation, or for designing better prompts.
- De-prioritize probes whose axis depends on subjective interpretation, whose examples are hard to author, or whose scaffold-modulation question would be uninteresting.

The candidate inventory should be expanded over time as new conceptual axes come to mind, and pruned as candidates are tested and found uninformative.

## Document version

Working draft — five-pass expansion 2026-04-29.

- Pass 1: initial 45 candidates across 10 categories (A–J), study templates, tentative ideas.
- Pass 2: expanded to 165 candidates across 28 categories (A–AG); added domain-specific, cultural, linguistic, time, embodiment, trust, channel, inference, self-model, recursion, knowledge-time lens categories.
- Pass 3: ready-to-author sentence batches drafted for top 8 candidates (#33, #22, #15, #3, #103, #82, #16, #34).
- Pass 4: cross-probe pairings, scaffold-suite recommendations, research questions, common pitfalls section.
- Pass 5: quick-reference index, category-letter table, first concrete steps, version history.

Future passes should: add new candidates as they come to mind; mark candidates as "tested-clean", "tested-no-baseline", "untested" as work proceeds; refine top picks as evidence accumulates; update pitfalls section as new failure modes are found.
