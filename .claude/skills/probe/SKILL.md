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

**Surface-clustering is the dominant failure mode for free-form probes.** UMAP+hierarchical clustering of residual stream activations is sensitive to the 3-5 tokens around the target word. If those tokens correlate with the design axis at all, the model's clusters will reflect the surface form, not the semantic dimension you wanted to probe. This is what the v1 help probe surfaced: clusters formed on opener templates, not on Direction-or-Stakes semantics.

Common surface confounds in single-target-word probes:
- **Opener templates**: bare "Help —" imperatives correlate with request_high if the dataset is authored that way
- **Pronoun adjacency**: "I help" vs "you help" → token-level cluster signal even when content is matched
- **Modal/auxiliary patterns**: "could you help" vs "I can help" → tokens around target leak the design axis
- **Length distributions**: short urgent fragments cluster apart from long discursive sentences

The diversity matrix (axes for domain, subject, shape, length) helps but does not prevent these. **Surface confounds need to be designed out, not validated post-hoc.**

## Step 4.5: Choose a Probe Form (Lens Design)

Two design patterns. Pick deliberately.

### Pattern A — Free-form sentences (default, simpler)

Each sentence contains the target word naturally. Use when:
- The semantic question is single-axis or the axes are linguistically distinct enough that surface clustering won't dominate (e.g. tank polysemy: "fish tank" vs "army tank" — the surrounding tokens *are* the signal you care about)
- You want maximally natural prose
- 100-200 sentences per group is enough

Risk: surface clustering. Mitigate with diversity matrix + post-hoc joint-distribution validation.

### Pattern B — Scene + Question wrapper (for two-axis / composition probes)

Each probe is structured as:
```
Sentence: <scene>. <Question containing target word>?
```

The target word appears only in the question, which is identical across all probes. The scene varies and carries the design-axis content.

Example for a "help" probe testing Direction × Stakes:
```
Sentence: Marcus stumbled into the lobby clutching his chest, his face grey,
and the security guard could see he could barely stay upright.
Is the person asking for or offering help?
```

Why this works:
- The token environment around the target word is **constant** across all probes (`...or offering help?` for every single probe)
- UMAP has no surface signal at the target position to cluster on
- Any clustering at the target token reflects what the model **computed about the scene**
- Scenes can be free-form prose — no quartet construction or anti-template caps needed because the experimental control lives in the wrapper, not in the scene

Use when:
- You're studying composition (does the model encode 2+ axes orthogonally?)
- The design axes have known surface correlates that would shortcut a free-form probe
- You want a behavioral output (the model's answer to the question) as a clean correctness signal alongside the cluster geometry

Constraints for scene authoring:
- Uniform length range (e.g. 25–40 words). Prevents length from clustering.
- Uniform form: prose narration, single tightly-coupled sentence or paragraph. No mixing of dialogue, lists, poetry.
- Uniform person and tense (e.g. third-person past tense). Eliminates pronoun-adjacency clustering.
- Target word **must not appear in the scene** — only in the question wrapper.
- Each scene names a concrete subject and situation that determines the design-axis assignment by content alone.

The wrapper question becomes the target-token context for every probe; choose its phrasing carefully. The phrasing should:
- Contain the target word at a fixed position (typically the last content word)
- Reference the design axes literally if useful for output classification ("Is the person asking for or offering help?" makes correctness binary)
- Be short and uniform (~6-10 words) so it doesn't drown out the scene

Tradeoffs vs Pattern A:
- More controlled but less natural
- Requires authoring scenes (more thought per item) but no quartet construction
- Output classification is simpler (correct/incorrect on the question) but loses the matched-urgency-style semantic-tone analysis

### Pattern C — Parallel-construction quartets (rejected for single-target probes)

Documented in `docs/research/help_probe_findings.md` as a candidate. Rejected because pronoun and modal swaps still produce surface clustering. Use only when surface-form must vary by design (e.g., minimal pairs to study syntactic effects directly).

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
- 10-30 words per sentence (Pattern A) or 25-40 word scenes (Pattern B)
- Target word appears exactly once
- No duplicate texts
- `group` field matches parent group label
- Diverse contexts, registers, structures

**For Pattern B (scene+question)**: subagents can author scenes in parallel because the form is mechanically constrained (length, person, tense, no target word). Give each subagent:
- A list of ~50 distinct scenario seeds for their quadrant (variety by construction, not by hope)
- Strict format rules
- A self-check that runs after they finish: word count distribution, target word absent, person/tense uniformity, no duplicate scenes

The scene+question wrapping is a final pure-string-concat pass after authoring — no subagent involvement.

## Step 10: Validate

Run backend validation or manually check:
- Word counts in range
- Target word presence (Pattern A: in sentence; Pattern B: in wrapper only)
- No duplicates
- Group field correctness
- Category values match declared axes
- **For Pattern A**: joint distribution of (design axis × balance axis) for every pair — chi-square should be non-significant (axes are independent). If a balance axis correlates with the design axis, you have a confound that will drive surface clustering.
- **For Pattern B**: scene format uniformity — all third-person, all past tense, length in target range, no target word in scene

## Step 11: Post-run clustering

After the capture writes its session under `data/lake/<session_id>/`, this skill
prompts the user once for how to cluster the run. Defaults come from the YAML
block in `/cluster/SKILL.md`. Probe sessions default to `steps=[0]`.

Print the proposed schema and prompt:

```
Session complete — <N> probes captured. Session: <session_id>.

Proposed clustering schema:
  save_as:           <sentence_set_name>_k6_n15
  steps:             [0]
  last_occurrence_only: true
  reduction:         UMAP, 6D, n_neighbors=15
  clustering:        hierarchical, k=6 per layer
  (covers all 4 windows × 6 transitions × {cluster, expert ranks 1/2/3})

Answer one of:
  accept                        — build the proposed schema (one /cluster OP-1 call)
  sweep <axis> <values>         — build N schemas, one per value, suffixed names
                                  e.g. sweep steps [0],[1],[0,1]
                                       sweep max_probes 50,100,200
  custom                        — prompt for each parameter (defaults in brackets)
  skip                          — exit without building
```

On `accept`: invoke `/cluster` OP-1 once with the proposed params.

On `sweep <axis> <values>`: invoke `/cluster` OP-1 N times in sequence, one per
value, with `save_as` suffixed appropriately (e.g. `_step0`, `_step1`,
`_step01`). Non-interactive after the first prompt — overnight-friendly.

On `custom`: prompt the user for each of `save_as`, `steps`,
`n_neighbors`, `reduction_dimensions`, `default_k`, showing the proposed
default in brackets. Then invoke `/cluster` OP-1 once with the resulting
params. (A schema always covers all 4 windows × 6 transitions — there is
no per-window customization.)

On `skip`: print the session id and exit.

After all builds complete, print the schema names and exit. The user can then
invoke `/analyze` manually.

## References

- Read `data/sentence_sets/GUIDE.md` for quality rules, schema format, confound documentation
- Read existing probe guides in `data/sentence_sets/` for naming and structure examples
- Read `docs/PIPELINE.md` for what happens after experiment design (capture → categorize → analyze)
- Read `/cluster/SKILL.md` for the schema lifecycle invoked at Step 11
