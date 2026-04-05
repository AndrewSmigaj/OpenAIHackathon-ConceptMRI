# Server Troubleshooting

## WSL2-Specific Issues

### Port won't free after `fuser -k`

```bash
# Escalate to SIGKILL
fuser -k -9 8000/tcp
sleep 2
fuser 8000/tcp 2>/dev/null && echo "STILL IN USE — check nvidia-smi" || echo "free"
```

If still stuck, the GPU driver may be holding the process. Check:
```bash
nvidia-smi
```

Kill any stuck GPU process, then retry.

### New endpoint returns 404 despite code being correct

**Cause**: Uvicorn `--reload` uses inotify, which is unreliable on WSL2 with `/mnt/c/` filesystem. New endpoints may not get loaded.

**Fix**: Full backend restart (OP-2 then OP-3 from SKILL.md).

**Verify** the endpoint is registered:
```bash
ROOT=$(git rev-parse --show-toplevel) && curl -s http://localhost:8000/openapi.json | "$ROOT/.venv/bin/python" -c "
import json, sys
paths = sorted(json.load(sys.stdin)['paths'])
for p in paths: print(p)
"
```

### Vite HMR not picking up changes

Usually auto-resolves. If not:
```bash
fuser -k 5173/tcp 2>/dev/null; sleep 1
cd $(git rev-parse --show-toplevel)/frontend && npm run dev
```
Then hard-refresh browser (Ctrl+Shift+R).

## Model Loading Issues

### `model_loaded: false` persists after 10 minutes

1. Check backend logs (the background task output file)
2. Check GPU memory: `nvidia-smi`
3. If OOM: kill backend, ensure no other GPU processes, restart
4. If CUDA error: kill backend, wait 10s, restart

### API responds but model never loads

The FastAPI app starts regardless of model status. Experiment/analysis endpoints (reading from disk) work fine. Only probe capture needs the model.

Check the health endpoint to distinguish:
```bash
ROOT=$(git rev-parse --show-toplevel) && curl -s http://localhost:8000/health | "$ROOT/.venv/bin/python" -m json.tool
```
