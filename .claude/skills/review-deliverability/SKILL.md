---
name: review-deliverability
description: Can phases ship independently with value? Are boundaries at natural integration points?
---

# Deliverability Review

Evaluate whether the implementation plan can be delivered incrementally, with each phase producing a working system that provides value.

ultrathink

## Rules
- Every finding must reference a specific phase, task, or dependency in the target
- Don't flag theoretical reordering issues — flag real ones where the doc shows Phase N depending on Phase N+1
- "Could be more granular" is not a finding. "Phase 2 tasks A-G are listed as one block but A-D are Evennia-independent while E-G require it, so they should be separate sub-phases" is a finding

## Questions

1. Does each phase produce a working system? What can you demo after each phase?
2. Are phase boundaries at natural integration points, or do they cut across concerns?
3. What's the minimum viable version of each phase? Could any phase be trimmed further?
4. Can phases be reordered if priorities change? What are the hard dependencies?
5. How do we verify each phase works? Is there a test plan or acceptance criteria?
6. Are there tasks that block everything else? What's the critical path?

## Output Format

| Finding | Phase/Task | Severity | Recommendation |
|---------|-----------|----------|----------------|
| [specific issue] | [Phase N, Task X] | Critical / Important / Minor | [specific action] |
