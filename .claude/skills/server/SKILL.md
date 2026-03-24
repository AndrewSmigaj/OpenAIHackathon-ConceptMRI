---
name: server
description: Start, stop, and check status of backend and frontend servers
---

# Server Management

Manage the Concept MRI backend (FastAPI + model) and frontend (Vite) servers.

## Constants

- **Project root**: `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI`
- **Python**: `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python`
- **Backend working dir**: `backend/src` (relative to project root)
- **Backend URL**: `http://localhost:8000`
- **Frontend URL**: `http://localhost:5173`
- **Health endpoint**: `http://localhost:8000/health`
- **Host binding**: `0.0.0.0` (required for WSL2)

## Commands

### Check Status

```bash
# Check if servers are running
ps aux | grep -E "uvicorn|vite" | grep -v grep

# Check if backend is up AND model is loaded
curl -s http://localhost:8000/health 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('Model loaded' if d.get('model_loaded') else 'API up but model NOT loaded')" 2>/dev/null || echo "Backend not responding"

# Check if frontend is responding
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```

### Stop All

**Always stop before starting.** The backend loads ~15GB model into GPU — duplicates will OOM.

```bash
pkill -f uvicorn; pkill -f vite; pkill -f "node.*vite"
sleep 2
# Verify clean — if process survives, force kill
PID=$(ps aux | grep uvicorn | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then kill -9 $PID; sleep 1; fi
# Final verify
ps aux | grep -E "uvicorn|vite" | grep -v grep
# Should print nothing
```

### Start Backend

```bash
cd /mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/backend/src && \
/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Run in background. **Wait for model to load** before using API.

**IMPORTANT: Model loading takes several minutes.** Do NOT start polling immediately. Wait at least 30 seconds before the first check, then poll every 15 seconds. The health endpoint distinguishes between "API is up" and "model is loaded":

```bash
# Wait 30s for uvicorn to start, then poll health endpoint
sleep 30
for i in $(seq 1 40); do
  HEALTH=$(curl -s --max-time 5 http://localhost:8000/health 2>/dev/null)
  if echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('model_loaded') else 1)" 2>/dev/null; then
    echo "Backend ready — model loaded"
    break
  fi
  # Check if API is at least responding (model still loading)
  if [ -n "$HEALTH" ]; then
    echo "API responding, model still loading... ($i/40)"
  else
    echo "Waiting for API... ($i/40)"
  fi
  sleep 15
done
```

If model loading fails, the API still starts (experiments/analysis endpoints work, but probe capture won't). Check the health endpoint — `model_loaded: false` means limited mode.

### Start Frontend

```bash
cd /mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/frontend && npm run dev
```

Run in background. Vite uses `strictPort: true` — will error (not silently rebind) if 5173 is taken.

### Full Start Sequence

1. Stop all existing processes (with force-kill fallback)
2. Verify nothing running on ports 8000/5173
3. Start backend in background
4. Wait 30s, then poll `/health` until `model_loaded: true` (up to 10 min)
5. Start frontend in background
6. Confirm both responding

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Network errors in browser | Backend not running or wrong port | Kill all, restart |
| Port 5173 in use | Zombie vite process | `pkill -f vite`, retry |
| Port 8000 in use | Zombie uvicorn | `pkill -f uvicorn`, retry |
| GPU OOM | Two backend instances or another GPU process | Kill all, check `nvidia-smi`, restart one |
| CORS errors | Backend not running | Start backend first |
| HMR not working | WSL2 polling issue | Check `vite.config.ts` has `usePolling: true` |
| New endpoint returns 404 | WSL2 reload didn't trigger | **Full restart required** — see TROUBLESHOOTING.md |
| Process won't die after pkill | GPU holding process | `kill -9 <PID>`, see TROUBLESHOOTING.md |
| `model_loaded: false` after startup | Model loading failed (GPU OOM, CUDA error) | Check backend logs, `nvidia-smi`, restart |
| Health returns but model never loads | Another process using GPU memory | Check `nvidia-smi`, close other GPU users |

For detailed troubleshooting steps, read `TROUBLESHOOTING.md` in this directory.

## Important Rules

- **Never** start a second backend instance — will OOM the GPU
- **Always** kill before start — even if you think nothing is running
- **Wait** for `model_loaded: true` from `/health` before making API calls
- **Use absolute paths** — don't rely on being in the right directory
- Backend must bind to `0.0.0.0` (not `127.0.0.1`) for WSL2 networking
- **Do NOT poll immediately** — wait at least 30s after starting backend before first health check
