---
name: agent-report
description: Generate a formatted markdown walkthrough report for agent scenario sessions, showing what the LLM saw and how it reasoned
---

# Agent Walkthrough Report

Generate a readable markdown report for one or more scenarios from an agent session. Shows the scenario definition alongside the agent's full tick-by-tick experience: what it saw, what it generated, how it reasoned, and whether it chose correctly.

Primarily used for debugging failed scenarios, but works for any scenario.

## Constants

| Constant | Value |
|----------|-------|
| Reports dir | `$ROOT/docs/agentreports/` |
| Sessions dir | `$ROOT/data/lake/<session_id>/` |
| Tick log | `$ROOT/data/lake/<session_id>/tick_log.jsonl` |
| Probe results | `$ROOT/data/lake/<session_id>/probe_results.jsonl` |
| Scenario YAMLs | `$ROOT/data/worlds/scenarios/<scenario_name>.yaml` |

## Inputs

The user provides:
- **session_id** — which session to report on
- **scenario_names** — one or more scenario names to include (or "failures" to auto-select all `correct: false`)

If the user says "report on the failures" or similar, filter `probe_results.jsonl` for `correct: false` entries.

## Report Format

Output file: `docs/agentreports/<date>_<session_name>_<scenario_name>.md`
(or `..._failures.md` if reporting multiple failures)

### Template

The report is markdown. Use the structure below exactly.

```markdown
# Agent Walkthrough: <scenario_name>

**Session:** `<session_id>` | **Date:** <timestamp> | **Result:** CORRECT / INCORRECT

## Scenario

> **Ground truth:** <friend|foe>
> **Agent chose:** `<action_command>` (<action_type>) — <correct|incorrect>
> **Ticks used:** <N>

### Room Description

<room description from YAML, as a blockquote>

### Objects

| Object | Examine text |
|--------|-------------|
| <name> | <examine> |

### NPC

- **Short desc:** <short_desc>
- **Examine (ground truth):**

<examine text from YAML, as a blockquote — this is what the agent sees after `examine person`>

### Actions Available

| # | Command | Description | Type | Correct? |
|---|---------|-------------|------|----------|
| 1 | `<command>` | <text> | friend | <yes/no> |
| ...

---

## Agent Walkthrough

### Turn 0 — Room Entry

**Game text the agent sees:**

```
<game_text from tick_log, verbatim>
```

**Agent reasoning:**

> <analysis field>

**Agent command:** `<action>`

**Evennia response:**

```
<evennia_response>
```

### Turn 1 — Decision

**Game text the agent sees:**

```
<game_text from tick_log, verbatim>
```

**Agent reasoning:**

> <analysis field>

**Agent command:** `<action>`

**Evennia response:**

```
<evennia_response>
```

(repeat for each turn)

---

## System Prompt

<details>
<summary>Full system prompt sent to the agent</summary>

```
<system_prompt from turn 0>
```

</details>

---

## Diagnosis

<Claude Code writes 2-3 sentences analyzing WHY the agent chose incorrectly,
based on the reasoning trace. What did the agent miss? What in the examine
text should have been a signal? Was the system prompt unclear?>
```

## Procedure

1. **Read the data.** Load `probe_results.jsonl` and `tick_log.jsonl` for the session. Read the scenario YAML files. Understand the data before writing anything.

2. **For each scenario**, read:
   - The YAML file for the scenario definition (room, objects, NPC, actions)
   - All tick_log entries for that scenario (ordered by `turn_id`)
   - The probe_results entry for the outcome

3. **Write the report** following the template above. The key sections:
   - **Scenario** — from the YAML, so the reader understands the setup and ground truth
   - **Agent Walkthrough** — tick by tick, showing game_text (what the LLM actually received), analysis (how it reasoned), action (what it chose), evennia_response (what happened)
   - **System Prompt** — collapsed in a details tag since it's the same across scenarios
   - **Diagnosis** — your analysis of why it failed (for failures) or what it did right (for successes)

4. **Write the file** to `docs/agentreports/`.

## Important

- The **game_text** is what matters most — it's the exact text the LLM receives from Evennia each turn. Show it verbatim in code blocks.
- The **analysis** field is the agent's chain-of-thought reasoning. Show it as a blockquote so it reads as the agent's internal monologue.
- The **generated_text** field contains raw channel-formatted output (`<|channel|>analysis<|message|>...`). The parsed `analysis` and `action` fields are cleaner — use those instead.
- Don't just dump data. Read it, understand it, and write the diagnosis.
- For multi-scenario failure reports, include a summary table at the top.
