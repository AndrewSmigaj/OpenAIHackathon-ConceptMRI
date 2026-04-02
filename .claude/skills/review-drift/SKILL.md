---
name: review-drift
description: Does the implementation match the design? What was built, dropped, or changed?
---

# Design Drift Review

Compare a design document against the actual implementation. Designs drift from code and code drifts from designs — both directions matter.

ultrathink

## Rules
- Every finding must cite a specific design section AND a specific code location (or absence)
- "Implementation differs from design" is not a finding. "§7.C specifies command dispatch via simple functions but the actual code in frontend/src/commands/ uses a CommandRegistry class pattern — the design should be updated or the code simplified" is a finding
- Drift isn't always bad. Legitimate evolution (design improved during implementation) should be noted and the design doc updated. Accidental drift (forgot the design, did something different) should be flagged for correction.
- If the design includes quantitative claims (line counts, file counts, endpoint counts), verify them against the actual code. Stale numbers erode trust in the document.

## Prerequisites
This skill requires both a design doc AND existing implementation to compare against. If there's no implementation yet, this skill doesn't apply — use other review skills instead.

## Questions

1. For each major component in the design: does corresponding code exist? Where?
2. What was built that wasn't in the design? Is it a good addition or scope creep?
3. What was designed but never built? Is it still needed or should the design be trimmed?
4. Where did the implementation deviate from the design? Was this deliberate (better approach found) or accidental?
5. Are there decisions embedded in code (naming, structure, patterns) that should be reflected back in the design doc?
6. Does the design doc's phase status match reality? Are phases marked "done" actually done?

## Output Format

| Design Section | Code Location | Status | Notes |
|---------------|--------------|--------|-------|
| [§ ref, component] | [file path or "not implemented"] | Match / Evolved / Drifted / Missing | [what changed and whether design or code should be updated] |
