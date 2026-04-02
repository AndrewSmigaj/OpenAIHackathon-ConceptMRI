---
name: review-trace
description: Walk a concrete scenario end-to-end through the architecture — find gaps and friction
---

# Scenario Trace Review

Take a concrete scenario (user story, data flow, or command sequence) and trace it through every component it touches. This catches gaps between "the design says X" and "but then how does Y actually happen?"

ultrathink

## Rules
- You must trace a SPECIFIC scenario, not review in the abstract. If no scenario is given, pick the most representative user workflow from the design.
- At each step, name: the component, the interface used, the data shape, and what could go wrong
- "Works fine" is not useful. Show the actual path and flag where the design is silent or hand-wavy about the transition

## Invocation
`/review-trace [target] [scenario]`

If no scenario specified, choose the most common/critical user workflow described in the design.

## Workflow

1. **Identify the scenario**: What is the user or system trying to accomplish?
2. **Trace entry**: Where does the scenario enter the system? What triggers it?
3. **Follow each hop**: Component → interface → next component. At each transition:
   - What interface is used? (API call, context update, event, file read)
   - What's the data shape at this point?
   - What could go wrong at this transition?
   - Is this transition documented or implicit?
4. **Trace exit**: Where does the scenario produce its final result? What does the user see?
5. **Flag gaps**: Where did you have to guess because the design doesn't specify?
6. **Flag friction**: Where does the scenario require unnecessary hops or transformations?

## Output Format

```
Scenario: [description]

Step 1: [User does X]
  → Component: [name, § ref]
  → Interface: [what's called/triggered]
  → Data: [shape at this point]
  → Risk: [what could go wrong]
  → Gap: [anything unspecified]

Step 2: [Component handles X, passes to Y]
  → ...

Summary:
- Gaps found: [list]
- Friction points: [list]
- Unspecified transitions: [list]
```
