---
name: review-scope
description: Is everything earning its complexity? Sunk cost and simplicity check.
---

# Scope Review

Evaluate whether every piece of the design is earning its place. Combines simplicity ("what could be simpler?") and sunk cost ("are we keeping this because it's good or because we started it?").

ultrathink

## Rules
- Every finding must name a specific component, section, or decision
- "Could be simpler" is not a finding. "The OOB event protocol (§8) defines 8 event types for Phase 2+ but Phase 1 only needs 0 — this complexity is speculative and could be deferred entirely" is a finding
- The project controls all software and data. There are no external users, no backward compatibility requirements. Refactoring is cheap. Use this as context when evaluating scope.

## Questions

1. Which pieces would we build if starting fresh today? What would we skip?
2. Is anything preserved because we already started it, not because it's the best approach?
3. Could we delete a section/component and still achieve the goal?
4. Are we solving real problems or hypothetical future ones?
5. Is every abstraction earning its complexity? Or are some one-use wrappers?
6. Are there sections marked "deferred" or "Phase N+" that are influencing earlier phase design unnecessarily?

## Output Format

| Finding | Component | Severity | Recommendation |
|---------|-----------|----------|----------------|
| [specific issue] | [§ ref] | Critical / Important / Minor | [specific action — usually "defer" or "delete"] |
