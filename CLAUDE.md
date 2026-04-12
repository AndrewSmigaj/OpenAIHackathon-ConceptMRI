Related: docs/architecturemud.md (if adding phases/skills), docs/PIPELINE.md (if changing pipeline stages), LLMud/VISION.md (if changing project scope)

# Concept MRI — Claude Code Context Engineering Guide

## Project Context
Independent research tool for studying attractor basin dynamics in MoE language models. Uses UMAP projection and hierarchical clustering of residual stream activations to identify stable geometric regions — attractor basins — that predict model behavior before output is generated. Backend (Python FastAPI) captures and analyzes; frontend (React) visualizes. Claude Code is the analysis runtime — it designs probes, runs captures, labels outputs, and generates hypotheses.

## Guides Index

Claude Code uses these guides to execute the full pipeline:

| Guide | Purpose |
|-------|---------|
| `CLAUDE.md` | Project context, architecture rules, change management (this file) |
| `docs/PIPELINE.md` | Full analysis pipeline — orchestration runbook for Claude Code |
| `docs/PROBES.md` | How to create and run probes via API |
| `data/sentence_sets/GUIDE.md` | How to design and write sentence set JSON files |
| `docs/ANALYSIS.md` | Analysis methodology reference (cluster/route data, reports) |
| `docs/scratchpad/` | Intermediate work products — research, drafts, explorations. Check for context from recent work. |

**Skills** (`.claude/skills/`) are the authoritative operational procedures. Each skill has self-contained, copy-paste-ready commands. Docs provide background and reference. When they conflict, skills win. **Before any API call to `/api/agent/*`, invoke the `/agent` skill and copy its curl template. Never construct agent curl commands from memory or from reading schemas.py — the skill templates omit credentials because they default from `.env`.**

| Skill | Purpose |
|-------|---------|
| `/setup` | First-time project setup — venv, Evennia, agent account, .env, scenarios |
| `/server` | Start, stop, check status of backend and frontend |
| `/agent` | Start, resume, monitor, stop agent scenario sessions — **always use for agent API calls** |
| `/probe` | Co-design a new experiment |
| `/categorize` | Classify model-generated outputs |
| `/analyze` | Read cluster/route data, write reports and element descriptions |
| `/temporal` | Run temporal basin capture experiments |
| `/pipeline` | Check pipeline state, suggest next step |
| `/cdd` | Uncertainty assessment before implementation |
| `/devils-advocate` | Challenge a design — find real weaknesses, not performative objections |
| `/competitive-design` | Generate and compare genuinely different approaches |
| `/review-onboarding` | Could a newcomer understand and implement from this? |
| `/review-deliverability` | Can phases ship independently with value? |
| `/review-risks` | Failure modes, blast radius, recovery paths |
| `/review-scope` | Is everything earning its complexity? Sunk cost check. |
| `/review-interfaces` | Are boundaries clean, minimal, well-defined? |
| `/review-consistency` | Do all the parts agree with each other? |
| `/review-evolution` | What's locked in vs. flexible? Cost of being wrong? |
| `/review-trace` | Walk a scenario end-to-end through the architecture |
| `/review-drift` | Does implementation match design? |
| `/review-best-practices` | Design quality against engineering principles |
| `/thorough-review` | Fan-out all review skills via agents, synthesize findings |

## Environment Rules

- **ALWAYS use the project virtual environment** — run Python with `.venv/bin/python` (or activate with `source .venv/bin/activate`). Never use system `python` or `python3` directly. Never install packages globally.

## Environment Detection

On first server start, detect the platform to apply the right operational procedures:

- **WSL2**: paths start with `/mnt/c/`, `uname -r` contains "microsoft". inotify unreliable on NTFS mounts — new endpoints may need full restart. Use `fuser` not `pkill` for port management.
- **macOS**: `uname` returns "Darwin". Standard `lsof -i :PORT` for port management.
- **Linux**: `uname` returns "Linux" without "microsoft". Standard behavior.

All platforms: use `http://localhost:8000` for API URLs. Backend binds to `0.0.0.0` (the `--host` flag in uvicorn).

## First-Time Setup

If `.venv` does not exist, the project needs initial setup:

1. `python3 -m venv .venv`
2. `.venv/bin/pip install -r backend/requirements.txt`
3. `cd frontend && npm install`
4. Download model: `.venv/bin/pip install huggingface_hub[cli] && huggingface-cli download openai/gpt-oss-20b --local-dir data/models/gpt-oss-20b`

After setup, use `/server` to start the backend and frontend.

## Context Engineering Rules

### 1. Architecture-First Development
- Follow the file paths and service organization established in the codebase
- Respect the probe/experiment separation — no mixing of concerns

### 2. Implementation Strategy
- **Start with schemas and contracts** — implement data structures first
- **Build services incrementally** — probe → capture → categorize → schema → analyze → temporal
- **Test contracts immediately** — verify Parquet writes, API responses, manifest generation
- **Logging is non-negotiable** — use structured JSON logging for debugging

### 3. Context Management for Complex Tasks
- **Break down large services** into single-responsibility functions
- **Use parallel tool execution** for independent operations (multiple API calls, file operations)
- **Provide concrete examples** in docstrings and comments for complex algorithms
- **Reference `paper/main.tex`** for methodology details (basin identification, temporal analysis, behavioral validation)

### 4. MoE-Specific Requirements
- Target model: **gpt-oss-20b only** — don't abstract for multiple models yet
- Routing: **K=1 (top-1) expert selection only**
- Dimensionality reduction: **UMAP 6D** for clustering, applied to residual stream activations
- Temporal captures process sequences of up to 40 sentences with expanding context windows

### 5. Error Handling Philosophy
- **Graceful degradation** - skip failed clusters, continue processing
- **Contextual logging** - always log the operation that failed and why
- **User-friendly errors** - API responses should explain what went wrong
- **Memory-aware** - handle GPU OOM with micro-batch backoff

### 6. Data Flow
```
PROBE FLOW: sentence set → capture (forward pass + hooks) → Parquet lake (reusable)
ANALYSIS FLOW: Parquet → UMAP 6D → hierarchical clustering → behavioral validation → reports
TEMPORAL FLOW: expanding context window → basin axis projection → lag measurement
```

### 7. File Contracts
- **Unique IDs everywhere**: capture_id, experiment_id, probe_id
- **Manifest-driven**: Every artifact has schema_version, created_at, provenance
- **Self-describing**: Parquet files include metadata for schema validation
- **Deterministic**: Same inputs → same outputs (seed=1 default)

### 8. Frontend Integration
- **API-first design** — frontend consumes clean REST endpoints
- **State management** — React components reflect backend state accurately
- **Visualization priority** — Sankey charts (ECharts), stepped UMAP trajectories, and temporal lag charts are the primary UX

### 9. Claude Code as Runtime
- Claude Code is the analysis runtime — it designs probes, runs analysis, labels outputs, and generates hypotheses
- No separate LLM API keys needed — Claude Code does the reasoning directly
- Skills (`.claude/skills/`) define the operational procedures for each pipeline stage
- The human steers; Claude executes and reasons

### 10. Development Workflow
- **Plan mode first** — use Claude's plan mode for complex implementations
- **Incremental builds** — get basic functionality working before adding features
- **Test early** — verify data contracts as soon as possible
- **Check scratchpad first** — read `docs/scratchpad/` for context from recent conversations before starting new work
- **Research before change** — read actual code, understand actual state, THEN decide what to change. Never jump to implementation based on pattern matching.
- **Investigate before proposing** — when something is wrong, read the actual data and code before suggesting fixes. State what you found, what you're certain about, and what you're uncertain about. Never propose a fix with high confidence when you haven't verified the root cause.
- **Watch for attractor patterns** — over-abstracting, over-engineering for hypothetical requirements, adding error handling for impossible cases, summarizing what you just did. Counter: "what's simplest?" and "is this real or hypothetical?"
- **Sunk cost awareness** — replace bad code, don't patch around it. We control everything; backward compatibility is unnecessary.
- **Document sync** — after modifying any file in `docs/` or `LLMud/`, check its `Related:` header. Update anything that drifted. Updating related docs is always in scope — you do not need separate permission.
- **Session-end review** — at the end of larger sessions, review what approaches worked or didn't and save insights to development feedback memories.

### 11. CRITICAL: Change Management Rules
- **NO aggressive bulk changes** - make small, targeted edits only
- **ASK before any significant changes** - if changing more than 5 lines or altering design decisions, ask first
- **Preserve existing work** - NEVER delete functionality to add new features; be additive
- **Explain changes clearly** - before making edits, explain what will change and why
- **User must approve** - for any architectural or design changes, get explicit approval

### 12. Uncertainty Assessment
- **Never jump straight to implementation** — assess uncertainty first. Run `/cdd` for the structured procedure, or do a quick inline assessment for smaller tasks.
- **New work needs a plan** — if the task involves more than a single targeted edit, write a plan and get approval before proceeding. Modifying scaffolding, architecture, or multi-file changes always require a plan.
- **Plans expire on scope change** — if you discover the task is different from what the plan covers, stop and re-plan rather than stretching the existing plan to fit.

## Key Technical Decisions
- **Backend**: Python 3.11, FastAPI, transformers, bitsandbytes (NF4)
- **Storage**: Parquet files in `data/lake/` — one directory per session
- **Frontend**: React + Vite + TypeScript + Tailwind + ECharts
- **Visualization**: Sankey diagrams (expert routing + latent space clusters), stepped UMAP trajectories, temporal lag charts
- **Model**: gpt-oss-20b, NF4 quantized, ~15GB VRAM

## Compact Instructions
When compacting, always preserve: active session IDs, schema names, the WSL2 environment rules (fuser not pkill, .venv paths), any in-progress pipeline stage, and any active scratchpad file names and their purpose.