---
name: review-onboarding
description: Could a newcomer (developer or new Claude conversation) understand this and implement from it?
---

# Onboarding Review

Evaluate whether a new developer or a fresh Claude Code conversation could understand this design and implement from it without tribal knowledge.

ultrathink

## Rules
- Every finding must reference a specific section, paragraph, or omission in the target
- "Confusing" is not a finding. "Section 7.C references VizConfigContext but the shape isn't defined until 7.D, and a reader following top-down order won't know what properties exist" is a finding
- Test by asking: if I deleted the conversation history and started fresh, what would I get stuck on?

## Questions

1. Is there a clear entry point and reading order? Can someone know where to start?
2. Are key terms defined or obvious from context? Is there a glossary?
3. Are there implicit assumptions that should be explicit? (e.g., "this assumes the backend is running" without saying so)
4. Could someone implement this from the document alone, or does it depend on undocumented knowledge?
5. Are cross-references to other documents clear about what to read and why?
6. Are examples concrete enough to follow? Do code snippets actually work?

## Output Format

| Finding | Section | Severity | Recommendation |
|---------|---------|----------|----------------|
| [specific issue] | [§ number or "missing"] | Critical / Important / Minor | [specific action] |
