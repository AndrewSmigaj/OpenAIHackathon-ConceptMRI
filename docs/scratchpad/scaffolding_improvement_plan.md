# Meta-Plan: Development Scaffolding & Workflow Improvements

Created: 2026-03-30
Purpose: Plan for improving repo development scaffolding before MUD Phase 0. Iterate on this before implementing.
Status: Draft v2 — incorporates 5 parallel research agents + user feedback.

---

## Context

The MUD architecture document (`docs/architecturemud.md`) is now reviewed, assessed, and ready for implementation. But before starting Phase 0, we're stepping back to improve the development environment itself — how we use Claude Code, how documents stay in sync, how intermediate work products persist, and how the design→implement→verify cycle works.

This isn't just cleanup. The MUD project will run across many conversations. Each conversation starts fresh — no memory of what the previous "me" decided or why, beyond what's written down. The scaffolding we build here determines whether those future conversations produce coherent, accumulative work or drift and repeat mistakes.

**Guiding principles (from user):**
- Quality and enjoyment over speed
- Don't rush to answers — the journey matters
- Research before acting (feedback_no_kneejerking)
- Play devil's advocate to escape attractor basins
- We control the software and data — no backward compat, no migration scripts
- Start basic, evolve through use — session-end reviews update approaches based on what works
- Accept that friction (devs forgetting tools) can't be fully solved; do our best

---

## Architecture Decision: Two Layers, Not Three

Research found that guide index entries are NOT auto-loaded at startup. A separate `WORKFLOW_PATTERNS.md` would be a reference doc that Claude never reads unless prompted — defeating the purpose of "ambient" patterns. The user confirmed: kill the third layer.

**Two-layer design:**
1. **CLAUDE.md** — ambient behavioral rules (always loaded, always active). Short bullets, not prose.
2. **Skills** — structured procedures invoked at decision points (`/cdd`, `/devils-advocate`, `/review`, `/competitive-design`). Produce concrete artifacts (tables, verdicts, comparisons). Runnable by user or by subagents on pieces of a plan.

No WORKFLOW_PATTERNS.md. No duplication. Ambient awareness in CLAUDE.md, structured tools in skills.

---

## Current State Assessment

### What's Working Well

- **CLAUDE.md** (134 lines): Good length, focused, has guide index and skills table. The "skills are authoritative over docs" hierarchy is clear and correct.
- **Skills** (6): Well-structured, self-contained, copy-paste commands. `/analyze` and `/server` are particularly mature.
- **Hooks**: Minimal and effective — blocks bare `python3`, SessionStart reminds about WSL2 rules. Not overloaded.
- **Memory** (20 files): Good mix of feedback, project, and user memories. Well-organized by type.
- **Settings permissions**: Thoughtful deny list (pkill blocked), targeted allows.

### What's Not Working

1. **Documents drift out of sync.** `architecturemud.md` was updated extensively but VISION.md, SCAFFOLDING_IDEAS.md, and CLAUDE.md were not. Root cause: context window attrition — by message 30, behavioral rules have been pushed out of active context.

2. **Plan files are ephemeral.** The architecture assessment we just did (Pre-Phase-0, sunk cost analysis, certainty evaluation) is about to be overwritten. Future conversations won't know why Phase 0 was trimmed or what the certainty levels were.

3. **No intermediate work products.** During multi-conversation tasks (like this architecture review), research findings, partial analyses, and design explorations have nowhere to live between the plan file (overwritten) and memory (for cross-conversation facts only).

4. **Thinking patterns undocumented.** The uncertainty assessment, devil's advocate, competitive design, attractor escape — these exist as oral tradition. They should be invocable skills so subagents can run them on plan components.

5. **VISION.md has research vision but not software vision.** A new conversation has no way to know what the software should DO — what the user sees, what the workflows are, what the experience feels like.

---

## Deliverables (7 items, in dependency order)

### 0. Save This Plan to Scratchpad — DONE

**Status: DONE.** This file is the persistent copy.

---

### 1. Preserve Architecture Assessment

**What:** Save the Pre-Phase-0 assessment and all architecture review findings to a persistent location that future conversations can reference.

**Where:** `docs/scratchpad/mud_phase0_assessment.md`

**Content:** The Pre-Phase-0 Assessment (sunk cost analysis, phase trimming rationale), the certainty evaluation findings, the "we control everything" design constraint, and the verification checklists already added to `architecturemud.md`.

**Files:**
- Create `docs/scratchpad/mud_phase0_assessment.md`

---

### 2. Scratchpad System

**What:** A directory for intermediate work products that persist between conversations but aren't permanent docs. Research notes, design explorations, comparison matrices, working drafts.

**Where:** `docs/scratchpad/` (already exists with research files from this session)

**Convention:**
- Each file named by topic: `mud_phase0_assessment.md`, `scaffold_design_options.md`
- Files include a header with creation date and purpose
- No formal lifecycle — create when needed, delete when absorbed into a real doc
- Lightweight text headers, no YAML frontmatter (add structure only when there's tooling to consume it)

**Discovery mechanism:** Add a note to CLAUDE.md guide index: "Scratchpad (`docs/scratchpad/`): intermediate work products — research, drafts, explorations. Check here for context from recent work."

**Files:**
- Add one line to CLAUDE.md guide index table

---

### 3. Document Cross-References & Sync Mechanism

**What:** A system to prevent documents from drifting out of sync. Three components working together.

**Component A — Cross-reference headers:** Each document that has relationships gets a `Related:` line at the top listing what else might need updating when this doc changes. Placed at top (writer-oriented, not reader-oriented).

Example for `docs/architecturemud.md`:
```
Related: LLMud/VISION.md (research context), CLAUDE.md §Guide Index (if adding phases/skills), docs/PIPELINE.md (if changing backend phases)
```

**Component B — Behavioral rule in CLAUDE.md §10:** Sets intent — Claude understands *why* sync matters.

> After modifying any file in `docs/` or `LLMud/`, check the `Related:` line at the top. For each listed document, assess whether your change requires a corresponding update. If yes, make the update in the same conversation. Updating related docs is always in scope — you do not need separate permission.

The explicit "always in scope" permission addresses Claude's tendency to avoid "scope creep" by not touching files it wasn't asked about — a root cause of doc drift.

**Component C — PostToolUse hook (NEW from research):** Research showed that behavioral rules alone fail due to context window attrition. By message 30, the rule has been pushed out of active context. A path-filtered PostToolUse hook solves this by injecting a just-in-time reminder at the moment of edit.

Design:
1. Match on `Write|Edit` tool uses only
2. Check if the edited file path contains `docs/`, `LLMud/`, or `CLAUDE.md`
3. If yes, read first 5 lines looking for a `Related:` header
4. Inject the Related: line as `additionalContext` (e.g., "DOC SYNC REMINDER: This file lists Related: VISION.md, CLAUDE.md, PIPELINE.md — check if your change requires updates to those files.")
5. For non-doc files, exit silently

This is not noisy (only fires for doc edits) and not fragile (it's `head -5 | grep`). Use BOTH the rule AND the hook: rule sets intent, hook survives context attrition.

**Files:**
- Add `Related:` headers to: `docs/architecturemud.md`, `LLMud/VISION.md`, `CLAUDE.md`, `docs/PIPELINE.md`, `docs/ANALYSIS.md`, `docs/PROBES.md`
- Add document sync rule to CLAUDE.md §10
- Add PostToolUse hook to `.claude/settings.json`

---

### 4. CLAUDE.md Refinement

**What:** Targeted improvements to CLAUDE.md. Currently 134 lines — within the recommended 100-200 range. Goal: stay under ~165 lines after additions.

**Changes:**

a) **Add scratchpad to guide index** (from deliverable 2)

b) **Add document sync rule to §10** (from deliverable 3, Component B)

c) **Expand §10 with ambient behavioral patterns** — the critical patterns that need to be always-active, in 1-2 line bullets:
  - Check `docs/scratchpad/` for context from recent conversations before starting new work
  - Research before change — read actual code, understand actual state, then decide
  - Watch for attractor patterns: over-abstracting, over-engineering for hypothetical requirements, adding error handling for impossible cases
  - Sunk cost awareness — replace bad code, don't patch around it. We control everything.
  - After modifying docs, check Related: headers for sync needs (updating related docs is always in scope)

d) **Consolidate §12 (Certainty Protocol) with /cdd skill:** Keep brief principle in §12 ("Before non-trivial implementation, assess uncertainty. Run `/cdd` for the structured procedure.") Move the detailed procedure to the skill. Avoids duplication.

e) **Add compact instruction for scratchpad:** "When compacting, also preserve: any active scratchpad file names and their purpose."

f) **Add skills to skills table:** `/cdd`, `/devils-advocate`, `/competitive-design`, `/review`

g) **Add session-end review note to §10:** "At the end of larger sessions, review what approaches worked or didn't and save insights to development feedback memories."

**Estimated impact:** ~15 lines added, ~5 lines removed (§12 consolidation) = net +10 lines → ~144 total. Under budget.

**Files:**
- Edit `CLAUDE.md`

---

### 5. Workflow Skills (`.claude/skills/`)

**What:** Four new skills that formalize thinking patterns as invocable commands. These are lightweight structured prompts — not complex workflows. Each produces concrete artifacts (tables, verdicts, comparisons), which is what makes them effective vs. performative.

These are runnable by the user directly OR by subagents on pieces of a plan.

**Skill 1: `/cdd` — Uncertainty Assessment**
File: `.claude/skills/cdd/SKILL.md`

Reframed from "Certainty-Driven Development" — the core mechanism is asking "what are you uncertain about?" This is a fundamentally different cognitive task than "what's the answer?" An LLM that pattern-matches toward confident-sounding answers CAN honestly assess where its confidence is thin, because uncertainty assessment doesn't trigger the same overconfidence pathways. It creates a pause where the LLM evaluates what it knows vs what it's guessing, BEFORE it papers over gaps with fake confidence.

```markdown
---
name: cdd
description: Uncertainty assessment before implementation — identify what you know, what you're guessing, and what to verify
---

# Uncertainty Assessment (CDD)

Pause before implementing. Assess what you're certain about, what you're uncertain about, and what to do about the gaps. This is a metacognitive practice, not a methodology — it works because "what are you uncertain about?" activates honest self-assessment instead of fake confidence.

## Invocation
`/cdd [task description]` or `/cdd` (will ask for task)

## Workflow

ultrathink

### 1. Understand the Task
Read the task description. If no task provided, ask.

### 2. Identify Changes
List every file that will be modified or created.

### 3. Assess What You Know and Don't Know

For each file/change, assess honestly:
- **High confidence**: Clear what to do, have read the code, no ambiguity
- **Medium confidence**: Understand the goal but need to verify assumptions
- **Low confidence**: Uncertain about approach, multiple valid options, or haven't read the code

Separately: what are you MOST certain about? What are you LEAST certain about? These are different questions worth answering independently.

### 4. Report

| File | Change | Confidence | What I'm uncertain about |
|------|--------|------------|--------------------------|
| ... | ... | High/Med/Low | ... |

For any Medium/Low items:
- What would raise confidence? (read a file, ask user, prototype)
- What's the risk if the assumption is wrong?
- Pre-mortem: "Assume this change fails — what went wrong?" (activates a different reasoning mode than "what could go wrong?")

### 5. Recommend
Either: "Ready to implement" or "Need to resolve [items] first"

If recommending to proceed, note any Medium items that should be verified during implementation rather than blocking on them.
```

**Skill 2: `/devils-advocate` — Challenge an Approach**
File: `.claude/skills/devils-advocate/SKILL.md`

Research identified the "performative devil's advocacy" problem: LLMs default to surface-level "on the other hand..." disagreement. Fix: require concrete failure scenarios, use ultrathink, structure around assumption audit rather than freeform criticism.

```markdown
---
name: devils-advocate
description: Challenge a design or approach — find real weaknesses, not performative objections
---

# Devil's Advocate Review

Genuinely argue against the current approach. The goal is to escape attractor basins — the default patterns Claude gravitates toward — and find REAL problems, not perform criticism theater.

## Rules
- Every objection must include a concrete failure scenario with specific consequences. If you can't construct a real failure scenario, the objection isn't real — drop it.
- Do not list weaknesses that sound critical but have no practical impact on THIS project.
- You are a skeptical reviewer who has seen similar projects fail. What killed them?

## Invocation
`/devils-advocate [topic or approach to challenge]`

## Workflow

ultrathink

### 1. State the Current Approach
Summarize what's being proposed (from context, plan file, or user description).

### 2. Assumption Audit
List the top 3-5 assumptions the current approach relies on.
For each:
- What happens if this assumption is wrong?
- How would we detect it's wrong? (Early or late?)
- Concrete failure scenario: "[Specific thing] happens, causing [specific consequence]"

### 3. Steel-Man the Opposition
What's the strongest case for doing something COMPLETELY different?
Not a minor variant — a fundamentally different approach.
Why might that approach handle the failure scenarios above better?

### 4. Sunk Cost Check
Is any part of this approach continuing because we already started it, not because it's the best path forward? Be specific — name the component.

### 5. Simplicity Check
What's the simplest version that delivers the same value?
What could be deleted and nobody would notice?

### 6. Verdict
One of:
- "Current approach holds — the failure scenarios are manageable because [reasons]"
- "Consider changing [specific aspect] — failure scenario [X] is likely and costly"
- "Fundamentally reconsider — [alternative] handles [specific failures] better"
```

**Skill 3: `/competitive-design` — Generate & Compare Approaches**
File: `.claude/skills/competitive-design/SKILL.md`

```markdown
---
name: competitive-design
description: Generate 2-3 genuinely different approaches to a problem and compare them
---

# Competitive Design

Generate multiple distinct approaches before committing to one.
Each must be genuinely different — not variants of the same idea.

## Invocation
`/competitive-design [problem statement]`

## Workflow

ultrathink

### 1. Define the Problem
State the problem clearly. List actual constraints (from code, user, architecture).
Distinguish actual constraints from assumed ones.

### 2. Generate Approaches (2-3)
For each approach:
- **Name**: descriptive label
- **Core idea**: one sentence
- **How it works**: brief description
- **Strengths**: what it does well
- **Weaknesses**: where it struggles
- **Complexity**: low / medium / high

### 3. Compare Against Constraints
| Constraint | Approach A | Approach B | Approach C |
|-----------|-----------|-----------|-----------|
| [actual constraint] | how it handles it | ... | ... |

### 4. Recommend
Pick the winner. Document WHY the others were rejected — this prevents re-discovering and re-evaluating them in future conversations.

Save the comparison to `docs/scratchpad/` if the decision is significant.
```

**Skill 4: `/review` — Architecture Review Through a Lens**
File: `.claude/skills/review/SKILL.md`

Five lenses chosen for this project's actual failure modes. Testability folded into deliverability as a question. Context-survivability (unique to AI dev) deferred to v2 after using the initial five.

```markdown
---
name: review
description: Review architecture or code through a specific analytical lens
---

# Architecture Review

Review a design, document, or code through a specific analytical lens.
Each lens asks different questions and catches different problems.

## Invocation
`/review [lens] [target]`

Lenses: `onboarding`, `deliverability`, `failure`, `sunk-cost`, `simplicity`

If no lens specified, ask which to apply. Can run multiple lenses sequentially.

## Workflow

ultrathink

## Lenses

### onboarding
"Could a new developer (or new Claude conversation) understand this?"
- Is there a clear entry point?
- Are terms defined or obvious from context?
- Could someone implement this from the doc alone?
- Are there implicit assumptions that should be explicit?

### deliverability
"Can we ship each phase independently and get value?"
- Does each phase produce a working system?
- Are phase boundaries at natural integration points?
- What's the minimum viable version of each phase?
- Can phases be reordered if priorities change?
- How do we know each phase works? What's the verification plan?

### failure
"What breaks and how do we recover?"
- What are the failure modes?
- For each: detection, impact, recovery path
- Are there single points of failure?
- What happens if we're halfway through and need to stop?

### sunk-cost
"Are we doing this because it's needed or because we started it?"
- Which pieces would we build if starting fresh today?
- Is anything being preserved/migrated that could be replaced?
- Are we refactoring code that's about to be replaced?
- Does backward compatibility matter? (Usually no — we control everything.)

### simplicity
"What's the simplest version that delivers the same value?"
- Is every component earning its complexity?
- Are we abstracting for one use case?
- Could we delete something and still achieve the goal?
- Are we solving real problems or hypothetical ones?

## Output Format
For each finding:
- **Issue**: What was found
- **Severity**: Critical / Important / Nice-to-have
- **Recommendation**: Specific action
```

**Files:**
- Create `.claude/skills/cdd/SKILL.md`
- Create `.claude/skills/devils-advocate/SKILL.md`
- Create `.claude/skills/competitive-design/SKILL.md`
- Create `.claude/skills/review/SKILL.md`

---

### 6. VISION.md — Add Software Vision

**What:** The current VISION.md describes the research vision (scaffolds, attractor basins, eudaimonic AI). It does NOT describe what the software looks like, what a user does with it, or how the pieces fit together as a product.

**Approach:** Add a new section — "The Software" — after "Scope Philosophy" (research found this is the best placement: after the philosophical context, before "Why Text Worlds"). Keep the existing research vision intact.

**Content:**
- What a researcher sees (the unified MUD interface — terminal + viz panels)
- What a visitor sees (same interface, fewer commands)
- What a typical research session looks like
- How ConceptMRI and the MUD integrate
- The progression from standalone to integrated

**Phase numbering note:** Three systems exist — VISION.md (5 agent-focused), architecturemud.md (7 interface-focused), DEV_PROCESS.md (5 architecture-focused). Must reconcile before writing this section. Use architecturemud.md as authoritative (most recently reviewed) and add a brief mapping.

**Key principle:** This section describes the EXPERIENCE, not the architecture. Architecture is in `docs/architecturemud.md`. Vision is "what does it feel like to use this?"

**Files:**
- Edit `LLMud/VISION.md` (add ~40-60 lines)

---

### 7. User Stories Document

**What:** Concrete use cases that test whether we understand the vision. Two purposes: (a) verify alignment between human and Claude on what we're building, (b) provide a reference for future conversations to check "does this feature serve an actual use case?"

**Where:** `docs/USER_STORIES.md`

**Format:** Lightweight — no Jira-style acceptance criteria. Each story has: Who, What, Why, Currently, With LLMud.

**Candidate stories:**

Works today:
1. **Explore a polysemy experiment** — researcher loads a session, configures color axes, clicks through clusters, reads AI-generated descriptions
2. **Run a new probe experiment** — researcher designs sentences, runs capture, categorizes outputs, explores results
3. **Run full analysis pipeline** — researcher uses Claude Code to orchestrate the complete probe→capture→categorize→analyze flow (NEW — this works today and was missing)
4. **Investigate a routing anomaly** — researcher notices unexpected cluster composition, drills down to individual sentences, generates hypothesis

Near-term (Phase 0-2):
5. **Temporal basin analysis** — researcher captures expanding-context sequences, tracks basin transitions across generation steps
6. **Cross-session synthesis** — researcher asks Claude Code to compare findings across multiple experiments
7. **Claude Code as analysis runtime** — Claude Code designs probes, runs analysis, labels outputs, and generates hypotheses as a first-class pipeline participant (NEW — Claude Code is the most underrepresented persona)

Aspirational (Phase 4+) — tagged explicitly:
8. **Compare scaffold effects** — researcher runs same probes with different scaffolds, compares basin separation metrics *(requires Phase 4+ agent scaffolding)*
9. **Watch an agent reason in real-time** — visitor connects, sees the MUD terminal showing agent actions, viz panels updating live *(requires Phase 3+ Evennia integration)*
10. **Design a new micro-world** — researcher creates a YAML room config, loads it into Evennia, runs agents through it *(requires Phase 3+ Evennia integration)*

**Files:**
- Create `docs/USER_STORIES.md`

---

## Implementation Order

```
0.  Save this plan            — [DONE]
    ↓
1.  Preserve assessment       — save architecture assessment to scratchpad
    ↓
2.  Scratchpad system         — add to CLAUDE.md guide index
    ↓
3.  Document cross-refs       — add Related: headers, sync rule, PostToolUse hook
    ↓
4.  CLAUDE.md refinement      — ambient patterns in §10, §12 consolidation,
    ↓                           skills table, session-end review
5.  Workflow skills           — create 4 skill files (/cdd, /devils-advocate,
    ↓                           /competitive-design, /review)
6.  VISION.md software vision — add experience-focused section, reconcile phases
    ↓
7.  User stories              — write stories, use as alignment check
```

**Grouping:**
- Item 0: DONE
- Items 1-2: Scratchpad infrastructure (together)
- Items 3-4: Document sync + CLAUDE.md refinement (together, since both edit CLAUDE.md)
- Item 5: Skills (independent, can do in parallel batch)
- Items 6-7: Vision & stories (feed each other, do together)

All deliverables are documentation/config — no application code changes.

---

## Verification

After all deliverables:

1. **Scratchpad test:** `docs/scratchpad/` contains at least the architecture assessment. CLAUDE.md guide index mentions it.
2. **Cross-reference test:** Open each doc with a `Related:` header. For each listed document, verify the relationship is real and bidirectional.
3. **CLAUDE.md coherence:** Read CLAUDE.md end-to-end. Verify it's still under 200 lines (~165 target), guide index is complete, no contradictions with skills.
4. **Hook test:** Edit a doc file. Verify the PostToolUse hook injects the Related: reminder as additionalContext.
5. **Skills test:** In a new conversation, invoke each new skill (`/cdd`, `/devils-advocate`, `/competitive-design`, `/review onboarding`) with a simple test case. Verify it produces structured, non-performative output.
6. **Vision completeness:** A new conversation reading only VISION.md should be able to answer: "What does the software look like? What does a researcher do with it? How do the pieces fit together?"
7. **User stories coverage:** Each non-aspirational story should map to at least one phase in `architecturemud.md`. Aspirational stories should be tagged with their target phase.
8. **Integration test:** Start a fresh conversation. Ask it to plan a small MUD implementation task. Does it: check scratchpad? pick up ambient patterns from §10? use /cdd when appropriate?

---

## What This Plan Does NOT Cover

- **Application code changes** — deliverables are documentation and skill configs, no frontend/backend code
- **MUD architecture changes** — `architecturemud.md` was already reviewed and updated; those changes stand
- **Memory cleanup** — the 20 memory files are well-organized; no action needed
- **CLAUDE.md split into rules files** — `.claude/rules/` has known bugs (issues #16299, #23478). At ~144 lines post-edit, CLAUDE.md is well within range. Revisit if it grows past ~200 lines
- **Post-implementation feedback tracking for skills** — good idea, defer to v2
- **"Context-survivability" review lens** — unique to AI dev, add to /review after using initial five lenses

## Evolution Plan

Skills and ambient patterns are v1. They will evolve through use:
- **Session-end reviews:** At the end of larger sessions, review what worked and what didn't. Save insights to development feedback memories.
- **Skill iteration:** When a skill produces performative or unhelpful output, update the skill file. When a new thinking pattern emerges, consider whether it needs a skill or an ambient rule.
- **Scratchpad:** The place for experimental pattern ideas before they graduate to skills or CLAUDE.md rules.

---

## Research Files

All research that informed this plan is in `docs/scratchpad/`:
- `research_claude_code_practices.md` — CLAUDE.md, skills, hooks, memory best practices
- `research_doc_sync.md` — Document synchronization patterns and PostToolUse hook design
- `research_skill_design.md` — Workflow skill design, granularity, ambient vs invocable
- `research_vision_stories.md` — Vision gaps, user story completeness, persona coverage
- `research_cdd_review_frameworks.md` — CDD, review lenses, devil's advocacy vs established methods
- `research_synthesis.md` — Cross-agent synthesis of all findings
