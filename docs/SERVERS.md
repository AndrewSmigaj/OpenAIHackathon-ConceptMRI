# Server Operations

## Ports

| Service  | Port | URL                    |
|----------|------|------------------------|
| Backend  | 8000 | http://0.0.0.0:8000    |
| Frontend | 5173 | http://localhost:5173   |

Frontend expects backend at `http://localhost:8000/api` (hardcoded in `frontend/src/api/client.ts`).
Vite is set to `strictPort: true` — it will **error** instead of silently picking another port.

## Before Starting

**Always kill existing instances first.** The backend loads a large model into GPU memory — duplicate instances will OOM or cause port conflicts.

```bash
# Kill everything
pkill -f uvicorn; pkill -f vite; pkill -f "node.*vite"

# Verify clean
ps aux | grep -E "uvicorn|vite" | grep -v grep
# Should print nothing
```

If processes survive `pkill`, use `kill -9` on the PIDs.

## Starting Servers

Run from the project root: `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI`

### Backend (~2 min to load model)

**Do NOT use `--reload`.** On WSL2, the reload watcher causes the server to stop accepting connections after model load. Use plain uvicorn:

```bash
cd backend/src && \
  /mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Model loading shows a progress bar (411 weight shards). After `Application startup complete`, the server is ready.

If model loading fails, the API still starts in limited mode (no probe capture, but experiments/analysis work).

### Frontend
```bash
cd frontend && npm run dev
```

Should print `Local: http://localhost:5173/`. If it errors with "port in use", run the kill commands above.

## Health Check

```bash
curl -s http://0.0.0.0:8000/health
```

Expected response:
```json
{"status": "healthy", "model_loaded": true, "gpu_available": true, "gpu_name": "NVIDIA GeForce RTX 5070 Ti", "sessions_available": true}
```

`model_loaded: false` means the API is up but model didn't load — probe capture won't work, but analysis endpoints will.

## Claude Code Protocol

When asked to start servers:
1. Kill all existing processes first (`pkill -f uvicorn; pkill -f vite; pkill -f "node.*vite"`)
2. If processes survive, `kill -9` by PID
3. Start backend (background, **no `--reload`**), wait for `Application startup complete`
4. Run health check: `curl -s http://0.0.0.0:8000/health` — confirm `model_loaded: true`
5. Start frontend (background)
6. Confirm both ports respond (8000 + 5173)

**Never** start a second instance. Always kill-then-start.
**Always** use `http://0.0.0.0:8000` for curl, not `localhost` (WSL2 routing).

## Pipeline State Check

After servers are up, assess pipeline state per `docs/PIPELINE.md`:

```bash
# 1. List sessions
curl -s http://0.0.0.0:8000/api/probes

# 2. Session details
curl -s http://0.0.0.0:8000/api/probes/{session_id}

# 3. Check output categorization
curl -s http://0.0.0.0:8000/api/probes/sessions/{session_id}/generated-outputs

# 4. Check clustering schemas
curl -s http://0.0.0.0:8000/api/probes/sessions/{session_id}/clusterings

# 5. Check reports in schema details
curl -s http://0.0.0.0:8000/api/probes/sessions/{session_id}/clusterings/{schema_name}
```

## Troubleshooting

- **curl times out / connection refused**: Server not ready yet (model still loading), or `--reload` was used. Kill and restart without `--reload`.
- **Port 5173 in use**: Zombie vite process. `pkill -f vite` then retry.
- **Port 8000 in use**: Zombie uvicorn. `pkill -f uvicorn` then retry.
- **GPU OOM**: Two backend instances loaded the model. Kill all, restart one.
- **CORS errors**: Backend not running, or running on wrong port.
- **`localhost` doesn't work for curl**: Use `http://0.0.0.0:8000` instead (WSL2 networking quirk).
