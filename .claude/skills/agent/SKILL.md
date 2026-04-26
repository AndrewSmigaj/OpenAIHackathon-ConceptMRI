---
name: agent
description: Start, monitor, inspect, and troubleshoot agent scenario sessions via the backend /api/agent endpoint
---

# Agent Session Management

Run agent scenario sessions through the backend's `/api/agent` endpoint. Agent sessions play Evennia scenarios tick-by-tick and capture residual-stream activations at target word positions. Results land in `data/lake/<session_id>/`.

This is the canonical reference for starting, monitoring, inspecting, stopping, and troubleshooting agent sessions. **Do not reconstruct the curl recipe from schemas.py** — use the operation blocks below verbatim.

## Prerequisites

The backend (with model loaded), Evennia, and the scenario build must all be ready:

1. Run `/server` OP-1 to confirm all three are up.
2. If backend is not loaded, `/server` OP-3 + OP-4.
3. If Evennia is not up, `/server` OP-6.
4. Scenarios must have been built into the Evennia DB — see "Building scenarios" below.

## Constants

| Constant | Value |
|----------|-------|
| Backend URL | `http://localhost:8000` |
| Start endpoint | `POST /api/agent/start` |
| Resume endpoint | `POST /api/agent/resume` |
| Stop endpoint | `POST /api/agent/stop` |
| Results dir | `$ROOT/data/lake/<session_id>/` |
| Tick log | `$ROOT/data/lake/<session_id>/tick_log.jsonl` |
| Probe results | `$ROOT/data/lake/<session_id>/probe_results.jsonl` |
| Session analysis | `$ROOT/data/lake/<session_id>/session_analysis.md` |
| Report (named) | `$ROOT/data/lake/reports/<date>_<session_name>_<...>.md` |
| Request schema | `backend/src/api/schemas.py:AgentStartRequest` |

All commands resolve `$ROOT` and `$PY` at the top:

```bash
ROOT=$(git rev-parse --show-toplevel)
PY="$ROOT/.venv/bin/python"
```

## Required parameters

Every `/api/agent/start` call **must** include:

- `session_name` (string) — human-readable name used in the report filename
- `scenario_id` (string) — which scenario YAML the session is anchored to
- `target_words` (list of string) — tokens whose activations to capture each tick
- `scenario_list` (list of string) — scenarios to run in sequence; can be a single entry
- `auto_start` (bool) — **MUST be `true`** to launch the agent loop immediately. Default is `false`; omitting it will create a session record that never runs anything.

Optional: `system_prompt` (overrides `DEFAULT_SYSTEM_PROMPT` in `agent_loop.py`), `max_ticks` (default 5), `capture_type_config`, `evennia_username`, `evennia_password` (defaults read from the `.env` file via `load_dotenv()` in `main.py`).

---

## Operations

### OP-1: Start agent session

Replace `SMOKE_NAME`, `FIRST_SCENARIO`, and `SCENARIOS` (a JSON array). The response's `session_id` is what you use for OP-2, OP-3, and OP-4.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && curl -s -X POST http://localhost:8000/api/agent/start -H "Content-Type: application/json" -d '{"session_name":"SMOKE_NAME","scenario_id":"FIRST_SCENARIO","target_words":["person"],"scenario_list":SCENARIOS,"auto_start":true}' | $PY -m json.tool
```

Save the returned `session_id`. If `auto_start` is omitted or `false`, the session is created but the loop never runs — a very common mistake.

### OP-1B: Resume an existing session

Add more scenarios to a session that already ran (completed or stopped). Results are appended to `probe_results.jsonl`. If the resume list includes scenarios that already have entries (e.g. retrying failures), duplicates will exist in the file. **Always run OP-1C after a resume completes** to deduplicate.

Replace `SESSION_ID` and `SCENARIOS` (a JSON array of scenario names to run). **Do not pass `evennia_username` or `evennia_password`** — the schema defaults read from `.env`.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && curl -s -X POST http://localhost:8000/api/agent/resume -H "Content-Type: application/json" -d '{"session_id":"SESSION_ID","scenario_list":SCENARIOS}' | $PY -m json.tool
```

Optionally pass `"system_prompt":"..."` to override the default prompt for the resumed run.

### OP-1C: Deduplicate probe results after resume

Keeps only the **last** entry per `scenario_name` — later retries replace earlier failures. Run this after a resumed session finishes.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && $PY -c "
import json
path = '$ROOT/data/lake/<session_id>/probe_results.jsonl'
lines = [json.loads(l) for l in open(path) if l.strip()]
seen = {}
for entry in lines:
    seen[entry['scenario_name']] = entry  # last wins
deduped = list(seen.values())
with open(path, 'w') as f:
    for entry in deduped:
        f.write(json.dumps(entry) + '\n')
print(f'Deduplicated: {len(lines)} entries -> {len(deduped)} unique scenarios')
"
```

### OP-2: Monitor a running session

Watch `tick_log.jsonl` grow, one line per tick:

```bash
ROOT=$(git rev-parse --show-toplevel) && tail -f "$ROOT/data/lake/<session_id>/tick_log.jsonl"
```

Or poll the result count to confirm scenarios finish (one line per completed scenario):

```bash
ROOT=$(git rev-parse --show-toplevel) && wc -l "$ROOT/data/lake/<session_id>/probe_results.jsonl"
```

Expected: `wc -l` equals `len(scenario_list)` when the session is done.

### OP-3: Inspect results

Pretty-print every probe result:

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && $PY -c "import json; [print(json.dumps(json.loads(l), indent=2)) for l in open('$ROOT/data/lake/<session_id>/probe_results.jsonl')]"
```

Human-readable per-tick summary (the file is generated at session end):

```bash
ROOT=$(git rev-parse --show-toplevel) && less "$ROOT/data/lake/<session_id>/session_analysis.md"
```

### OP-4: Stop a running session

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && curl -s -X POST http://localhost:8000/api/agent/stop -H "Content-Type: application/json" -d '{"session_id":"<session_id>"}' | $PY -m json.tool
```

### OP-5: Build (or rebuild) scenarios into Evennia

Idempotent. Re-run any time a scenario YAML changes. **Does NOT require an Evennia restart** for data changes, but Evennia typeclass/command changes do.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/evennia_world" && "$ROOT/.venv/bin/python" -c "
import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
sys.path.insert(0, os.getcwd())
django.setup()
import evennia; evennia._init()
from world.build_scenarios import build_all_scenarios
build_all_scenarios()
"
```

After running, do `evennia reload` from `$ROOT/evennia_world` to reload the running server.

---

## Common workflows

### Smoke test a scenario set

1. `/server` OP-1 to confirm backend ready, Evennia running.
2. OP-5 here (build scenarios) if any YAML was touched since the last run.
3. OP-1 here with `scenario_list` set to every YAML you want exercised. Use a descriptive `session_name` (e.g. `bus_stop_part3_smoke`).
4. OP-2 until `probe_results.jsonl` line count equals `len(scenario_list)`.
5. OP-3 to confirm `correct: true` and `error: null` for every entry.

### Single-scenario debug run

Set `scenario_list` to a one-element array with just the scenario you want to debug. Inspect `tick_log.jsonl` for the full generated text and parsed action per tick.

---

## Troubleshooting

### "Evennia authentication failed for 'agent' — still on welcome screen after connect"

The backend cannot auth as the `agent` account. Causes, in order of likelihood:

1. **`EVENNIA_AGENT_PASS` not in backend environment.** `main.py` calls `load_dotenv(project_root/".env")` at import time (since 2026-04-11) — if this is still failing, the `.env` file is missing, in the wrong place, or missing the `EVENNIA_AGENT_PASS=...` line. Check:

   ```bash
   ROOT=$(git rev-parse --show-toplevel) && grep EVENNIA_AGENT_PASS "$ROOT/.env"
   ```

2. **Backend wasn't fully restarted after a code change.** `schemas.py` reads `os.environ.get("EVENNIA_AGENT_PASS", "")` at import time as a Pydantic field default — a `--reload` may re-import schemas.py without re-running main.py's module init. Do `/server` OP-2 then OP-3 for a full restart.

3. **Orphaned Evennia session holding the agent puppet.** The `agent` account has only one character, so a stale login blocks new logins. Fix: `/server` OP-2 + OP-6 (full Evennia stop/start, not reload).

### "read_until_prompt timed out waiting for text"

Almost always a symptom of the auth failure above — the `connect` command never produced a prompt because the password was wrong. Same fixes.

### `probe_results.jsonl` shows `"error": "teleport_failed"`

`goto <room_name>` didn't find the scenario room. The scenario YAML was added or renamed but not built into the Evennia DB. Run OP-5 + `evennia reload` and try again.

### `probe_results.jsonl` shows `"error": "max_ticks_exceeded"`

The agent ran out of turns before reaching a scenario-complete action. Either the agent is struggling (look at `tick_log.jsonl` to see what it was doing) or `max_ticks` is too low for the scenario's state graph. Default is 5; set higher via the request body's `max_ticks` field.

### Session created but no `probe_results.jsonl` ever appears

You forgot `"auto_start": true`. The session exists as a record but the loop never launched. Stop/delete it, re-issue OP-1 with `auto_start: true`.

### Probe results all show `correct: false` despite obvious scenarios

Look at `session_analysis.md` tick 0 game text — if the short_desc for the NPC leaks friend/foe before the agent has a chance to examine, the agent skips the examine step and guesses from vibes. Fix the YAML short_desc, rebuild (OP-5 + reload), re-run. See `data/worlds/scenarios/GUIDE.md` for the short_desc / examine rule.

---

## OP-6: Post-run clustering

When a session finishes (`probe_results.jsonl` line count == `len(scenario_list)`),
this skill prompts the user once for how to cluster the run. Defaults come
from the YAML block in `/cluster/SKILL.md`. Agent sessions default to
`steps=[1]` (the post-examine tick).

Print the proposed schema and prompt:

```
Session complete — <N> scenarios captured. Session: <session_id>.

Proposed clustering schema:
  save_as:           <session_name>_k6_n15
  steps:             [1]
  last_occurrence_only: true
  reduction:         UMAP, 6D, n_neighbors=15
  clustering:        hierarchical, k=6 per layer
  (covers all 4 windows × 6 transitions × {cluster, expert ranks 1/2/3})

Answer one of:
  accept                        — build the proposed schema (one /cluster OP-1 call)
  sweep <axis> <values>         — build N schemas, one per value, suffixed names
                                  e.g. sweep steps [0],[1],[0,1]
                                       sweep max_probes 50,100,200
  custom                        — prompt for each parameter (defaults in brackets)
  skip                          — exit without building
```

On `accept`: invoke `/cluster` OP-1 once with the proposed params.

On `sweep <axis> <values>`: invoke `/cluster` OP-1 N times in sequence, one per
value, with `save_as` suffixed appropriately (e.g. `_step0`, `_step1`,
`_step01`). Non-interactive after the first prompt — overnight-friendly.

On `custom`: prompt the user for each of `save_as`, `steps`,
`n_neighbors`, `reduction_dimensions`, `default_k`, showing the proposed
default in brackets. Then invoke `/cluster` OP-1 once with the resulting
params. (A schema always covers all 4 windows × 6 transitions — there is
no per-window customization.)

On `skip`: print the session id and exit.

After all builds complete, print the schema names and exit. The user can then
invoke `/analyze` manually.

---

## Important rules

- **Never start a second backend** while one is already running — will OOM the GPU (~15GB model). Always `/server` OP-2 first.
- **`auto_start: true` is mandatory** for real runs — omit it only when you specifically want to create a dormant session record.
- **Don't push commits unless explicitly asked.** Commits are fine on user request; pushes must be explicit.
- **Agent sessions are single-tenant against Evennia's `agent` account.** Do not run two sessions concurrently.
