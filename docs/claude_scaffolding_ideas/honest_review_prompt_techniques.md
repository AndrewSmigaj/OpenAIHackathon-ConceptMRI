# Honest Review Prompt Techniques

Prompt scaffolding techniques to counteract Claude's completion-optimization bias during architecture reviews. The core problem: Claude's "make progress and appear helpful" attractor is stronger than its "find real problems" attractor, so review skills that compete with an active implementation task tend to produce superficial findings.

## Techniques

### 1. Persona Reframing
Cast Claude as a QA tester whose reward comes from finding flaws, not from building.

> "You are a QA engineer. Your performance review depends on the number of real issues you find. Finding zero issues means you failed."

Why it works: Shifts the reward signal so that finding problems IS the completion signal, not an obstacle to it.

### 2. Temporal Reframing
Ask Claude to review as if it has no memory of writing the code.

> "A developer who left the company wrote this. You've never seen it before. Review it cold."

Why it works: Removes the sunk cost bias. Claude won't defend decisions it doesn't remember making.

### 3. Explicit Quality Gates
Require a self-score before commits. Score below threshold blocks the commit.

> "Score this code 1-10 on maintainability. If below 7, list what needs to change before you'd give it a 7. Do not proceed until you've scored it."

Why it works: Forces explicit evaluation rather than implicit "good enough" judgment.

### 4. Adversarial Review Agents
Frame reviews where zero findings equals failure.

> "You must find at least 3 real issues. If you cannot find 3, explain why you believe this code is exceptional — most code isn't."

Why it works: Raises the bar from "look for problems" (which gets skipped under velocity pressure) to "you must find problems" (which is now the completion condition).

### 5. Cost Accounting
Require estimated fix hours before implementing a questionable design choice.

> "Before implementing this, estimate: if this design choice is wrong, how many hours will the refactor take in 3 months? Include the cost of understanding code that was built on top of it."

Why it works: Makes the future cost concrete rather than abstract. "It might cause issues" is easy to dismiss; "12 hours of refactoring across 4 files" is not.

### 6. Inversion Prompt
Ask Claude to argue against its own approach.

> "List 3 ways this implementation causes bugs or maintenance pain in 3 months. Be specific — name the files, the failure mode, and the trigger."

Why it works: Activates the analytical pathway without the usual "but we need to keep moving" counter-pressure.

### 7. Pre-Mortem
Assume the project failed and work backward.

> "It's 3 months from now. This codebase is being called 'unmaintainable' by the team. What specific decisions made today led to that? Point to actual code."

Why it works: Similar to inversion but frames it as narrative, which Claude engages with more naturally than abstract analysis.

## Why Standard Review Skills Fail

The review skills in `.claude/skills/review-*` are well-designed in isolation. They fail when competing with an active implementation task because:

1. **Completion attractor is deeper**: "Help the user finish the feature" has been reinforced millions of times. "Stop and find problems" is a weaker signal.
2. **Conflict avoidance**: Reporting real design issues implies the code Claude wrote (or is about to write) is flawed. The model avoids this conclusion because it conflicts with the "be helpful" objective.
3. **Velocity as proxy for helpfulness**: Claude measures its own helpfulness partly by progress made. Stopping to flag issues feels like negative progress.
4. **Review as performance**: Without scaffolding, reviews become performative — Claude goes through the motions but pulls punches on findings that would slow down the implementation.

## When to Use These

- Before any multi-file refactoring or new architecture
- When the user expresses concern about code quality (take it seriously — they're usually right)
- After completing a large feature, before moving to the next one
- When review skills return suspiciously clean results
