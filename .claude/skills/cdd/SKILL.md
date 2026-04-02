---
name: cdd
description: Uncertainty assessment before implementation — identify what you know, what you're guessing, and what to verify
---

# Uncertainty Assessment (CDD)

Pause before implementing. Assess what you're certain about, what you're uncertain about, and what to do about the gaps. This is a metacognitive practice — it works because "what are you uncertain about?" activates honest self-assessment instead of fake confidence.

## Invocation
`/cdd [task description]` or `/cdd` (will ask for task)

## Workflow

ultrathink

### 1. Understand the Task
Read the task description. If no task provided, ask.

### 2. Identify Changes
List every file that will be modified or created.

### 3. Assess What You Know and Don't Know

For each file/change, assess honestly:
- **High confidence**: Clear what to do, have read the code, no ambiguity
- **Medium confidence**: Understand the goal but need to verify assumptions
- **Low confidence**: Uncertain about approach, multiple valid options, or haven't read the code

Separately: what are you MOST certain about? What are you LEAST certain about? These are different questions worth answering independently.

### 4. Report

| File | Change | Confidence | What I'm uncertain about |
|------|--------|------------|--------------------------|
| ... | ... | High/Med/Low | ... |

For any Medium/Low items:
- What would raise confidence? (read a file, ask user, prototype)
- What's the risk if the assumption is wrong?
- Pre-mortem: "Assume this change fails — what went wrong?" (activates a different reasoning mode than "what could go wrong?")

### 5. Recommend
Either: "Ready to implement" or "Need to resolve [items] first"

If recommending to proceed, note any Medium items that should be verified during implementation rather than blocking on them.
