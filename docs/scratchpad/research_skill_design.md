# Research: Workflow Skill Design Assessment

Created: 2026-03-30
Agent: Workflow Skill Design Research

---

## 1. Are Cognitive Skills a Valid Use of the Skill System?

**YES — HIGH confidence.** Anthropic's official docs explicitly define "reference content" skills (conventions, patterns, domain knowledge) alongside "task content" skills. Our cognitive skills fit squarely in the supported design. The community has examples: 63 design skills collection, thoughtbot audit skills, plan-first patterns.

---

## 2. Keep All Four Skills Separate?

**YES — keep separate.** Each is well under the 500-line/2,000-token recommended limits. The skills serve different decision points:
- `/cdd` — before implementation
- `/devils-advocate` — after converging on a design
- `/competitive-design` — when design space is large
- `/review` — architecture review at phase boundaries

**But resolve the /cdd vs CLAUDE.md §12 redundancy.** The certainty procedure should exist in exactly one place. Replace CLAUDE.md §12 prose with a one-line reference: "Run `/cdd` before non-trivial implementation."

---

## 3. Is the Ambient/Invocable Separation Correctly Drawn?

**YES — the line is correct.** The key test: "Does this pattern need structured output, or just awareness?"
- Attractor escape needs awareness (ambient) → WORKFLOW_PATTERNS.md
- Devil's advocate needs a verdict (skill) → `/devils-advocate`
- Research before change needs awareness (ambient) → WORKFLOW_PATTERNS.md
- Certainty assessment needs a table (skill) → `/cdd`

**But WORKFLOW_PATTERNS.md won't be auto-read.** It's listed in the guide index, but Claude doesn't automatically read every referenced doc at startup. Critical ambient patterns need 1-2 line summaries directly in CLAUDE.md (or in a `.claude/rules/` file if supported and stable).

---

## 4. Making Devil's Advocate Actually Work (Not Performative)

Two highest-impact changes for genuine critique:

**A. Add `ultrathink` keyword** to `/devils-advocate` and `/review` skill content. This activates extended thinking, giving Claude more processing space for genuine reasoning rather than surface-level responses.

**B. Add anti-performativity instructions** to `/devils-advocate`:
> "Every criticism must include a specific failure scenario and concrete consequence — if you can't construct one, the objection isn't real. Do not list weaknesses that sound critical but have no practical impact on this specific project."

Research on sycophancy mitigation in LLMs confirms that explicit instructions to "disagree when warranted" and role assignment ("you are a skeptical reviewer") improve genuine critique quality.

---

## 5. Are the Five Review Lenses Right?

**Our five lenses are well-chosen** for this project's actual failure modes (onboarding, deliverability, failure, sunk-cost, simplicity).

Consider adding two more:
- **testability** — "How do we know this works? What's the verification plan?" (Catches the common failure of building something untestable)
- **context-survivability** — "What survives a conversation boundary? If a new Claude conversation picks this up, what will it understand vs. lose?" (Unique to AI-assisted development)

These could be added in v2 after using the initial five.

---

## 6. Will WORKFLOW_PATTERNS.md Actually Shape Behavior?

**Mixed — MEDIUM confidence.**

It will be useful as a **user-invoked reference** ("read WORKFLOW_PATTERNS.md before starting"). It will NOT automatically shape behavior because:
- Claude doesn't auto-read guide index entries
- By the time Claude is deep in a task, it won't remember to check the cycle steps
- Abstract descriptions ("Assess: Check scratchpad for prior context") don't trigger action

**Make the development cycle steps concrete with actual commands/paths:**
```
- Assess: `ls docs/scratchpad/` + read any files related to this task
- Design: Run `/cdd [task]`. If confidence < High on any item, use plan mode.
- Document: Update the design doc in `docs/` BEFORE writing code.
```

---

## Summary of Certainty Levels

| Decision | Certainty | Notes |
|----------|-----------|-------|
| 4 separate skills | HIGH | Well-scoped, under token limits |
| Cognitive skills valid | HIGH | Matches Anthropic patterns |
| Ambient/invocable split | HIGH | Correctly drawn |
| /cdd design | HIGH | Resolve CLAUDE.md §12 duplication |
| /devils-advocate design | MEDIUM | Needs anti-performativity prompts + ultrathink |
| /competitive-design design | HIGH | Clean structure |
| /review lenses (5) | HIGH | Consider adding testability + context-survivability later |
| WORKFLOW_PATTERNS.md effectiveness | MEDIUM | Needs concrete commands, not abstract descriptions |
