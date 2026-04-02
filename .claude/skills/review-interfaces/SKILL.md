---
name: review-interfaces
description: Are the boundaries between components clean, minimal, and well-defined?
---

# Interface & Boundary Review

Evaluate the seams between components. Clean interfaces make systems replaceable, testable, and understandable. Messy interfaces make everything fragile.

ultrathink

## Rules
- Every finding must identify a specific interface, contract, or boundary
- "Tightly coupled" is not a finding. "The MUD command dispatch (§7.C) directly calls VizConfigContext setters, meaning command logic can't be tested without the React context — an interface boundary is missing" is a finding
- Look for implicit contracts (assumptions that aren't documented) as hard as you look for explicit ones
- If the design references existing code (reuse, refactor, replace), read that code before assessing interfaces. The existing code's contracts may answer questions the design doc leaves open. A finding that the code already resolves is not a finding.
- Distinguish "not yet specified" (future phase placeholder) from "underspecified" (current phase gap). Phase 2+ placeholders in a phased design doc are expected, not findings.

## Questions

0. **Read referenced code first.** If the design doc says "reuse X" or "replace Y," read those components' actual interfaces before reviewing. The code is ground truth for existing contracts.
1. Identify all interfaces/contracts in the design: APIs, context shapes, event protocols, file formats, command grammars
2. For each interface: is it minimal? Does either side depend on internal details of the other?
3. Could you swap one side of an interface without the other knowing? If not, why?
4. Where would a change ripple? If you modify component X, what else has to change?
5. Are there implicit contracts — things that must be true for the system to work but aren't documented as interfaces?
6. Are there missing interfaces — places where components interact without a defined contract?
7. Do interfaces have clear error contracts? What happens when one side sends unexpected input?

## Output Format

| Interface | Between | Issue | Severity | Recommendation |
|-----------|---------|-------|----------|----------------|
| [name/description] | [Component A ↔ B] | [specific issue] | Critical / Important / Minor | [specific action] |
