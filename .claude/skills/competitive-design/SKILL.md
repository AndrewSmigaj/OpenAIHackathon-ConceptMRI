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
