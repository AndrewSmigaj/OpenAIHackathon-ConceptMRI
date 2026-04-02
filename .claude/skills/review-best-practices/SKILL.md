---
name: review-best-practices
description: Does the design follow established software engineering principles? Separation of concerns, coupling, error handling, API design.
---

# Best Practices Review

Evaluate the design against established software engineering principles. Not every principle applies to every project — flag only violations that would cause real problems in THIS design.

ultrathink

## Rules
- Every finding must explain the CONCRETE consequence for this project, not just cite the principle
- "Violates single responsibility" is not a finding. "The MUD command handler (§7.C) both parses command syntax AND updates visualization state — if command parsing logic changes, viz state management has to be retested, and vice versa" is a finding
- Principles are tools, not laws. If a violation is the right tradeoff for this project, say so and explain why.

## Principles to Check

### Separation of Concerns
- Does each component have one clear responsibility?
- Are concerns mixed in ways that make testing or modification harder?
- Could you explain what each component does in one sentence?

### Coupling & Cohesion
- Are modules loosely coupled? Can you change one without changing others?
- Is related functionality grouped together (high cohesion)?
- Where are the tightest couplings? Are they necessary or accidental?

### Interface Segregation
- Are interfaces minimal? Do consumers depend only on what they use?
- Are there "god objects" or "god contexts" that everything depends on?

### Error Handling
- Are error paths defined at component boundaries?
- Is there a graceful degradation strategy?
- Are error contracts explicit (what errors can each interface produce)?

### State Management
- Is state ownership clear? (Who owns what data, who can modify it)
- Are there shared mutable state risks?
- Could race conditions occur? (Especially with async operations)

### API & Command Design
- Do endpoints/commands follow consistent conventions?
- Is naming predictable? Could a user guess the command for a new operation?
- Are similar operations handled similarly?

### Cross-Cutting Concerns
- Logging, validation, auth — handled systematically or ad-hoc?
- Are there patterns that should be consistent but aren't?

### Dependency Direction
- Do dependencies flow toward stability? (Stable core, volatile periphery)
- Are there circular dependencies?
- Could a dependency be inverted to improve flexibility?

## Output Format

| Principle | Finding | Component | Impact | Recommendation |
|-----------|---------|-----------|--------|----------------|
| [which principle] | [specific violation and concrete consequence] | [§ ref] | Critical / Important / Minor | [specific action] |
