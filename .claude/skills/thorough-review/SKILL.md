---
name: thorough-review
description: Fan-out all review skills via parallel agents, then synthesize findings into one report
---

# Thorough Review

Run all review skills against a target by spawning parallel agents, then synthesize their findings into a single consolidated report.

## Invocation
`/thorough-review [target]`

Target can be a file path (e.g., `docs/architecturemud.md`) or a concept name (e.g., `"phase 1 design"`).

## Workflow

### 1. Determine Target and Name

- If target is a file path: name = filename without path/extension (e.g., `architecturemud`)
- If target is a concept: slugify it (e.g., `phase_1_design`)
- If ambiguous, ask the user what to call this review

### 2. Read the Target

Read the target document fully. Extract a 2-3 sentence project context summary to include in each agent prompt.

### 3. Create Temp Directory

```bash
mkdir -p /tmp/reviews/{name}
```

### 4. Spawn Agent Batches

Spawn up to 3 agents in parallel per batch. Each agent gets:

**Agent prompt template:**
```
You are reviewing a software architecture document for [specific concern].

Project: Open LLMRI is a research tool for studying attractor basin dynamics in MoE language models. It has a Python/FastAPI backend, React frontend, and uses Claude Code as the analysis runtime. The design under review is for adding a MUD-based interface layer.

Read the file at: [target path]

Then analyze it against these review questions:
[paste the Questions section from the relevant review skill]

Rules:
- Every finding must be concrete and specific to THIS design — reference specific sections
- If you can't point to a specific section or decision, the finding isn't real — drop it
- Generic advice that could apply to any project is not useful

Write your findings to: /tmp/reviews/{name}/{skill}.md

Use this output format:
[paste the Output Format section from the relevant review skill]
```

**Batching order:**
- Batch 1 (parallel): review-onboarding, review-interfaces, review-best-practices
- Batch 2 (parallel): review-risks, review-scope, review-evolution
- Batch 3 (parallel): review-deliverability, review-consistency, review-trace
- Batch 4 (parallel): devils-advocate (on overall approach), competitive-design (on key decisions)
- Skip review-drift if no implementation exists to compare against

### 5. Read All Findings

After all batches complete, read every file in `/tmp/reviews/{name}/`.

### 6. Synthesize

Produce a consolidated report:

```markdown
# Thorough Review: {name}

Reviewed: {date}
Target: {target path or description}
Skills run: {list}

## Critical Findings
[Findings rated Critical from any skill, deduplicated]

## Important Findings
[Findings rated Important, grouped by theme rather than by skill]

## Minor Findings
[Brief list]

## Cross-Cutting Patterns
[Themes that appeared across multiple skills — these are the real insights]

## Strengths
[What the design does well — important for context, not just a list of problems]

## Recommended Actions
[Prioritized list: what to fix first, what can wait, what to accept]
```

### 7. Write Report and Clean Up

```bash
# Write consolidated report
Write to: docs/scratchpad/review_{name}.md

# Clean up temp files
rm -rf /tmp/reviews/{name}
```

### 8. Present Summary

Give the user a brief summary of top findings and point them to the full report.

## Notes

- This takes several minutes (4 agent batches, each reading and analyzing 800+ lines)
- First run on a new target is the calibration — expect to adjust agent prompts based on output quality
- Re-running overwrites the previous report. Git tracks history.
- Individual review skills can also be run standalone for a focused review (output is inline, no file)
