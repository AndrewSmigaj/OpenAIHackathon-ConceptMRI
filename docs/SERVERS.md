# Server Operations

## Ports

| Service  | Port | URL                    |
|----------|------|------------------------|
| Backend  | 8000 | http://localhost:8000   |
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

## Starting Servers

Run from the project root: `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI`

### Backend (takes 1-2 min to load model)
```bash
cd backend/src
/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for `Model loaded successfully - API ready` before using the frontend.
If model loading fails, the API still starts in limited mode (no probe capture, but experiments/analysis work).

### Frontend
```bash
cd frontend
npm run dev
```

Should print `Local: http://localhost:5173/`. If it errors with "port in use", run the kill commands above.

## Claude Code Protocol

When asked to start servers:
1. Kill all existing processes first (`pkill -f uvicorn; pkill -f vite`)
2. Verify with `ps aux | grep` that nothing is running
3. Start backend first (background), wait for startup message
4. Start frontend (background)
5. Confirm both ports are correct (8000 + 5173)

**Never** start a second instance. Always kill-then-start.

## Troubleshooting

- **Network errors in browser**: Wrong port. Kill everything, restart.
- **Port 5173 in use**: Zombie vite process. `pkill -f vite` then retry.
- **Port 8000 in use**: Zombie uvicorn. `pkill -f uvicorn` then retry.
- **GPU OOM**: Two backend instances loaded the model. Kill all, restart one.
- **CORS errors**: Backend not running, or running on wrong port.
