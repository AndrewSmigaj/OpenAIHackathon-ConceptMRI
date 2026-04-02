---
name: review-evolution
description: What's locked in by this design vs. what stays flexible? Cost of being wrong about the future?
---

# Evolution & Flexibility Review

Evaluate what this design locks in and what it leaves open. Every design decision is a bet on the future — some bets are cheap to reverse, others are expensive.

ultrathink

## Rules
- Every finding must name a specific decision and what it locks in
- "Could be more flexible" is not a finding. "Choosing xterm.js for the terminal (§7) locks us into a browser-based terminal emulator — if we later need SSH access for remote MUD clients, this would require a parallel implementation" is a finding
- Distinguish reversible decisions (can change cheaply later) from irreversible ones (would require significant rework)

## Questions

1. For each major design decision: how hard is it to change later? What would have to be rewritten?
2. What assumptions about the future does this design bake in? List them explicitly.
3. If those assumptions are wrong, what's the cost? Which assumptions are the most expensive to be wrong about?
4. Which components are easy to swap (behind clean interfaces) vs. deeply coupled (touching everything)?
5. Are we making irreversible decisions where reversible ones would do?
6. Does the phased approach allow changing direction mid-stream, or does Phase 1 commit us to a specific Phase 3?

## Output Format

| Decision | What it locks in | Reversibility | Cost if wrong | Recommendation |
|----------|-----------------|---------------|---------------|----------------|
| [specific decision, § ref] | [what becomes hard to change] | Easy / Medium / Hard | [specific consequence] | [defer, accept, or mitigate] |
