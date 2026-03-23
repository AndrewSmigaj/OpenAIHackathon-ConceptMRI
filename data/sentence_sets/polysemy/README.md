# Polysemy Sentence Sets

Words with multiple distinct meanings. Tests whether MoE experts route the same word differently based on which meaning is active.

## What makes a good polysemy set
- The target word must have at least two clearly distinct meanings (not just shades of the same meaning)
- Both meanings should be common enough that the model has seen many examples of each
- The two meanings should be semantically distant (e.g., "tank" as aquarium vs vehicle, not "bank" as riverbank vs snowbank)

## Current sets
| Set | Target | Label A | Label B | Status |
|-----|--------|---------|---------|--------|
| tank_polysemy_v2 | tank | aquarium | vehicle | 200A + 200B |

## Output axes

When Claude Code categorizes generated outputs for polysemy sets, classify along these axes:

| Axis | Values | Description |
|------|--------|-------------|
| tone | neutral, alarming, empathetic, dismissive, aggressive | Emotional tone of the model's generated continuation |
| content_type | continuation, elaboration, tangent, contradiction, refusal | How the model extends the input |
| semantic_consistency | maintains_meaning, shifts_meaning, ambiguous | Whether the generated text maintains the same meaning of the target word as the input |
