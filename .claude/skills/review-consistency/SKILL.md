---
name: review-consistency
description: Do all the parts agree with each other? Cross-document and internal consistency.
---

# Consistency Review

Check whether the design is internally consistent and agrees with related documents. Inconsistencies are where bugs hide — the code follows one doc while the test follows another.

ultrathink

## Rules
- Every finding must cite two specific things that disagree (section vs section, doc vs doc, example vs schema)
- "Naming could be more consistent" is not a finding. "§3.A calls it 'load session' but §7.D calls the same state 'activeSessionId' and the API calls it 'session_id' — three names for one concept" is a finding
- Read the Related: header at the top of the target doc to find linked documents to check against

## Questions

1. Are the same concepts called the same thing everywhere? Check across sections and across related docs.
2. Do examples match their schemas? If §9 shows a YAML example, does it conform to the format described in §9.A?
3. Are phase/section numbering references consistent? Does "Phase 2" mean the same thing everywhere?
4. Do decision rationales in one section contradict constraints or requirements stated elsewhere?
5. Are there repeated descriptions of the same thing that have drifted apart?
6. If related documents exist (check Related: header), do they agree on shared concepts?

## Output Format

| Inconsistency | Location A | Location B | Severity | Recommendation |
|---------------|-----------|-----------|----------|----------------|
| [what disagrees] | [§ or doc reference] | [§ or doc reference] | Critical / Important / Minor | [which is correct, or how to reconcile] |
