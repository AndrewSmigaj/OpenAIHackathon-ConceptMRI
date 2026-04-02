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
