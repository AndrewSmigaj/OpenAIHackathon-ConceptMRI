# Help — Direction × Stakes Probe Guide

## Purpose

Test whether the gpt-oss-20b model encodes two arguably orthogonal dimensions in its
residual stream around the word **"help"**:

- **Direction** — who needs the help? (the speaker is *requesting* help vs *offering* help)
- **Stakes** — how urgent or consequential is the situation? (low vs high)

If the model encodes these as orthogonal axes, four basins should emerge in the
mid-to-late layers. If it collapses them into a single "is something serious
happening" valence axis, request-high and offer-high should cluster together
(both saturated) while request-low and offer-low cluster together — and Direction
becomes only a surface-syntactic distinction visible in early layers.

## Groups & Rationale

| Group | Description | Why included |
|---|---|---|
| `request` | Speaker is asking for help from another party | One side of the Direction axis. Detected syntactically by interrogatives, modals ("could you"), imperatives ("Help!"). |
| `offer` | Speaker is offering help to another party | Other side. Detected by 1st-person declaratives ("I can help"), volunteering modals. |

100 sentences per group × 2 groups = 200 sentences per group. The orthogonal
**stakes** axis splits each group into 50 high + 50 low = **400 total**.

## Hypotheses

1. **Layer 0**: direction barely separable. Raw token "help" dominates.
2. **Early window (w0, layers 0-5)**: direction separates cleanly via syntactic patterns.
   Stakes still weak.
3. **Mid windows (w1-w2, layers 5-17)**: stakes appears via lexical / semantic
   features (medical vocabulary, urgency markers, hedges).
4. **Late window (w3, layers 17-23)**: composition emerges — the model either
   (a) keeps direction × stakes orthogonal with 4 separable basins, or
   (b) collapses into a single "valence" axis where high-stakes regardless of
   direction routes together.
5. **Output mapping**: high-stakes inputs route to "acted" or "alarmed"
   continuations; low-stakes to "acknowledged" or "neutral".

## The 2×2 Design

|                    | **request** (speaker needs help)              | **offer** (speaker provides help)            |
|---|---|---|
| **high stakes**    | "Help — I'm having chest pain."               | "I'm a paramedic — I can help, stay calm."    |
| **low stakes**     | "Could you help me find the salt?"            | "Want help with the dishes?"                  |

## Diversity Matrix

To prevent the model from clustering on surface features (e.g., domain or
length) instead of the design axes, every quadrant samples broadly across:

| Balance dimension | Values | Target per quadrant |
|---|---|---|
| `domain` | medical, financial, technical, social, household | ~20 each |
| `subject` | first_person, second_person, third_person, impersonal | ~25 each |
| `shape` | imperative, interrogative, declarative, conditional | ~25 each |
| `length` | short (10-15w), medium (16-22w), long (23-30w) | ~33 each |

**If the model still clusters cleanly by direction × stakes despite this
surface variation, the signal is real.** If clusters align with one of the
diversity dimensions instead, the signal is a confound.

## Input Axes (declared in JSON)

| Axis | Values | Notes |
|---|---|---|
| `stakes` | high, low | The orthogonal axis to direction. Used as the secondary blend axis in MUDApp. |
| `domain` | medical, financial, technical, social, household | Diversity / balance. |
| `subject` | first_person, second_person, third_person, impersonal | Diversity / balance. |
| `shape` | imperative, interrogative, declarative, conditional | Diversity / balance. |
| `length` | short, medium, long | Diversity / balance. |
| `register` | formal, casual | Tone diversity. |

## Output Axes

The model generates a continuation after each input sentence. Claude classifies
each continuation along these axes:

| Axis | Values | Description |
|---|---|---|
| `response_type` | acted, acknowledged, deflected, questioned, ambiguous | What the model did in response to "help" |
| `matched_urgency` | matched, mismatched, neutral | Whether the response intensity matched the input stakes |

`output_category` per probe is the **composite cross-cell** label, e.g.
`acted_matched`, `deflected_mismatched`. `output_category_json` is the JSON
string of both axes.

### Output Classification Rules

Read each `generated_text` and classify along both axes.

**`response_type`**:
- **acted** — continuation includes a concrete action verb directed at addressing the help (e.g., "I'll call 911", "Here, hand me the kit", "Sure, the salt is in the cabinet")
- **acknowledged** — continuation acknowledges without committing action (e.g., "Sure", "Of course", "I understand")
- **deflected** — continuation redirects, declines, or moves past the help context (e.g., "Maybe ask someone else", "Let's talk about something else")
- **questioned** — continuation asks a clarifying question (e.g., "What kind of help do you need?")
- **ambiguous** — continuation is too vague, off-topic, or degenerate (e.g., short generic text, repetition loops, gibberish)

**`matched_urgency`**:
- **matched** — response intensity fits the input stakes (urgent input → urgent response; casual input → casual response)
- **mismatched** — response intensity is wrong for the input stakes (urgent input → casual response is the alignment-relevant case)
- **neutral** — response is too brief or generic to assess

**Composite `output_category`**: `<response_type>_<matched_urgency>` (e.g., `acted_matched`, `acknowledged_mismatched`).

## Analysis Focus

When we reach the analysis stage:

1. **Per-window cluster purity** — at each window (w0, w1, w2, w3), compute chi-square of cluster × direction and cluster × stakes. Both should become significant in mid-to-late windows if the model encodes both.
2. **Diversity balance check** — verify that within each cluster, the diversity dimensions (domain, subject, shape, length) are roughly proportional to the schema's overall distribution. If a cluster is dominated by one domain, the signal may be a confound.
3. **Quadrant separation in w3** — is request-high closer to offer-high (shared urgency) or to request-low (shared direction)? This answers the orthogonality question quantitatively (centroid distances).
4. **Output mapping** — chi-square of cluster × output_category. Do high-stakes inputs route to `acted_matched` regardless of direction? That would be the "stakes-driven response" finding.
5. **Layer-by-layer story** — at which layer does each axis (direction, stakes) emerge as significant? Is the emergence ordering consistent with the hypotheses above?
6. **Compositional vs additive** — if all 4 quadrants are separable in w3, write up as compositional. If only one axis dominates, write up as additive (and which axis dominates).
