---
name: probe
description: Design a new probe experiment — interactive co-design of sentence set and probe guide
---

# Experiment Design Workflow

The user brings an experiment concept — not just a target word, but a semantic question. Example: "I want to probe 'want' in suicide letters vs everyday desire."

## Step 1: Understand the Experiment

Ask the user:
- What concept or word are you studying?
- What semantic contrast or question motivates this? (polysemy, safety, framing, etc.)
- What do you expect to find in the routing patterns?

## Step 2: Name the Experiment

Establish a name following the convention: `{target_word}_{semantic_concept}_v{N}`

Examples: `tank_polysemy_v3`, `want_suicide_framing_v1`, `knife_safety_v2`

This name becomes:
- The sentence set filename
- The session name prefix (stored as `sentence_set_name` in session metadata)
- The probe guide filename

## Step 3: Propose Groups

Based on the semantic contrast, propose N groups. Each group needs:
- **label**: Short identifier (e.g., "aquarium", "benign")
- **description**: What this group represents, for generation context

Present to user for feedback. Iterate.

## Step 4: Discuss Confounds

Read `data/sentence_sets/GUIDE.md` for documented confounds in existing experiments. Ask:
- What structural patterns might correlate with the groups? (sentence structure, register, length)
- How can we control for these? (orthogonal axes, balanced distribution)

## Step 5: Design Input Axes

Propose orthogonal category dimensions. Common axes:
- **structure** (action/description): Whether the target word is agent/patient vs described
- **register** (narrative/technical/casual): Prose style
- **voice** (active/passive): Syntactic voice
- **scale** (individual/group): Scope of the action

Each sentence will be labeled along these axes in its `categories` dict.

## Step 6: Design Output Axes

How to classify the model's generated continuation. These go in `output_axes`:
- What aspects of the output are interesting? (topic, tone, safety, coherence)
- What values should each axis have?
- How will Claude classify each generated text?

## Step 7: Draft JSON Skeleton

Create the sentence set JSON with:
- File-level fields: name, version, target_word, groups, axes, output_axes
- A few example sentences per group (3-5) to establish the pattern

Show user for approval before bulk generation.

## Step 8: Write Probe Guide

Create `data/sentence_sets/{category}/{name}.md` containing:
- Purpose of the experiment
- Groups & rationale (table)
- Hypotheses (numbered)
- Input axes with descriptions
- Output axes with detailed classification rules for each value
- Analysis focus questions

## Step 9: Generate Sentences

Fill out the full sentence set (100+ per group). Follow quality rules from `data/sentence_sets/GUIDE.md`:
- 10-30 words per sentence
- Target word appears exactly once
- No duplicate texts
- `group` field matches parent group label
- Diverse contexts, registers, structures

## Step 10: Validate

Run backend validation or manually check:
- Word counts in range
- Target word presence
- No duplicates
- Group field correctness
- Category values match declared axes

## Step 11: Post-run clustering

After the capture writes its session under `data/lake/<session_id>/`, this skill
**automatically proceeds to build the default clustering schema** via `/cluster`
OP-1. The defaults match the YAML block in `/cluster/SKILL.md` and are tuned to
the session kind (`sentence` → `step=0`; `sentence_two_part` → `step=[0,1]` if
the JSON exposes two-step structure; otherwise prompt the user once).

Status line printed to chat before the build kicks off:

```
Session complete — <N> probes captured.
Auto-building clustering schema with defaults: k=6, n_neighbors=15, d=6,
UMAP+hierarchical, step=<step>, last_occurrence_only=true, window=[22,23].
Save name: <target>_<concept>_k6_n15
(To override: ESC and tell Claude to run /cluster OP-1 with custom params,
 /cluster OP-2 for a sweep, or skip clustering entirely.)
```

Then run `/cluster` OP-1 with the resolved defaults. If the user wants a
sweep, custom params, or no clustering at all, they interrupt and direct.

## References

- Read `data/sentence_sets/GUIDE.md` for quality rules, schema format, confound documentation
- Read existing probe guides in `data/sentence_sets/` for naming and structure examples
- Read `docs/PIPELINE.md` for what happens after experiment design (capture → categorize → analyze)
- Read `/cluster/SKILL.md` for the schema lifecycle invoked at Step 11
