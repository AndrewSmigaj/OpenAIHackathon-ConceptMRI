# Concept MRI - Claude Code Context Engineering Guide

## Project Context
This is a 7-day OpenAI Hackathon project implementing **Concept MRI** - a tool that applies Concept Trajectory Analysis (CTA) to analyze MoE (Mixture of Experts) models. We're building both backend (Python FastAPI) and frontend (React) components.

## Guides Index

Claude Code uses these guides to execute the full pipeline:

| Guide | Purpose |
|-------|---------|
| `CLAUDE.md` | Project context, architecture rules, change management (this file) |
| `docs/PIPELINE.md` | Full analysis pipeline — orchestration runbook for Claude Code |
| `docs/PROBES.md` | How to create and run probes via API |
| `data/sentence_sets/GUIDE.md` | How to design and write sentence set JSON files |
| `docs/ANALYSIS.md` | Analysis methodology reference (cluster/route data, reports) |

**Skills** (`.claude/skills/`) are the authoritative operational procedures. Each skill has self-contained, copy-paste-ready commands. Docs provide background and reference. When they conflict, skills win.

| Skill | Purpose |
|-------|---------|
| `/server` | Start, stop, check status of backend and frontend |
| `/probe` | Co-design a new experiment |
| `/categorize` | Classify model-generated outputs |
| `/analyze` | Read cluster/route data, write reports and element descriptions |
| `/temporal` | Run temporal basin capture experiments |
| `/pipeline` | Check pipeline state, suggest next step |

## Environment Rules

- **ALWAYS use the project virtual environment** — run Python with `.venv/bin/python` (or activate with `source .venv/bin/activate`). Never use system `python` or `python3` directly. Never install packages globally.

## Environment Detection

On first server start, detect the platform to apply the right operational procedures:

- **WSL2**: paths start with `/mnt/c/`, `uname -r` contains "microsoft". inotify unreliable on NTFS mounts — new endpoints may need full restart. Use `fuser` not `pkill` for port management.
- **macOS**: `uname` returns "Darwin". Standard `lsof -i :PORT` for port management.
- **Linux**: `uname` returns "Linux" without "microsoft". Standard behavior.

All platforms: use `http://localhost:8000` for API URLs. Backend binds to `0.0.0.0` (the `--host` flag in uvicorn).

## Context Engineering Rules

### 1. Architecture-First Development
- **Reference `docs/research/architecture.yaml`** for original architecture design (note: may be stale — trust current code over YAML)
- Follow the file paths and service organization established in the codebase
- Respect the probe/experiment separation - no mixing of concerns

### 2. Implementation Strategy
- **Start with schemas and contracts** - implement data structures first
- **Build services incrementally** - capture → highways → cohorts → clustering → CTA
- **Test contracts immediately** - verify Parquet writes, API responses, manifest generation
- **Logging is non-negotiable** - use structured JSON logging for debugging

### 3. Context Management for Complex Tasks
- **Break down large services** into single-responsibility functions
- **Use parallel tool execution** for independent operations (multiple API calls, file operations)
- **Provide concrete examples** in docstrings and comments for complex algorithms
- **Reference the original CTA research paper** for mathematical implementations

### 4. MoE-Specific Requirements
- Target model: **ossb20b only** - don't abstract for multiple models yet
- Routing: **K=1 (top-1) expert selection only** 
- Features: **PCA128 dimensionality reduction** per layer
- Constraints: **Two token inputs, several thousand words max**

### 5. Error Handling Philosophy
- **Graceful degradation** - skip failed clusters, continue processing
- **Contextual logging** - always log the operation that failed and why
- **User-friendly errors** - API responses should explain what went wrong
- **Memory-aware** - handle GPU OOM with micro-batch backoff

### 6. Data Flow Clarity
```
PROBE FLOW: contexts → MoE capture → Parquet lake (reusable)
EXPERIMENT FLOW: word lists → highway selection → cohort → clustering/CTA → LLM labeling
```

### 7. File Contracts
- **Unique IDs everywhere**: capture_id, experiment_id, probe_id
- **Manifest-driven**: Every artifact has schema_version, created_at, provenance
- **Self-describing**: Parquet files include metadata for schema validation
- **Deterministic**: Same inputs → same outputs (seed=1 default)

### 8. Frontend Integration
- **API-first design** - frontend consumes clean REST endpoints
- **State management** - React components reflect backend state accurately  
- **Visualization priority** - Sankey charts (ECharts) are the primary UX
- **Demo scenarios** - build for the three hackathon demo workflows

### 9. LLM Integration Guidelines
- **User-supplied API keys** - no hardcoded credentials
- **Rate limiting** - handle API limits gracefully
- **Dual labeling** - LLMs generate BOTH cluster names AND archetypal path narratives
- **Provenance tracking** - record which LLM generated which labels

### 10. Development Workflow
- **Plan mode first** - use Claude's plan mode for complex implementations
- **Incremental builds** - get basic functionality working before adding features
- **Test early** - verify data contracts as soon as possible
- **Update architecture.yaml** - keep status current as you implement

### 11. CRITICAL: Change Management Rules
- **NO aggressive bulk changes** - make small, targeted edits only
- **ASK before any significant changes** - if changing more than 5 lines or altering design decisions, ask first
- **Preserve existing work** - NEVER delete functionality to add new features; be additive
- **Explain changes clearly** - before making edits, explain what will change and why
- **User must approve** - for any architectural or design changes, get explicit approval

## Key Technical Decisions
- **Backend**: Python 3.11, FastAPI, transformers, bitsandbytes (NF4)
- **Storage**: Parquet + DuckDB (local for MVP)  
- **Frontend**: React + Vite + TypeScript + Tailwind + ECharts
- **Visualization**: Sankey diagrams for both Expert and Latent highways
- **Window Strategy**: First window auto-selection only (MVP constraint)

## Hackathon Scope Reminders
- **Console logging only** - no file rotation or complex log management
- **Essential features first** - defer nice-to-haves until core demos work
- **User supplies LLM keys** - don't worry about cost optimization
- **Simple deployment** - local development environment sufficient

## Architecture Status Tracking
Monitor implementation progress by checking component statuses in architecture.yaml. Update as you complete tasks to maintain accurate project state.

Remember: This is context engineering, not prompt engineering. Provide Claude with complete context about data structures, algorithms, and system architecture so implementations are consistent and correct.