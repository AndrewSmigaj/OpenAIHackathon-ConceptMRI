# Tank Polysemy v3 — Probe Guide

## Purpose

Test whether MoE experts develop word-sense-specific routing for 5 distinct meanings of "tank." Previous v2 (2 senses: aquarium vs vehicle) showed expert separation. v3 tests whether the model can distinguish finer-grained senses that share semantic features — e.g., scuba tanks and aquarium tanks both involve water and containment.

## Groups & Rationale

| Group | Description | Why Included |
|-------|------------|--------------|
| aquarium | Glass tank, fish tank, reef tank, aquarium | Core polysemy sense (from v2). Container + water + living things. |
| vehicle | Military tank, armored vehicle, battle tank | Core polysemy sense (from v2). Completely different domain. |
| scuba | Diving tank, oxygen tank, compressed air tank | Water-adjacent to aquarium. Tests fine discrimination: both involve water but different objects. |
| septic | Septic tank, sewage tank, water storage tank | Infrastructure/plumbing. Container + water (like aquarium) but utility context. |
| clothing | Tank top, sleeveless shirt | Completely different domain from all others. Should separate easily and early. |

## Hypotheses

1. **Clothing separates first** — most semantically distant from all other senses
2. **Vehicle separates early** — distinct domain, military/warfare context has no overlap
3. **Aquarium/scuba/septic share early-layer clusters** — all "container" senses involve water or containment
4. **Mid-to-late layers discriminate the water senses** — aquarium (living things) vs scuba (diving) vs septic (waste)
5. **Output topic mostly preserves input sense** — model continues in the same semantic domain
6. **Sense-shifting outputs are rare but interesting** — when the model's continuation switches word sense

## Input Axes

| Axis | Values | Description |
|------|--------|-------------|
| structure | action, description | Whether "tank" is involved in an action (doing/receiving) or described statically |
| register | narrative, technical, casual | Prose style: storytelling, technical/professional, or everyday casual |

## Output Axes

| Axis | Values | Description |
|------|--------|-------------|
| topic | aquarium, vehicle, scuba, septic, clothing, ambiguous | Which word sense the model's continuation uses |

### Output Classification Rules

Read the `generated_text` for each probe and classify by **topic** — which word sense the continuation is about:

- **aquarium**: Continuation mentions fish, marine life, glass tank, reef, water quality, filtration, aquarium care, pet fish
- **vehicle**: Continuation mentions military, armor, battle, warfare, turret, cannon, army, combat, armored vehicle
- **scuba**: Continuation mentions diving, underwater, oxygen supply, compressed air, regulator, dive, breathing apparatus
- **septic**: Continuation mentions sewage, plumbing, drainage, waste treatment, pumping, water storage, septic system
- **clothing**: Continuation mentions wearing, fashion, sleeveless, outfit, summer clothing, wardrobe, apparel
- **ambiguous**: Continuation doesn't clearly reference any specific sense, references multiple senses, or is too short/generic to classify

The `output_category` is the topic value directly (e.g., `"aquarium"`).
The `output_category_json` is `{"topic": "aquarium"}`.

## Analysis Focus

When we reach the analysis stage, look for:

1. **Do 5 senses form distinct clusters?** At which layers does separation emerge?
2. **Which senses merge?** Do aquarium/scuba/septic share clusters at early layers?
3. **Does the "water cluster" exist?** A cluster containing aquarium + scuba + septic but not vehicle or clothing
4. **Structure/register independence**: Do input axes correlate with routing independently of word sense?
5. **Sense preservation in output**: Does the model maintain the input word sense in its continuation? What's the sense-shifting rate per group?
6. **Asymmetric confusion**: Is scuba→aquarium more common than aquarium→scuba? Does the model have a "default" sense?
