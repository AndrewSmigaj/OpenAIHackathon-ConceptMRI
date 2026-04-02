# Research: Claude Code Best Practices Assessment

Created: 2026-03-30
Agent: Claude Code Scaffolding Best Practices

---

## Overall Verdict

**The scaffolding improvement plan is substantially correct.** Five of six areas assessed at HIGH certainty. Three areas need refinements.

---

## 1. CLAUDE.md — HIGH Certainty (Plan is Correct)

- At 134 lines, we are within the 50-200 recommended range. No need to split.
- `.claude/rules/` path-scoped rules have known bugs (issues #16299, #23478) — not reliable yet. Don't depend on them.
- Minor optimization: tighten paragraph-style sections (§11, §12) to bullet points for better adherence. LLMs follow bullet points more consistently than prose paragraphs.

**Recommendation:** Keep CLAUDE.md as-is structurally. Tighten §11 and §12 when editing.

---

## 2. Skills — MEDIUM Certainty (Needs Adjustment)

Thinking/workflow skills are a validated pattern in the community. But:

**Reconsider `/devils-advocate` and `/competitive-design` as skills vs ambient patterns.** These are "think differently" prompts. They work when Claude is told to run them, but they're the skills most likely to produce performative output (going through the motions). The operational skills (`/analyze`, `/server`) work because they have concrete steps (curl commands, API calls). Cognitive skills work best when they produce concrete artifacts (tables, verdicts).

- `/cdd` — **KEEP as skill**. Produces a concrete table. Clear trigger point.
- `/review` — **KEEP as skill**. Produces structured findings per lens. Clear trigger point.
- `/devils-advocate` — **KEEP as skill but add anti-sycophancy measures.** Role assignment, ultrathink keyword, requirement for concrete failure scenarios.
- `/competitive-design` — **KEEP as skill.** Produces comparison matrix. Clear trigger point.

**Resolve `/cdd` vs CLAUDE.md §12 duplication.** The certainty procedure should exist in one place. Replace §12 prose with: "Before non-trivial implementation, run `/cdd`. See `.claude/skills/cdd/` for the full procedure."

**Add trigger conditions to skill descriptions.** Not just "what it does" but "when to use it": "Use when task involves 3+ files or any architectural change."

---

## 3. Memory — HIGH Certainty (Plan is Correct)

- Auto Dream feature now automatically prunes stale memories and resolves contradictions. Manual cleanup less necessary.
- 20 memory files at ~3-5K tokens is within budget.
- No action needed.

---

## 4. Hooks — HIGH Certainty (Plan is Correct)

- Minimal hooks approach validated. The current two hooks (block python3, SessionStart reminder) are textbook good hooks.
- One optional addition: PostToolUse auto-format hook (run Black/Prettier after file edits). Low priority.
- Doc-sync hook: see the doc sync research agent's findings — a path-filtered PostToolUse hook for doc edits is actually viable and recommended.

---

## 5. Scratchpad — HIGH Certainty (Plan is Correct)

- `docs/scratchpad/` is the community-validated pattern. An open Claude Code feature request (#21248) confirms the gap exists in the tooling.
- Keep it in `docs/`, not `.claude/`. Config vs content distinction.
- Lightweight text headers, not YAML frontmatter. Add structure only when there's tooling to consume it.

---

## 6. NEW FINDING: WORKFLOW_PATTERNS.md Has a Loading Problem — MEDIUM Certainty

Reference docs listed in CLAUDE.md guide index are **NOT auto-loaded** at startup. They're only read when Claude decides to look at them. This means "ambient patterns" in WORKFLOW_PATTERNS.md won't actually be ambient.

**Options:**
A. Put the most critical ambient patterns (2-3 lines each) directly in CLAUDE.md §10
B. Use `.claude/rules/workflow.md` (no path frontmatter = global loading) — BUT rules have known bugs
C. Accept that WORKFLOW_PATTERNS.md is a reference doc, not ambient, and design accordingly

**Recommended: Option A.** Add 3-5 bullet points of the most critical patterns to CLAUDE.md §10. Keep the full document as reference. This adds ~10 lines to CLAUDE.md (total ~155, still under 200).

---

## 7. NEW FINDING: Context Budget Awareness — MEDIUM Certainty

All CLAUDE.md + memory + skill metadata loads at startup. Current estimate: ~9-11K tokens. Recommended max: ~10K.

Adding 4 skills (descriptions only load at startup, full content loads on invocation) is fine. But if we also add 10+ lines to CLAUDE.md, we should do a consolidation pass on memory files to stay within budget. Not urgent but worth tracking.

---

## Summary

| Area | Certainty | Action Needed |
|------|-----------|---------------|
| CLAUDE.md structure | HIGH | No split needed. Tighten §11/§12 to bullets. |
| Skills as thinking tools | MEDIUM | Keep all 4, add anti-performativity to /devils-advocate |
| Memory | HIGH | No action |
| Hooks | HIGH | Add doc-sync PostToolUse hook (from sync research) |
| Scratchpad | HIGH | docs/scratchpad/ confirmed correct |
| WORKFLOW_PATTERNS.md loading | MEDIUM | Put critical ambient patterns in CLAUDE.md §10 |
| Context budget | MEDIUM | Track, consolidate memory if needed after changes |
