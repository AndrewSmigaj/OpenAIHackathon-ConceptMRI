# Server Troubleshooting

Detailed troubleshooting for issues not covered by the quick table in SKILL.md.

## WSL2 File Watching Issues

### Symptom: New endpoint returns 404 despite code being correct

**Cause**: Uvicorn `--reload` uses file watchers. On WSL2 with Windows filesystem (`/mnt/c/...`), inotify events are unreliable. The reload watcher may not detect file changes, so new endpoints or code changes never get loaded.

**Diagnosis**:
```bash
# Check if endpoint exists in OpenAPI schema
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
paths = [p for p in data['paths']]
for p in sorted(paths):
    print(p)
"
```
If your new endpoint isn't listed, uvicorn didn't reload.

**Fix**: Full backend restart (not just touch):
```bash
# 1. Kill backend
pkill -f uvicorn
sleep 2
# 2. Verify dead (sometimes needs force kill on WSL2)
PID=$(ps aux | grep uvicorn | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    kill -9 $PID
    sleep 1
fi
# 3. Verify clean
ps aux | grep uvicorn | grep -v grep
# Should print nothing

# 4. Restart
cd /mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/backend/src && \
/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# Run in background

# 5. Poll until ready
for i in $(seq 1 24); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null)
  if [ "$STATUS" = "200" ]; then echo "Backend ready"; break; fi
  echo "Waiting for backend... ($i/24)"
  sleep 5
done

# 6. Verify new endpoint exists
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
paths = json.load(sys.stdin)['paths']
print('Endpoint registered' if '/api/YOUR_ENDPOINT' in paths else 'STILL MISSING')
"
```

**Key rule**: After adding or renaming any backend endpoint, ALWAYS do a full restart. Do not rely on `--reload` for structural changes on WSL2.

### Symptom: Vite HMR not picking up changes

**Cause**: Same WSL2 inotify issue. `vite.config.ts` should have `usePolling: true` but even that can lag.

**Fix**: Kill and restart Vite:
```bash
pkill -f vite; pkill -f "node.*vite"
sleep 1
cd /mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/frontend && npm run dev
# Run in background
```

After restart, hard-refresh browser (Ctrl+Shift+R). Vite cold-starts are fast (~2s).

## Backend Won't Die

### Symptom: `pkill -f uvicorn` exits but process still shows in `ps aux`

**Cause**: Process in uninterruptible state (common with GPU model loaded on WSL2).

**Fix**:
```bash
# Get exact PID
ps aux | grep uvicorn | grep -v grep | awk '{print $2}'
# Force kill
kill -9 <PID>
sleep 2
# Verify
ps aux | grep uvicorn | grep -v grep
```

If it STILL won't die, the GPU driver may be holding it. Wait 10 seconds and retry, or check `nvidia-smi` for stuck processes.

## Backend Starts but Model Fails to Load

### Symptom: API responds (200 on /docs) but probe capture endpoints fail

**Cause**: Model loading failed (OOM, CUDA error, missing weights). The FastAPI app starts regardless — experiment/analysis endpoints work, but anything requiring the model won't.

**Diagnosis**:
```bash
# Check backend logs for model loading errors
# (logs go to the background task output file)
```

**Fix**: Kill backend, check GPU memory (`nvidia-smi`), restart. If OOM, ensure no other GPU processes are running.

## Port Already in Use

### Symptom: Backend or frontend fails to start with "Address already in use"

**Fix**:
```bash
# Find what's using the port
ss -tlnp | grep -E "8000|5173"
# Kill it
pkill -f uvicorn  # or pkill -f vite
# Wait and retry
sleep 2
```

## When to Restart What

| Change made | Restart needed |
|-------------|---------------|
| Frontend `.tsx`/`.ts` file edit | None — Vite HMR (usually). If not, restart Vite |
| Backend `.py` file edit (existing endpoint) | None — uvicorn `--reload` (usually). If not, full restart |
| **Backend new endpoint or route added** | **ALWAYS full restart** |
| Backend dependency added | Full restart |
| Frontend dependency added (`npm install`) | Restart Vite |
| `.env` or config change | Full restart of affected server |
