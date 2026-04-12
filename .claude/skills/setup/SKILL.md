---
name: setup
description: First-time project setup — venv, Evennia database, agent account, .env, scenarios
---

# Project Setup

Full setup for someone cloning the repo from scratch. After this, `/server` starts everything and `/agent` runs sessions.

All commands resolve `$ROOT` and `$PY` at the top:

```bash
ROOT=$(git rev-parse --show-toplevel)
PY="$ROOT/.venv/bin/python"
```

---

## Operations

### OP-1: Create virtual environment and install dependencies

```bash
ROOT=$(git rev-parse --show-toplevel) && python3 -m venv "$ROOT/.venv" && "$ROOT/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt" && cd "$ROOT/frontend" && npm install
```

### OP-2: Create `.env` file

The `.env` file lives at the project root. The backend loads it via `load_dotenv()` in `main.py` before any schema imports. Format is bare `KEY=VALUE` (no `export`).

```bash
ROOT=$(git rev-parse --show-toplevel) && cp "$ROOT/.env.example" "$ROOT/.env" && PASS=$(openssl rand -base64 18) && echo "" >> "$ROOT/.env" && echo "# Evennia Agent (used by backend for agent loop)" >> "$ROOT/.env" && echo "EVENNIA_AGENT_USER=agent" >> "$ROOT/.env" && echo "EVENNIA_AGENT_PASS=$PASS" >> "$ROOT/.env" && echo ".env created. Agent password: $PASS" && echo "Edit .env to set OPENAI_API_KEY and other keys."
```

### OP-3: Initialize Evennia database

Creates the SQLite database and runs Django migrations. Run once.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/evennia_world" && PATH="$ROOT/.venv/bin:$PATH" "$ROOT/.venv/bin/evennia" migrate
```

### OP-4: Create agent account

Reads `EVENNIA_AGENT_USER` and `EVENNIA_AGENT_PASS` from `.env`. Does NOT require Evennia to be running — uses Django ORM directly. Idempotent.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/evennia_world" && set -a && source "$ROOT/.env" && set +a && "$ROOT/.venv/bin/python" -c "
import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
sys.path.insert(0, os.getcwd())
django.setup()
import evennia; evennia._init()
from world.setup_agent import setup_agent
setup_agent()
"
```

### OP-5: Build hub and lab rooms

Creates the Observer Hub (renames Limbo #2) and Researcher's Lab. Does NOT require Evennia to be running. Run once.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/evennia_world" && "$ROOT/.venv/bin/python" -c "
import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
sys.path.insert(0, os.getcwd())
django.setup()
import evennia; evennia._init()
from world.batch_build import build
build()
"
```

### OP-6: Build scenarios

Reads YAML files from `data/worlds/scenarios/` and creates rooms, NPCs, objects, and action state machines. Does NOT require Evennia to be running. Idempotent — re-run after any YAML changes.

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

### OP-7: Download model

~40GB download. Run with `run_in_background: true`.

```bash
ROOT=$(git rev-parse --show-toplevel) && "$ROOT/.venv/bin/pip" install "huggingface_hub[cli]" && huggingface-cli download openai/gpt-oss-20b --local-dir "$ROOT/data/models/gpt-oss-20b"
```

---

## Full setup sequence

Run in order for a fresh clone:

1. **OP-1** — venv + dependencies
2. **OP-2** — create `.env` (then edit to add API keys)
3. **OP-7** — download model (`run_in_background: true`, takes a while)
4. **OP-3** — Evennia migrate
5. **OP-4** — create agent account
6. **OP-5** — build hub and lab
7. **OP-6** — build scenarios
8. `/server` OP-6 — start Evennia
9. `/server` OP-3 — start backend (`run_in_background: true`)
10. `/server` OP-5 — start frontend (`run_in_background: true`)
11. `/server` OP-4 — wait for model to load (`run_in_background: true`)

Steps 4-7 do not require Evennia to be running — they write directly to the database. Evennia only needs to be up before the agent connects.

---

## Troubleshooting

### `evennia migrate` fails with "No module named 'evennia'"

The venv doesn't have Evennia installed. Run OP-1 first — `requirements.txt` includes it.

### `setup_agent` says "ERROR: No password"

`.env` is missing `EVENNIA_AGENT_PASS`. Run OP-2 or add the line manually.

### Agent auth fails after setup

The backend must be fully restarted after `.env` changes — `schemas.py` reads env vars at import time. Do `/server` OP-2 then OP-3.
