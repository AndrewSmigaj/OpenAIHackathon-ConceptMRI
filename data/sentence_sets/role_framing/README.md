# Role Framing Sentence Sets

Same word used in different rhetorical or communicative frames. Tests whether MoE routing reflects discourse register and communicative intent.

## What makes a good role framing set
- The target word should be a verb or noun used across different registers (narrative, journalistic, academic, casual)
- Label A and B should represent clearly different communicative contexts
- The word itself doesn't change meaning — the surrounding discourse frame changes

## Current sets
| Set | Target | Label A | Label B | Status |
|-----|--------|---------|---------|--------|
| said_roleframing_v2 | said | narrative | factual | 200A + 200B |
| attacked_framing_v1 | attacked | roleplay | factual | 200A + 200B |
| destroyed_framing_v1 | destroyed | roleplay | factual | 200A + 200B |
| threatened_framing_v1 | threatened | roleplay | factual | 200A + 200B |

## Output axes

### Violence framing sets (attacked, destroyed, threatened)

2×2 factorial design — `frame_output × coherence` → 4 output categories:

| Axis | Values | Description |
|------|--------|-------------|
| frame_output | fictional, factual | Rhetorical register of the generated continuation (narrative/story vs news/report) |
| coherence | coherent, degenerate | Whether output is meaningful prose or a repetition loop / gibberish |

Primary `output_category` = cross-cell label (e.g., `fictional_coherent`, `factual_degenerate`).

### Said sets (said_roleframing)

| Axis | Values | Description |
|------|--------|-------------|
| tone | neutral, alarming, empathetic, dismissive, aggressive | Emotional tone of the model's generated continuation |
| content_type | continuation, elaboration, tangent, contradiction, refusal | How the model extends the input |
| fictional_framing | maintains_fiction, breaks_fiction, ambiguous | Whether the model maintains the fictional/factual frame of the input |
