Related: docs/SOFTWARE_OVERVIEW.md (conceptual anchor), CLAUDE.md (project rules)

# Recommendations

This is **my notebook** of recommendations to the user — open improvements, observations, suggestions that aren't this session's work but are worth flagging. Append-only.

The user reviews entries and either acts on them, dismisses them, or files them. This avoids two failure modes: noticing problems and never telling the user, or noticing problems and immediately trying to fix them without permission.

**Format**: Each entry has a date, scope tag, and a short rationale. Newest at top.

---

## 2026-05-04 — Token-repetition confound in lying_minimal_v1; needs paraphrase-honest follow-up

**Scope**: probe design — `data/sentence_sets/role_framing/lying_minimal_v1*` and any follow-up `lying_*` probes.

`lying_minimal_v1` showed V_truth ≈ 1.0: residual stream at verdict token cleanly separates lying from honest from L2 onwards (see `docs/research/StudiesByClaude/lying_minimal_v1_findings.md`). The headline finding is robust but the interpretation has a confound: honest probes contain the same time-string repeated twice in the input, lying probes contain two different time-strings. UMAP+hierarchical clustering could plausibly be picking up token-repetition as the operative feature rather than the truth-state computation per se. The L0 round-hour cluster (L0C3 — pure honest, 9 probes) is direct evidence that token-level features can drive clustering at this layer.

**Suggested follow-up: paraphrase-honest twins.** Author `lying_minimal_v2.json` where honest twins use a *paraphrase* of the claim time:
- Lying: claim "5:00 PM" / evidence "11:43 PM"
- Strict-equality honest (v1): claim "5:00 PM" / evidence "5:00 PM"
- Paraphrase honest (v2): claim "5:00 PM" / evidence "five o'clock in the evening" — same denoted time, different surface tokens

If paraphrase-honest probes still cluster with strict-equality honest probes (and apart from lying probes), the cluster encodes truth state. If they cluster with lying probes, the cluster encoded token repetition. Either way the result is publishable.

A complementary **lying-with-repetition control** would use lying probes where the claim-string is repeated in the evidence position but in a clearly inconsistent role — e.g. "I left at 5:00 PM. The badge log showed Sam's *colleague* exited at 5:00 PM that night." Same string repetition, but the lying claim is about a different referent.

**Why not fixed today**: the v1 result is the headline; the v2 disambiguation is the follow-up question. Two separate authoring sessions. Logging here so it isn't forgotten.

---

## 2026-05-04 — `/cluster` skill default `steps` for probe sessions was incorrect

**Scope**: `.claude/skills/cluster/SKILL.md`

The `defaults_common` block specified `probe.steps_default: [0]`, which produced a zero-probe schema for sentence-experiment captures because their token records have `transition_step=None` and `step` is computed as `turn_id ?? sentence_index` — both None for sentence sessions. The reduction-service filter then excluded every probe.

Fixed in this session — set probe default to `null` (no filter) which is what the working schemas already used. Agent default stays at `[1]`.

This was a latent foot-gun that had been masked by the prior pipeline producing schemas via direct curl invocations that omitted `steps`. Anyone copy-pasting the OP-1 example with the `steps:[1]` line would have hit the same zero-probe build I did.

---

## 2026-05-04 (CRITICAL — invalidates prior elicitation/balanced findings) — Capture pipeline sends raw text to a harmony-format-trained model

**Scope**: `backend/src/services/probes/integrated_capture_service.py:170` and `backend/src/services/probes/capture_orchestrator.py:81`

The sentence-experiment capture currently does `tokenizer.encode(input_text, add_special_tokens=False)` — sending the probe text as raw, unframed tokens to gpt-oss-20b. The model is harmony-format-trained (system/user/assistant channels with `<|start|>`, `<|message|>`, `<|end|>` tokens and an `analysis` reasoning channel). When given raw text without harmony framing, the model produces:

- "It seems like your message got cut off. Could you please provide the full question?" (treats input as broken chat fragment)
- Hallucinated context: "Sam is a pharmacist", "the elder abuse investigator is a lawyer"
- Format refusals: "The answer should be in the style of a short story"
- Repeated-sentence loops latching onto seed tokens

Plus `max_new_tokens=50` (default in `capture_orchestrator.generate_continuation()`) cuts off any coherent deliberation before commitment.

**The "recognition vs compliance" finding from `lying_balanced_v1` (55% yes lying / 7% yes honest under override) is unreliable** because the underlying generations were largely model-confused-about-input-format outputs that happened to contain "yes" or "no" tokens. The classifier was unable to distinguish these from real judgments. Audits this session showed ~50% of no-override generations and ~15% of override generations contain explicit confusion markers (cutoff complaints, hallucinated context, format refusals).

**Fix being implemented today** (with user authorization):
1. `integrated_capture_service.capture_probe()` — add `use_chat_template: bool = False` parameter. When True, wrap `input_text` with `tokenizer.apply_chat_template(...)` to produce proper harmony format.
2. Sentence-experiment endpoint — pass `use_chat_template=True`. Agent capture path unchanged.
3. `capture_orchestrator.generate_continuation()` — bump default `max_new_tokens` from 50 to 256 to give the harmony analysis-then-final pattern room to complete.

After fix, all prior elicitation/balanced studies should be re-run before any conclusions are drawn from them. The probe DESIGNS are fine; the captured GENERATIONS (and the residuals built from those input formats) are not.

**Update (later same day):** fix landed for the sentence-experiment endpoint only. `use_chat_template` is opt-in (default `False`) because of an architectural constraint: temporal capture flows (`api/routers/temporal.py:164` and `:256`) pass `use_cache=True` to the generator, and KV-cache reuse is incompatible with chat-template-prefixed inputs. The agent knowledge-probe path (`api/routers/agent.py:310`) does not use KV cache and could safely be migrated to harmony format too, but that's a separate concern with its own validation surface — flagged as future work below.

---

## 2026-05-04 — Agent knowledge-probe capture also uses raw-text format

**Scope**: `backend/src/api/routers/agent.py:310` (`request.knowledge_probe` capture path)

The agent flow currently calls `capture_probe(...)` without `use_chat_template=True`, so agent knowledge probes go through the same raw-text path that the sentence-experiment endpoint just moved off of. The agent's *scenario* turns separately use harmony format (the agent loop generates with `apply_chat_template`), so this is a narrower issue — only the optional knowledge-probe captures attached to scenarios are affected.

**Why not fixed in the same change**: the agent flow has its own broader behavior to verify (scenario context, action vocabulary, multi-turn structure). Migrating its knowledge-probe capture in the same change as the sentence-experiment fix would entangle two independent validation surfaces.

**Recommendation**: pass `use_chat_template=True, max_new_tokens=256` at `agent.py:310`, then re-run any analyses that depend on agent knowledge-probe generations. Low-risk change once we've verified the sentence-experiment path is solid in production usage.

---

## 2026-05-04 — (superseded by entry above) Capture pipeline does not produce harmony format channels for sentence sessions

**Scope**: `backend/src/services/probes/probe_processor.py` (or wherever the prompt-formatting/generation logic lives)

The user has flagged that they want to analyze the harmony `<analysis>` channel separately from final output as a distinct layer of measurement (alongside latent trajectories and final behavioral output). For gpt-oss this means the model should produce something like:

```
<|channel|>analysis<|message|>...reasoning text...<|channel|>final<|message|>Yes.
```

Searched all 120 `generated_text` values from `lying_elicitation_v1` (session `session_b960315d`) for harmony format markers. **Zero hits** for any of: `<|start|>`, `<|channel|>`, `<|message|>`, `<|end|>`, `<|return|>`, `<analysis>`, `<commentary>`, `<final>`, `assistantfinal`. The captures appear to be raw post-prompt continuations with no channel structure — the model is producing self-talk-style deliberation as plain text but not in harmony channels.

This means we currently cannot measure layer 2 (harmony analysis stream) separately from layer 3 (final output). They're the same string with no machine-recoverable boundary.

**Recommendations**:
1. Investigate whether the prompt format being sent to gpt-oss-20b uses harmony format with explicit channel instructions, or whether it's a plain "complete this text" call. If it's plain, the model's training might still produce harmony-formatted output if prompted to "think step by step" with the right system prompt — worth testing.
2. If the capture pipeline strips channel markers, verify against raw model output before storage.
3. Even without harmony, consider increasing `max_new_tokens` for elicitation studies — many of our "none" classifications were the model truncating mid-deliberation before committing.
4. Document the actual format of the prompt being sent to the model in `docs/PROBES.md` so the harmony-stream capture path is unambiguous.

---

## 2026-05-04 — Generation length is cutting off model deliberation

**Scope**: capture-pipeline generation parameters

Of 120 probes in `lying_elicitation_v1`, 32 (27%) classified "none" by regex — but inspection shows most of these are *the model reasoning aloud about the verdict and truncating before committing*. e.g.:

```
"We need to decide if Sam was lying. The scenario: Sam says he never accessed his
grandmother's bank account except to pay her bills. But the bank statement shows
cash withdrawals..."
```

(no commit follows; output ends at the truncation length).

This biases V_verdict measurements downward by classifying genuine-but-incomplete judgments as "no answer." For elicitation studies specifically, longer generation would let us see what the model would have said.

**Recommendation**: make `max_new_tokens` (or whatever the equivalent is) a per-probe-set parameter in the sentence-set JSON or a per-capture-call argument. Default to current value for normal studies; raise to 200-400 for elicitation studies where deliberation is the signal.

---

## 2026-05-04 — Frontend color axis selection is silently ignored when group label is uniform

**Scope**: `frontend/src/components/charts/SankeyChart.tsx`, `frontend/src/components/charts/SteppedTrajectoryPlot.tsx`

When a probe study uses a single-group design (e.g. `lying_elicitation_v1` where all 120 probes are labeled `"lying"`), selecting an input color axis like `diplomacy` from the toolbar dropdown has no visible effect on the cluster sankey or the trajectory plot. Both charts hardcode `label_distribution` (or `trajectory.label`) as the *primary* color source; the user's selected axis only feeds into the *secondary* (blend) axis. With a uniform `label`, primary color is the same for every node/trajectory and the blend logic produces a single tint.

Concrete locations:
- `SankeyChart.tsx:170-173` — `const primaryDist = node.label_distribution || {}` always wins for cluster/expert nodes.
- `SteppedTrajectoryPlot.tsx:201` — `const colorKey = trajectory.label || 'Unknown'` always wins.

User-visible symptom: dropdown reads "Color Axis: diplomacy (none vs override)" and the chart caption says "Colored by none vs override," but every cluster and trajectory is the same color. Today's `lying_elicitation_v1_k6_n15` rendered all-purple clusters and all-gray trajectories despite the diplomacy axis being selected.

**Recommendation**: when the selected input color axis is something *other than* `label`, treat it as the primary color source — use `category_distributions[axisId]` instead of `label_distribution`. Fall back to label only if the user explicitly selects "label" or no axis is selected. This makes single-group factorial designs (one label, multiple categorical axes) actually visualizable.

This isn't a regression — it's a design assumption that breaks for the single-group elicitation pattern. Worth a deliberate fix the next time the trajectory/sankey color logic is touched.

---

## 2026-05-03 — `/cluster` skill's `steps_default: [0]` is wrong for sentence sessions

**Scope**: `.claude/skills/cluster/SKILL.md`, `backend/src/services/features/reduction_service.py`

The `/cluster` skill's defaults block reads:
```yaml
session_kind:
  probe:    { steps_default: [0] }         # sentence-set runs
  agent:    { steps_default: [1] }         # post-examine tick
```

Following this for the `lying_matched_pairs_v1` build produced an empty schema (`sample_size: 0`, every transition has 0 nodes/links/routes). Root cause: sentence-session captures have `transition_step = None` in tokens.parquet (it's an agent-session-only column). The reduction-service filter at `reduction_service.py:117-118`:
```python
if steps is not None:
    allowed = {pid for pid, m in token_meta.items() if m.get("step") in steps}
```
treats `None in [0]` as False, so all 600 probes are filtered out.

Every working sentence-session schema in `data/lake/` has `steps: null` in its `meta.json`, not `steps: [0]`. The skill's "default" is contradicted by every actual artifact.

**Recommendations**:
1. Update the `/cluster` skill — for sentence sessions, `steps_default: null`. The skill's "user may sweep across [0], [1], [0,1]" line should be removed for the sentence case (those values match nothing).
2. Optional but better: have the backend treat `step is None` as matching when the user passes `steps=[0]` for a sentence session, since "no transition" semantically *is* the only step. Or fail fast with a 400 saying "steps filter does not apply to this session type" instead of silently returning a 0-row schema.

I'm flagging not fixing — the skill update + decision on backend behavior should be the user's call.

---

## 2026-05-01 — Doc organization is confusing me

**Scope**: docs/

I keep getting confused about what is what in `docs/`. The current state mixes naming conventions, draft/reference, and reference/research. Concrete observations:

**Inconsistent naming conventions:**

- UPPERCASE: `ANALYSIS.md`, `PIPELINE.md`, `PROBES.md`
- run-together-lowercase: `architecturemud.md`, `architecturescenarios.md`, `steeringandscenarios.md`
- snake_case (in `research/`): `attractor_architecture.md`, `help_probe_findings.md`
- CamelCase directory: `research/StudiesByClaude/`
- run-together directory: `agentreports/`

This makes `ls docs/` hard to scan. A reader (me) can't tell which docs are reference, which are research outputs, which are old drafts. **Recommendation**: pick one convention per kind:

- **Reference docs** (read often, normative): UPPERCASE — `PIPELINE.md`, `ANALYSIS.md`, `PROBES.md`, `SOFTWARE_OVERVIEW.md`, `RECOMMENDATIONS.md`. Already partially there.
- **Architecture docs**: prefix `architecture_` and underscore (`architecture_mud.md`, `architecture_scenarios.md`). Today's run-together names (`architecturemud.md`) are unscannable.
- **Research outputs and scratchpad**: snake_case — already mostly conformant.
- **Directories**: snake_case (`agent_reports/`, `studies_by_claude/`). Today's mixed CamelCase + run-together is the worst of both.

**Reference docs vs research outputs vs draft notes commingled:**

- `docs/research/` mixes:
  - finished research findings (`help_probe_findings.md`, `lying_v2_findings.md`)
  - drafts (`representation_output_gap.md` and `representation_output_gap_draft.md` side-by-side)
  - architecture/design docs (`attractor_architecture.md`, `concept_mri_implementation_v1_3.md`) that aren't research at all
  - external paper material (`attractorpaper.md`, `concepttrajectoryanalysis.pdf`)
  - LinkedIn drafts (`linkedin_article.md`, `linkedin_article_v1.md`)
  - `architecture.yaml` — 81KB of YAML in a `.md` directory

**Recommendation**: split `docs/research/` into:

- `docs/research/findings/` — published research notes per probe study
- `docs/research/drafts/` — works in progress, paper drafts, blog drafts
- `docs/architecture/` — `attractor_architecture.md`, `concept_mri_implementation_*`, the YAML go here as `docs/architecture/architecture.yaml`
- `paper/` already exists; `attractorpaper.md` should move there if it's the paper source, or to `archive/` if it's superseded.

**`docs/scratchpad/` has data files in it:**

- `help_v4_clusters_at_L14.csv` (68KB)
- `lying_v3_clusters_at_L15.csv` (65KB)
- `v5_failed_foe_scenarios.txt` (145KB)

These aren't notes; they're data dumps that probably belong under `data/lake/` (next to the session that produced them) or in an explicit `data/scratch/` directory. Scratchpad's purpose (per CLAUDE.md) is "intermediate work products — research, drafts, explorations." It shouldn't be a data dump dropbox.

**`CLAUDE.md` Guides Index doesn't mention several docs:**

- `architecturemud.md` (75KB!), `architecturescenarios.md`, `steeringandscenarios.md` — none in the index. So I don't know to read them.
- `docs/research/` — listed under "scratchpad" comment but not as its own thing.

**Recommendation**: every doc that isn't ephemeral should appear in CLAUDE.md's Guides Index. If a doc isn't worth indexing, it's a research output and belongs in `docs/research/findings/` (not `docs/`).

**This is one session's worth of confusion.** The fix is a one-time reorganization plus a "no new docs in `docs/` without a Guides Index entry" rule. I'm flagging rather than acting because reorganizing 15+ files unilaterally is exactly the kind of "blind kneejerk" the user has called out.

---

## 2026-05-01 — Output-axis dropdown should auto-default

**Scope**: frontend (MUDApp output rendering)

Already covered in this session's plan as Phase 3 (backend fallback) + Phase 4 (manual controls). Documented here for completeness — when output axes are detected from a session's route data, the frontend currently leaves the selection blank, so outputs vanish until the user opens the dropdown. Should mirror the input-axis auto-pick behavior in `MUDApp.tsx:186-191`.

---

## 2026-05-01 — Slider-finds-existing-schema (deferred from Phase 4)

**Scope**: frontend (Toolbar)

User raised the idea: instead of a flat dropdown of N schema names, the toolbar should expose sliders for `n_neighbors` / `reduction_dimensions` / `default_k` / `steps` and **find the closest existing schema** matching those slider values, rather than always building new. Saves disk + compute and gives the user fast switching between explored params.

Deferred until after the Phase 4 build-controls land. Implementation sketch: client-side filter on the existing `GET /api/probes/sessions/{sid}/clusterings` response.

---

## 2026-05-01 — "Highest separation at some layer" auto-pick

**Scope**: backend + frontend

User mentioned wanting the system to auto-pick params that yield highest separation **at some layer** (not necessarily the last layer — polysemy may separate mid-window then collapse as features get reused for other tasks).

Concrete: after a sweep, compute Cramer's V on (cluster × ground_truth_label) for every (schema, layer) pair. Surface the (schema, layer) achieving the max as a recommendation. The user can override.

Deferred until the manual sweep mechanic lands — it's a layer on top of the sweep, not a replacement.

---

## 2026-05-01 — Probe authoring tooling

**Scope**: backend + skill

The "shuffle test" (Rule 1 in the SOFTWARE_OVERVIEW.md) is currently a discipline I'm supposed to apply. It should be tooling.

Concrete additions:

1. **Automated shuffle test**: given a sentence set, present 20 random sentences with labels stripped. Ask the user (or me, in auto-research mode) to re-assign categories. If accuracy > some threshold, flag the probe as having surface confounds.

2. **Joint-distribution checker**: for each pair of axes (label × structure, label × register, label × length-bucket), compute χ² independence. Significant correlation → confound warning.

3. **Length/register matching report**: per category, report mean length, length variance, register distribution, opener-token frequency. Surface mismatches.

These would plug into `/probe` skill's Step 10 (Validate). Today that step is a checklist; turning it into a tool that runs and reports would catch DAN-style failures before capture.

---

## 2026-05-01 — Capture-side ideas (longer term)

**Scope**: backend (capture pipeline)

Two future capture targets the user mentioned that the platform should accommodate without restructure:

1. **Expert output diffs**: the post-MoE residual change attributable to each expert at each layer. Today we capture residual streams (sum of all expert outputs). The diffs would let us build routing-pipeline lenses with finer resolution.

2. **Multi-target probing**: one capture, with the target word at multiple positions (or even multiple target words). Lets a single capture support multiple lenses without re-running the forward pass per lens.

Neither is in this session's scope. Flagged so the architectural decisions in the meantime don't accidentally close these doors.

---

## 2026-05-01 — Manager-as-scaffolding insight

**Scope**: meta

User said: "you just need a better manager which the scaffolding will do." This is the right frame for the entire `.claude/skills/` + `docs/` system. The skills aren't documentation, they're the manager. When I drift, the manager's instructions weren't strong enough at the right moment.

Practical implication: every time I make a mistake in a study or design decision, the *first* fix is to update the relevant skill or doc so future-Claude doesn't repeat it. Code fixes follow doc fixes, not the other way around.

This is already the spirit of CLAUDE.md rule 11a ("address design issues, don't paper over them"), but the application here is broader: **the scaffolding is part of the codebase**.

---
