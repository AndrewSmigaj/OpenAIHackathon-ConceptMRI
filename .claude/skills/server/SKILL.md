---
name: server
description: Start, stop, and check status of backend (FastAPI + Evennia) and frontend servers
---

# Server Management

Manage the Open LLMRI backend and frontend servers.

**The backend has two components:** FastAPI (API + model) and Evennia (MUD server). "Restart the backend" means restart BOTH. Always start/stop them together.

All commands use `$ROOT` as the project root (the git repo root). Resolve it once at the start of any operation:

```bash
ROOT=$(git rev-parse --show-toplevel)
PY="$ROOT/.venv/bin/python"
```

## Constants

| Constant | Value |
|----------|-------|
| Backend working dir | `$ROOT/backend/src` |
| Evennia working dir | `$ROOT/evennia_world` |
| Backend URL | `http://localhost:8000` |
| Frontend URL | `http://localhost:5173` |
| Evennia WebSocket | `ws://localhost:4002` |
| Health endpoint | `http://localhost:8000/health` |
| Host binding | `0.0.0.0` (required for WSL2) |

**NEVER use bare `python3`** — always use `$PY`.
**Evennia needs venv on PATH** — always prefix Evennia commands with `PATH="$ROOT/.venv/bin:$PATH"`.

---

## Operations

Each operation below is a single self-contained block. Copy the EXACT block — do not improvise or compose steps from multiple blocks.

### OP-1: Check Status

Run this FIRST before any other operation to understand current state.

```bash
ROOT=$(git rev-parse --show-toplevel) && PY="$ROOT/.venv/bin/python" && echo "=== Processes ===" && ps aux | grep -E "uvicorn|vite|evennia" | grep -v grep || echo "(none running)" && echo "=== Ports ===" && (fuser 8000/tcp 2>/dev/null && echo "8000: IN USE" || echo "8000: free") && (fuser 5173/tcp 2>/dev/null && echo "5173: IN USE" || echo "5173: free") && (fuser 4002/tcp 2>/dev/null && echo "4002: IN USE" || echo "4002: free") && echo "=== Backend Health ===" && curl -s --max-time 3 http://localhost:8000/health 2>/dev/null | $PY -c "import json,sys; d=json.load(sys.stdin); s=d.get('loading',{}).get('stage','?'); e=d.get('loading',{}).get('elapsed_seconds'); print(f'Model loaded — ready' if d.get('model_loaded') else f'Stage: {s} ({e}s elapsed)' if e else f'Stage: {s}')" 2>/dev/null || echo "Not responding" && echo "=== Frontend ===" && (curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:5173 2>/dev/null || echo "Not responding") && echo "" && echo "=== Evennia ===" && (cd "$ROOT/evennia_world" && PATH="$ROOT/.venv/bin:$PATH" "$ROOT/.venv/bin/evennia" status 2>&1)
```

### OP-2: Stop All

Use `fuser -k` (kills by port) — this is reliable on WSL2. `pkill` is NOT reliable here. Evennia uses its own stop command.

```bash
ROOT=$(git rev-parse --show-toplevel) && fuser -k 8000/tcp 2>/dev/null; fuser -k 5173/tcp 2>/dev/null; cd "$ROOT/evennia_world" && PATH="$ROOT/.venv/bin:$PATH" "$ROOT/.venv/bin/evennia" stop 2>/dev/null; sleep 2 && echo "=== Verify ===" && (fuser 8000/tcp 2>/dev/null && echo "8000: STILL IN USE" || echo "8000: free") && (fuser 5173/tcp 2>/dev/null && echo "5173: STILL IN USE" || echo "5173: free") && (fuser 4002/tcp 2>/dev/null && echo "4002: STILL IN USE" || echo "4002: free")
```

If a port shows "STILL IN USE" after this, run `fuser -k -9 <port>/tcp` (SIGKILL).

### OP-3: Start Backend — FastAPI (background)

**Prerequisite**: Port 8000 must be free (run OP-2 first if needed). **Always start OP-6 (Evennia) alongside this** — both are part of the backend.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/backend/src" && "$ROOT/.venv/bin/python" -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Run with `run_in_background: true`.

**Do NOT add `--reload`.** The WatchFiles reloader interacts badly with the model-load thread on WSL2 — the worker can bind the port but leave the event loop wedged, so connections hang even though the process looks healthy. After any code change, do a full restart (OP-2 → OP-3 + OP-5 + OP-6 → OP-4). No shortcuts.

### OP-4: Wait for Model

**Run AFTER OP-3.** Must use `run_in_background: true` — takes ~2-3 minutes.

The health endpoint now reports loading stage in real time (the API serves immediately while model loads in background). No need to read log files.

```bash
PY=$(git rev-parse --show-toplevel)/.venv/bin/python; for i in $(seq 1 60); do H=$(curl -s --max-time 3 http://localhost:8000/health 2>/dev/null); if [ -z "$H" ]; then echo "[$i] Waiting for API..."; sleep 5; continue; fi; STAGE=$(echo "$H" | $PY -c "import json,sys; print(json.load(sys.stdin).get('loading',{}).get('stage','unknown'))"); ELAPSED=$(echo "$H" | $PY -c "import json,sys; print(json.load(sys.stdin).get('loading',{}).get('elapsed_seconds','?'))"); if [ "$STAGE" = "ready" ]; then echo "READY — model loaded in ${ELAPSED}s"; exit 0; fi; if [ "$STAGE" = "failed" ]; then echo "FAILED — check backend logs"; exit 1; fi; echo "[$i] Stage: $STAGE (${ELAPSED}s elapsed)"; sleep 5; done; echo "TIMEOUT — model did not load in 5 minutes"
```

**Expected output:**
```
[1] Waiting for API...
[2] Stage: initializing (3.2s elapsed)
[3] Stage: loading_model (8.1s elapsed)
...
[24] Stage: loading_model (118.5s elapsed)
[25] Stage: creating_service (121.0s elapsed)
[26] READY — model loaded in 123.4s
```

**Stages**: `not_started → initializing → loading_model → creating_service → ready | failed`

### OP-5: Start Frontend (background)

**Prerequisite**: Port 5173 must be free.

```bash
cd $(git rev-parse --show-toplevel)/frontend && npm run dev
```

Run with `run_in_background: true`. Vite uses `strictPort: true` — will error if 5173 is taken.

### OP-6: Start Backend — Evennia (background)

**Prerequisite**: Ports 4000, 4002 must be free. **Always start alongside OP-3** — both are part of the backend.

```bash
ROOT=$(git rev-parse --show-toplevel) && cd "$ROOT/evennia_world" && PATH="$ROOT/.venv/bin:$PATH" "$ROOT/.venv/bin/evennia" start
```

Run with `run_in_background: true`. Evennia is a daemon — Portal starts immediately, Server takes a few seconds. Check with `evennia status`.

---

## Common Workflows

### Deploy Code Changes (MANDATORY after any backend/Evennia edit)

After editing ANY backend `.py` or Evennia typeclass/command file, ALWAYS run this full sequence. Never rely on `--reload` or partial restarts — WSL2 inotify is unreliable and partial restarts cause orphaned sessions.

1. Run **OP-2** (stop all) — wait for all ports to show "free"
2. If Evennia scenario YAMLs changed, rebuild scenarios (agent skill OP-5)
3. Run **OP-3** + **OP-5** + **OP-6** in parallel (start backend, frontend, Evennia)
4. Run **OP-4** (wait for model) — do NOT start agent sessions until this shows "READY"

This is the ONLY way to deploy changes. No shortcuts.

### Restart All

Same as Deploy Code Changes above — this is the typical workflow.

1. Run **OP-2** (stop all)
2. Verify all ports show "free"
3. Run **OP-3** + **OP-6** + **OP-5** in parallel (`run_in_background: true` for all three) — OP-3 and OP-6 are both backend components, OP-5 is frontend
4. Run **OP-4** (wait for model, `run_in_background: true`)
5. When OP-4 completes with "READY", backend is fully operational

### Start From Scratch

1. Run **OP-1** to assess current state
2. If anything is running, run **OP-2**
3. Follow steps 3-7 from "Restart All" above

### Frontend-Only Restart

Only needed if Vite HMR stops working (rare).

```bash
fuser -k 5173/tcp 2>/dev/null; sleep 1; cd $(git rev-parse --show-toplevel)/frontend && npm run dev
```

Run with `run_in_background: true`.

---

## When to Restart

| Change made | Action needed |
|-------------|---------------|
| Frontend `.tsx`/`.ts` edit only | None — Vite HMR handles it |
| **Any backend or Evennia code change** | **ALWAYS full restart: OP-2 → OP-3 + OP-5 + OP-6 → OP-4** |

**No exceptions.** Never rely on `--reload`. Never do partial restarts. Never restart only one service. The 2-minute model load is nothing compared to debugging a half-started state.

## Important Rules

- **Never** start a second backend — will OOM the GPU (~15GB model)
- **Always** stop before start — even if you think nothing is running
- **Use `fuser -k`** to stop, not `pkill` — `pkill` is unreliable on WSL2
- **Wait** for `model_loaded: true` before making API calls that need the model
- Experiment/analysis endpoints work WITHOUT the model (they read from disk)
- Backend must bind to `0.0.0.0` (not `127.0.0.1`) for WSL2 networking
- **NEVER use bare `python3`** — always use `$PY` (venv path)
