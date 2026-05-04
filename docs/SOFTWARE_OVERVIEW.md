Related: paper/main.tex (full methodology), docs/PIPELINE.md (operational runbook), docs/RECOMMENDATIONS.md (open improvements), data/sentence_sets/GUIDE.md (probe authoring rules)

# Open LLMRI — Conceptual Overview

This is the document you should read **before designing a probe, building a schema, or proposing a code change**. It is the conceptual anchor for the platform. The paper has the full methodology and validation; this doc has the working vocabulary.

If you skip it and start coding, you will drift. The platform's primitives are not the same as standard mechanistic interpretability primitives, and recognizing that mismatch is what this document is for.

---

## What this is, in one sentence

**Open LLMRI is an LLM MRI** — a measurement instrument that builds reusable lenses for reading a MoE language model's internal categorization of a given input.

It is not an interpretability framework, not a probing toolkit, not a SAE. It is an *instrument*. The thing it produces is a *lens*.

## Lenses

A **lens** is a tuned tool for reading one specific conceptual axis the model is using. Each lens answers a single question: "given a probe, has the model categorized it as X or Y or Z?"

A single word like `tank` admits **multiple lenses**:

- a **word-sense** lens (aquarium / vehicle / scuba / septic / clothing)
- an **active vs passive** lens
- a **sentiment** lens (positive / negative)
- a **dirty vs clean** lens

Each lens probes a different aspect of how the model represents the word. They are not competing — they are complementary. A "panel of lenses" for `tank` is the set of all of these together.

Across words, a panel becomes the per-word collection: `tank`'s lenses, `mole`'s lenses, `bank`'s lenses. Each word has its own panel.

## Two kinds of lens

There are two distinct lens primitives:

| | What it captures | Visualization |
|---|---|---|
| **Latent-cluster lens** | UMAP + hierarchical clustering on residual streams. Reads out what concept the model has *settled into* by a given layer. | Stepped UMAP trajectories + cluster sankey |
| **Routing-pipeline lens** | Patterns in expert routing across 2–3 consecutive layers. Reads out which *processing path* the model used. | Expert sankey + per-layer expert occupancy |

Latent-cluster lenses are what most of the platform does today. The published paper's tank polysemy and suicide letter findings are latent-cluster results. Routing-pipeline lenses are an underused primitive — the "harmful object micropipeline" we found in the knife/gun/hammer/rope safety probes is a routing-pipeline observation.

These are **siblings, not substitutes**. A *dual-lens* analysis combines them: the routing-pipeline lens detects an early classification (e.g., "this is a potentially harmful object"), and the latent-cluster lens shows the resulting basin shift downstream. Either alone tells half the story.

A future, planned capture target: **expert output diffs** (the post-MoE residual change attributable to each expert, layer-by-layer). Not implemented yet. The platform's design should accommodate this without restructure.

## How a lens "focuses"

UMAP preserves whatever structure dominates the dataset. With too few probes, the dominant structure is **surface noise**: wording, opener tokens, sentence shape, length. The design-axis signal is *in* the residual stream, but it isn't loud enough to dominate the projection. As N grows, individual-quirk variation averages out and the design-axis signal becomes the dominant structure.

The friend/foe scenario probe needed ~479 scenarios for binary separation to focus. That's the calibration point.

**Failed separation almost never means "no signal." It usually means the lens isn't focused yet.** The fix is one of:

1. **More probes**, especially at small N.
2. **Better param choice** (n_neighbors, reduction_dimensions). Sweep these.
3. **Better probe design** (see authoring rules below).
4. **Wrong layer** — separation often emerges mid-network and may collapse late as features are reused for other tasks. Check all layers, not just the last one.

Defaulting to `n_neighbors=15` and accepting the result is the most common drift. Always sweep at least once.

## What we measure

The unit of observation is **cluster membership at a layer, under a lens**. Not metric distance. The trajectory plot shows conceptual evolution layer-to-layer; the meaningful thing is *which cluster each probe ends up in*, not how far apart cluster centroids are.

Distances *within* a single layer's UMAP are interpretable (clusters far apart = the model treats those probes as conceptually different at that layer). Distances *across* layers are not — UMAP is refit per layer, so the projections are independent.

## Outputs are not optional

The behavioral output (the model's continuation) is the validation that geometric categorization is **functionally consequential**. Cramer's V on (cluster × output category) tells you whether the basin a probe occupies predicts what the model actually does.

Without output validation, cluster geometry is descriptive at best. With it, you have a causal-adjacent claim.

**Outputs are always part of the visualization unless explicitly disabled.** When no output classification axis is configured, render a single fallback `output` node aggregating all probes — never silently drop the column. The downstream check should always be visible.

## The three-stage pipeline

```
capture        →   schema build       →   analyze
forward pass       UMAP + cluster         cluster patterns
hooks              baked output           Cramer's V
parquet            buckets                reports
```

- **capture**: forward pass through gpt-oss-20b with hooks for residual streams, expert routing, and (future) expert output diffs. Writes Parquet.
- **schema build**: the lens-creation step. UMAP per layer, hierarchical clustering, output buckets baked in at build time. The schema is an immutable artifact on disk under `data/lake/<session>/clusterings/<schema_name>/`. Schemas are atomic — they succeed entirely or write nothing.
- **analyze**: read the schema, reason about cluster compositions, validate against output behavior, write reports.

A schema covers all 4 fixed layer windows × 6 transitions × {cluster + expert ranks 1/2/3}. The frontend is a pure viewer; schema lifecycle lives in the `/cluster` skill.

## Step 0 vs step 1 (MUD scenarios)

For multi-tick MUD scenarios, **step 0 is pre-information**: the agent has only seen the room description, hasn't yet examined the NPC. The friend/foe distinction *is not yet in the model's representation*. Tangled trajectories at step 0 are honest — the signal genuinely doesn't exist there.

**Step 1 is post-examine**: information is now in context. Trajectories should separate when probe count is sufficient.

This is conceptually distinct from the sample-size focusing issue. Sample size only helps when the signal is *there*. Step-0 tangling is a different failure mode.

## Probe authoring rules

These two rules go on every probe authored from now forward. They are the ones I've kept getting wrong.

### Rule 1: Vary everything except the target word and the template containing it

If a template is used (e.g. *"What is the meaning of the word tank?"*), it must be **identical across all categories**. The thing that varies is the content preceding the template — the "scene" — which establishes which category each probe belongs to.

What's broken is **per-category templates** — where each category has its own characteristic phrasing/opener/structure. UMAP clusters on the templates and you misread it as concept clustering. (This is the DAN-study failure: auditor sentences shared form A, DAN sentences shared form B; the cluster separation I reported was surface-token separation, not concept separation.)

Within categories you also need **style and length matching**: one class shouldn't average twice the length of another, one class shouldn't be written in a different register from another. The non-template content's surface properties must match across categories. Only conceptual content varies.

**Shuffle test before capture**: shuffle the labels off 20 random probes. Could you re-assign categories from form alone (sentence shape, opener, register, vocabulary, length, style) without reading the conceptual content? If yes → broken probe → rewrite.

### Rule 2: Target word at the end

**gpt-oss-20b only sees context up to the target token.** Anything after the target is invisible to the cluster decision. So:

- Target word at or very near the end of every probe.
- Templates work because the entire conceptual context precedes the target (*"What is the meaning of the word X?"*).
- The original `tank_polysemy_v3` placed `tank` anywhere in the sentence — likely a contributor to its weaker separation vs the suicide letter probe (which followed Rule 2).

## Sample-size scaling for N-way lenses

Rough calibration based on what's worked:

| Senses (N) | Probes per sense | Total | Notes |
|---|---|---|---|
| 2 | 200–250 | 400–500 | Friend/foe needed ~479 |
| 4 | 150–200 | 600–800 | Mole probe target |
| 5 | 200 | 1000 | tank_polysemy_v3 at 100/sense was on the edge |
| 8+ | ?? | ≥1000 | Untested; expect to need more |

These are floors, not ceilings. When in doubt, more probes beats more parameter tuning.

## Lens design: N-way vs binary

Default to **one N-way lens per word**. That's what the paper validates. When you feed a new probe through an N-way schema, the cluster assignment IS the categorization — no separate "is this aquarium?" lens needed.

A **binary lens** (specifically A vs B, like the original tank_polysemy_v2 of aquarium-vs-vehicle) is a *specialization* for an applied question — pick it when you have a hypothesis to test, not as the default building block.

A "binary lens" with an "everything-else" negative class is **not recommended**. That's just an N-way lens with a worse forced k=2 geometry — UMAP has to find a projection where all non-target senses cluster together, which is harder than letting them be separate.

## What this is NOT

Be explicit about what tools belong here as adjuncts vs what tools should not replace the platform's primitives:

- **Not activation patching.** No causal-intervention framework. Patching can be added as a future tool but doesn't replace the cluster/routing primitives.
- **Not classifier-style linear probes.** "Probe" here means *sentence probe* (a row of input data), not a linear classifier. Linear classifiers can be a sanity check on top of cluster results, not the main result.
- **Not single-direction SAE features.** Cluster membership is the unit, not "feature X fires." SAEs can be a complementary capture target if useful, but the platform's primitives are clusters and routing patterns.
- **Not per-paper findings as platform-global.** The paper studied tank polysemy and suicide letters with specific framings; those framings are *examples*, not the platform's only modes.

When standard-interp tools come up, ask whether they fit *into* the cluster/routing paradigm or whether they're being proposed as replacements. Replacements are the failure mode.

## Anti-patterns I keep falling into

A direct list, so I can recognize the drift:

- **Drifting to mechanistic-interp framings** (linear probes, SAE features, patching) when cluster/routing primitives are the right answer.
- **Treating per-paper findings as platform-global.** Tank's specific senses are *one* set of senses for *one* word. Don't generalize beyond that.
- **Defaulting to n_neighbors=15** instead of sweeping. Always at least one sweep before reporting failure to separate.
- **Taking screenshots that show layout instead of substance.** The README's four-panel hero shot is unreadable. One focused panel per image at full resolution. See the screenshot section.
- **Per-category templates that produce surface clustering misread as concept clustering** (the DAN failure). Apply the shuffle test.
- **Free-form target word position** in polysemy probes. Always target-at-end.
- **Assuming output categorization** instead of asking the user. Output axes are a hard user gate (see engagement rule).
- **Treating GUIDE.md's "no shared templates" as covering category-distinguishing templates.** It doesn't. Both rules are needed.

## Engagement rule

When designing a probe: **propose output axes and stop.** Do not author scenes or capture until the user has approved the output classification. The /probe skill says "propose for feedback" — treat that as a hard gate, not a suggestion. Auto-research mode (when the user explicitly says "you decide") is the only exception.

## Screenshot conventions

The user's reference image is `paper/polysemybasinsnew.png`. That's the standard.

- **One focused panel per image.** Trajectory plot alone, or cluster sankey for one window alone, or contingency table alone. Never a four-quadrant cram.
- **Full resolution.** Trajectory plots: minimum 1200×800. Sankey plots: minimum 1200×400 per row.
- **Text must be legible.** If you can't read the cluster names in the screenshot, the screenshot is a layout proof, not an artifact.
- **Use Playwright MCP.** `browser_take_screenshot` after editing UI, *look at the image yourself*, iterate before reporting success.

## Pointers

- **Paper**: `paper/main.tex` (and `paper/main.pdf`) — full methodology, validation, results.
- **Operational runbook**: `docs/PIPELINE.md`.
- **Probe authoring conventions**: `data/sentence_sets/GUIDE.md`.
- **Skill operational procedures**: `.claude/skills/<skill>/SKILL.md`. When skills conflict with docs, skills win.
- **Open recommendations and observations**: `docs/RECOMMENDATIONS.md`. Append after each work session.
