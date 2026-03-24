---
name: pipeline
description: Check analysis pipeline state for an experiment and suggest next step
---

# Pipeline State Check

Read `docs/PIPELINE.md` for the full pipeline reference.

## Step 1: Identify the Experiment

Ask the user which experiment to check, or list all available sessions:

```
GET /api/probes
```

Match by `sentence_set_name` field in session metadata (or `session_name` / `target_word` as fallback).

If multiple sessions match, present the list with dates and ask the user to pick one.

## Step 2: Find the Probe Guide

From the session's `sentence_set_name`, find the probe guide:

```
glob data/sentence_sets/**/{sentence_set_name}.md
```

Read it — it contains classification rules and analysis focus for this experiment.

## Step 3: Determine Pipeline Stage

Run these checks in order:

1. **No session found** → Stage 1 (design experiment with `/probe`)
2. **Session state != 'completed'** → Stage 2 (capture in progress or failed)
3. **`GET /api/probes/sessions/{id}/generated-outputs`** — check `output_category` field:
   - If null/empty on most probes → Stage 3 (categorize outputs with `/categorize`)
4. **`GET /api/probes/sessions/{id}/clusterings`** — list schemas:
   - If empty → USER GATE (user needs to explore clustering in UI)
5. **Load each schema** — check for reports:
   - If no reports → Stage 5 (analysis — protocol TBD)
   - If reports exist → Stage 6 (present reports) or temporal gate

## Step 4: Report & Suggest

Tell the user:
- Which experiment and session you found
- Current pipeline stage
- What the next action is
- Ask if they want to proceed

If user confirms, execute the next stage following docs/PIPELINE.md instructions.
