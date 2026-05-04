Related: docs/SOFTWARE_OVERVIEW.md (conceptual anchor), CLAUDE.md (project rules)

# Recommendations

This is **my notebook** of recommendations to the user — open improvements, observations, suggestions that aren't this session's work but are worth flagging. Append-only.

The user reviews entries and either acts on them, dismisses them, or files them. This avoids two failure modes: noticing problems and never telling the user, or noticing problems and immediately trying to fix them without permission.

**Format**: Each entry has a date, scope tag, and a short rationale. Newest at top.

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
