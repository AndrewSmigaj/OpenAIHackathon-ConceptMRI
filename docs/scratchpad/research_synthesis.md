# Research Synthesis: Scaffolding Plan Assessment

Created: 2026-03-30
Source: 5 parallel research agents + human feedback on findings

---

## Verdict: Plan is directionally correct, needs these refinements

### Actionable changes (strong consensus across agents)

**1. Add a PostToolUse hook for document sync.**
The behavioral rule alone fails because of context window attrition — by message 30, Claude has forgotten the rule exists. A path-filtered hook on Write|Edit that reads `Related:` headers from doc files and injects a reminder is lightweight and solves the root cause. Use both: rule sets intent, hook provides the just-in-time nudge.

**2. Critical ambient patterns must go in CLAUDE.md, not just WORKFLOW_PATTERNS.md.**
Guide index entries are NOT auto-loaded. WORKFLOW_PATTERNS.md is reference-only — Claude won't read it unless prompted. The 3-5 most important behavioral rules need 1-2 line summaries in CLAUDE.md §10 directly. Adds ~10 lines (total ~155, under 200 limit).

**3. Resolve the /cdd vs CLAUDE.md §12 duplication.**
The uncertainty assessment procedure should exist in one place. Replace §12 prose with a reference to the skill.

**4. Restructure /devils-advocate to avoid performative critique.**
LLMs default to surface-level "on the other hand..." disagreement. Fix: require concrete failure scenarios with specific consequences. If you can't construct a real failure scenario, the objection isn't real. Add ultrathink keyword. Structure around assumption audit, not freeform criticism.

**5. Add to sync rule: "Updating related docs is always in scope."**
Claude avoids touching files it wasn't asked about ("scope creep" avoidance). The rule must explicitly give permission to update related docs after any doc edit.

**6. Two missing user stories: "Run full analysis pipeline" (works today) and "Claude Code as analysis runtime."**
Claude Code is the most underrepresented persona — it's a first-class pipeline consumer with 6 stages of its own workflow. 3 of 8 proposed stories are aspirational (Phase 4+) and should be tagged as such.

**7. Reconcile phase numbering.**
Three systems: VISION.md (5 agent-focused phases), architecturemud.md (7 interface-focused phases), DEV_PROCESS.md (5 architecture phases). Same project, incompatible numbering. Must reconcile before writing software vision section.

### Reframing: Uncertainty Assessment, not "Certainty-Driven Development"

The agents compared CDD to TDD, risk matrices, and design reviews. This is a category error. CDD is not a development methodology — it's a metacognitive practice.

The core mechanism: asking an LLM "what are you uncertain about?" is a fundamentally different cognitive task than "what's the answer?" An LLM that pattern-matches toward confident-sounding answers CAN honestly assess where its confidence is thin, because uncertainty assessment doesn't trigger the same sycophancy/overconfidence pathways. It creates a pause where the LLM evaluates what it knows vs what it's guessing, BEFORE it papers over gaps with fake confidence.

Useful refinements from the research:
- Separate "how likely am I wrong?" from "how bad is it if I am?" — different questions, both worth asking
- Ask what you're certain about AND uncertain about (not just one direction)
- Pre-mortem framing helps: "Assume this fails — what went wrong?" activates a different mode than "what could go wrong?"

The branded name "CDD" has been kept through two previous renaming attempts (memory: feedback_keep_cdd). The user now notes "uncertainty" may be better framing than "certainty" — this is an evolution of the concept, not a rename.

### What the research confirmed (no changes needed)

- `docs/scratchpad/` is the right location and pattern (not .claude/)
- All 4 skills should stay separate (well under token limits, serve different decision points)
- Cognitive/workflow skills ARE a valid use of the skill system (Anthropic docs confirm)
- The ambient/invocable separation is correctly drawn
- 5 review lenses are well-chosen for this project. Add testability as a question in "deliverability" lens, not a separate lens. Consider "context-survivability" (unique to AI dev) for v2.
- Related: headers at top of docs is the right pattern (oriented toward writer, not reader)
- Don't create MANIFEST.md (creates meta-drift)

### What to defer

- Post-implementation feedback tracking for skills (good idea, v2)
- "Context-survivability" review lens (v2)
- Memory consolidation pass (monitor context budget first, currently ~9-11K tokens)
- `.claude/rules/` directory (has known bugs, don't depend on it)

---

## Research files

All in `docs/scratchpad/`:
- `research_claude_code_practices.md` — CLAUDE.md, skills, hooks, memory best practices
- `research_doc_sync.md` — Document synchronization patterns and the PostToolUse hook design
- `research_skill_design.md` — Workflow skill design, granularity, ambient vs invocable
- `research_vision_stories.md` — Vision gaps, user story completeness, persona coverage
- `research_cdd_review_frameworks.md` — CDD, review lenses, devil's advocacy vs established methods
