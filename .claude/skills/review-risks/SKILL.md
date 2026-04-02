---
name: review-risks
description: Failure mode analysis — what breaks, how do you detect it, what's the blast radius, how do you recover?
---

# Risk & Failure Mode Review

Systematically identify what can go wrong, how you'd know, and what happens when it does.

ultrathink

## Rules
- Every failure mode must be specific: "[Component X] fails when [condition] because [mechanism], causing [consequence]"
- Generic risks like "performance could be an issue" are not findings. "The dataset viewer loads all session data into memory (§5.A) — with 84 sessions this could be 500MB+ and freeze the tab" is a finding
- Rank by: likelihood x impact. A rare catastrophic failure and a common minor annoyance are both worth flagging, but differently

## Questions

1. For each component or interface: what are the failure modes?
2. For each failure mode: how do you detect it? Early or late?
3. What's the blast radius? Does one component failing cascade to others?
4. What's the recovery path? Restart? Retry? Manual intervention?
5. Are there single points of failure? What has no fallback?
6. What happens if you're halfway through implementation and need to stop? Is partial implementation safe?
7. Are there race conditions, timing dependencies, or ordering assumptions?

## Output Format

| Failure Mode | Component | Likelihood | Impact | Detection | Recovery | Severity |
|-------------|-----------|-----------|--------|-----------|----------|----------|
| [specific failure] | [§ ref] | High/Med/Low | High/Med/Low | [how you'd know] | [what to do] | Critical/Important/Minor |
