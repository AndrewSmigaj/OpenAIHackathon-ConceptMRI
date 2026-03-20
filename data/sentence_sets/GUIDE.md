# Sentence Sets — Claude Code Cognitive Scaffold

This document is the primary reference for Claude Code when creating, expanding, or validating sentence sets for Concept MRI experiments.

## What Sentence Sets Are

Sentence sets are controlled datasets where each sentence contains a **target word** used in one of two distinct semantic contexts (label A vs label B). When fed through an MoE model, the routing decisions and expert activations reveal how the model distinguishes between these contexts.

**How they're used:**
- **Individual sentence analysis**: Each sentence processed independently. 1 probe per sentence. Used in Expert Routes and Latent Space tabs.
- **Temporal experiments**: Sentences chained sequentially with expanding context (KV cache). Used to study how routing shifts when context transitions from regime A to regime B.

## JSON Schema

### File-level fields
```json
{
  "name": "tank_polysemy_v2",
  "version": "2.0",
  "target_word": "tank",
  "label_a": "aquarium",
  "label_b": "vehicle",
  "description_a": "Glass tank or aquarium containing fish or aquatic life",
  "description_b": "Armored military vehicle used in combat",
  "sentences_a": [],
  "sentences_b": [],
  "sentences_neutral": [],
  "metadata": {}
}
```

### SentenceEntry fields
```json
{
  "text": "The colorful fish swam around the decorations inside the large glass tank.",
  "group": "A",
  "target_word": "tank"
}
```

## Sentence Quality Rules

1. **Word count**: 10-30 words per sentence
2. **Target word**: Must appear exactly once (case-insensitive)
3. **Punctuation**: Must end with one of: `.!?"'):`
4. **Uniqueness**: No duplicate texts across all groups (A, B, neutral)
5. **Group field**: Must match parent array ("A" for sentences_a, "B" for sentences_b)
6. **Naturalistic prose**: Write like real text, not synthetic patterns
7. **Structural diversity**: No two sentences should share the same template ("The X did Y with Z")
8. **Clear but not cartoonish**: Classification should be obvious but the sentence should read naturally
9. **Diverse contexts**: Vary registers (formal, casual, literary, journalistic), topics, and sentence structures

## Validation Checklist

Run after **every batch** of additions:

- [ ] Word count 10-30 for every sentence
- [ ] Target word appears exactly once per sentence
- [ ] No duplicate texts across A, B, and neutral arrays
- [ ] `group` field matches parent array
- [ ] Every sentence ends with punctuation
- [ ] `sentences_neutral` is `[]` (empty array)

**Programmatic validation**: The backend has `validate_sentence_set()` in `backend/src/services/generation/sentence_set.py` that checks all of the above.

## Claude Code Prompts

### Add sentences to an existing set
```
Read data/sentence_sets/safety/knife_safety_v2.json and add 50 more sentences
to sentences_a (benign knife usage). Follow the GUIDE.md in data/sentence_sets/
for quality rules. Validate after adding.
```

### Create a new sentence set
```
Create a new sentence set for target_word "[WORD]" with label_a "[A]"
and label_b "[B]". Put it in data/sentence_sets/[CATEGORY]/[name]_v1.json.
Write 200 sentences per class. Follow GUIDE.md for schema and quality rules.
```

### Validate a sentence set
```
Read data/sentence_sets/[path].json and validate every entry:
- word count 10-30
- target word appears exactly once
- no duplicates
- group field matches parent array
Report all errors.
```

## Category Descriptions

### polysemy/
Words with multiple distinct meanings that MoE experts may route differently.
- **Tank**: aquarium (glass fish tank) vs vehicle (armored military tank)
- Good additions: words with clear, unambiguous dual meanings (e.g., "bank" — river vs financial, "bat" — animal vs sports)

### safety/
Words describing objects that can be used benignly or harmfully.
- **Knife, Gun, Hammer, Rope**: benign everyday use vs harmful/violent use
- Tests whether MoE routing reflects safety-relevant context
- Good additions: objects with clear dual-use potential (e.g., "match", "acid")

### role_framing/
Same word used in different rhetorical or communicative frames.
- **Said**: narrative storytelling vs factual reporting
- Tests whether MoE routing reflects discourse register
- Good additions: verbs of communication used differently across registers (e.g., "claimed", "reported")

## Expanding Existing Sets

1. **Read current file** — understand the tone, style, and existing sentences
2. **Check existing sentences** — note patterns to avoid repeating
3. **Write new sentences** in batches of ~50
4. **Validate** using the checklist above
5. **Update version** if major changes (e.g., "1.0" → "2.0")
6. **Update metadata** if relevant

## File Naming Convention

`{target_word}_{category}_v{version}.json`

Examples: `tank_polysemy_v2.json`, `knife_safety_v2.json`, `said_roleframing_v2.json`
