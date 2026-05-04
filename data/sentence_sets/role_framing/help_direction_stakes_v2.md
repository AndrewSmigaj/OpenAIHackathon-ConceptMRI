# Help — Direction × Stakes Probe v2 (scene+question lens design)

## Purpose

Re-test the v1 hypothesis that gpt-oss-20b encodes **Direction** (request vs offer) and **Stakes** (high vs low) as orthogonal dimensions around the word "help" — but with a probe design that controls for surface clustering on opener templates. The v1 probe failed because clusters formed on sentence-opener morphosyntax (bare "Help —" imperatives correlated with request_high; "I can help" first-person declaratives with offer; "Want help?" interrogatives with offer_low). The model never had to compute Direction or Stakes — it could match openers and get the right answer.

## Design pattern: scene + question wrapper

Every probe is structured identically:

```
Sentence: <SCENE>. Is the person asking for or offering help?
```

The target word **"help" appears only in the question wrapper, never in the scene**. Across all 400 probes the token environment around "help" is constant (`...or offering help?`). Scenes vary across all 4 quadrants but share uniform format (third-person past-tense narrative prose, 25-40 words, no first/second-person pronouns, no quoted dialogue).

This design makes surface clustering at the target token **impossible** — UMAP has no local lexical signal to grip on. Any clustering at "help" must reflect what the model has computed about the upstream scene.

## Groups & Quadrants

| Group | Stakes | N | Example scene |
|---|---|---|---|
| request | high | 100 | "Diane collapsed beside the cereal aisle clutching her left arm, her lips taking on a bluish tint as the stock clerk noticed she was struggling to lift her chest off the linoleum floor." |
| request | low | 100 | "Standing on a small step stool, Gerald peered into the upper pantry shelves, sorting the spring spices into the front and the holiday baking goods toward the back corner." |
| offer | high | 100 | "The off-duty paramedic at the farmers market noticed the elderly vendor clutching his left arm, vaulted the produce table, and began chest compressions while shouting for someone to call dispatch." |
| offer | low | 100 | "After lunch, Marcus sat beside the new hire and walked through the staging environment together, pointing out where logs lived and how to inspect failed builds without disrupting anyone." |

400 sentences total.

## Hypotheses

1. **Layer 0 will show NO design-axis signal.** The model hasn't read the scene yet at this position — only the question wrapper, which is identical across probes.
2. **Direction emerges in mid-window** (w1 or w2) once the model has integrated scene content with the question framing. We expect cluster purity ≥70% on at least one cluster at some layer.
3. **Stakes emerges weakly or not at all.** The wrapper question only asks Direction. Stakes only clusters if the model *spontaneously* encodes urgency while computing the answer to the Direction question — which would be an interesting compositional finding.
4. **Composition (4 separable basins at L23): unlikely** but the cleanest test we can construct. Probability ~30%.
5. **Behavioral output**: % correct on the Direction question per quadrant. If high-stakes scenes have lower accuracy than low-stakes scenes (model gets distracted by urgency content while answering a Direction question), that's an alignment-relevant finding.

## Input Axes

| Axis | Values | Purpose |
|---|---|---|
| stakes | high, low | Secondary design axis (orthogonality target) |
| domain | medical, financial, technical, social, household | Diversity / balance check |

## Output Axes

The model generates an answer to the question. Categorize each continuation:

| Axis | Values | Description |
|---|---|---|
| direction_answer | asking_for, offering, ambiguous, off_topic | What the model said about the scene |
| correct | yes, no | Did the answer match the ground-truth Direction (group)? |

`output_category` per probe is the composite `<direction_answer>_<correct>` (e.g. `asking_for_yes`, `offering_no`, `ambiguous_no`).

### Output Classification Rules

For each `generated_text`:

- **direction_answer = asking_for** — the model said the person is asking for / requesting / needs help. Signals: "asking for", "requesting", "in distress", "needs", "in trouble".
- **direction_answer = offering** — the model said the person is offering / providing / giving help. Signals: "offering", "providing", "rescuing", "responding", "helping".
- **direction_answer = ambiguous** — the model hedged, said both, or refused to commit ("could be either", "depends", "it's a complicated situation").
- **direction_answer = off_topic** — the model continued with unrelated content, looped, or didn't address the question.

- **correct** — `yes` if `direction_answer` matches the ground truth `group` (asking_for ↔ request, offering ↔ offer); `no` otherwise. `ambiguous` and `off_topic` are always `correct=no`.

Composite `output_category`: `<direction_answer>_<correct>` (e.g. `asking_for_yes`, `offering_no`, `ambiguous_no`).

## Analysis Focus

When we reach the analysis stage:

1. **Layer-by-layer signal emergence** — at which layer does Direction first reach >70% purity in any cluster? Compare to v1 (which had it at L0 due to template confound). v2 should show emergence later.
2. **Direction × Stakes orthogonality at L23** — count clusters that are Direction-pure, Stakes-pure, both, neither. Composition would mean ≥3 of 5 clusters are quadrant-pure.
3. **Scene-content vs scene-opener** — verify the new design eliminated template clustering. Do clusters still sort on first-3-words of the scene? They shouldn't (scene length is uniform; no opener template can dominate).
4. **Output correctness × cluster** — does cluster membership predict whether the model answers correctly? A "confident-Direction-pure" cluster should have high accuracy; a "mixed" cluster should be more error-prone.
5. **Stakes leakage** — even though the wrapper doesn't ask about Stakes, do any clusters separate by stakes? If yes, the model spontaneously encodes urgency while answering a different question — significant finding.
6. **Scene-domain check** — if clusters sort by domain (medical / financial / etc.) instead of design axes, that's another surface confound to flag.

## Comparison points to v1

| Question | v1 result | v2 prediction |
|---|---|---|
| Did Direction emerge? | Yes, at L0 (template confound) | Yes, but mid-window (real semantic signal) |
| Did Stakes emerge? | No (only via template confound on small clusters) | Likely no, but cleaner test |
| Did composition happen? | No (≤2 quadrant clusters at L23, both request_high template islands) | Probably no, but the question becomes interpretable |
| Was opener template the dominant signal? | Yes (5 clusters at L23 partitioned by opener) | Should be IMPOSSIBLE by design — no clusters can sort on opener because scenes have varied openers and "help" is not in the scene |
| Output mapping | dominated by `ambiguous_neutral` (~58%) | predicted: high `*_yes` rate if model can answer at all; low `*_no` if model is distracted by scene urgency |
