# Scaffolding Ideas — Future Improvements

Ideas for improving Claude Code's role as an interactive MoE interpretability research assistant.

---

## New Skills

### `/health` — Pre-flight Validation
Before any pipeline stage, verify the system is ready:
- Backend running and model loaded (`/health` endpoint)
- GPU memory sufficient for planned operation
- Required session data exists on disk
- No zombie processes from previous runs

### `/compare` — Cross-Experiment Comparison
Compare routing patterns across two or more sessions:
- Load routing data from multiple sessions
- Identify shared vs divergent expert activations
- Statistical comparison of cluster distributions
- "What changed when we added the confound control?"

### `/temporal` — Temporal Basin Analysis
Guide Claude through the temporal capture experiment:
- Design token sequences that test attractor dynamics
- Run temporal captures with KV cache threading
- Analyze basin transitions across generation steps
- Visualize how routing evolves during autoregressive generation

### `/setup` — First-Run Experience
Guided setup for new users:
- Check Python version, CUDA availability, disk space
- Create venv and install dependencies
- Download model weights (with progress reporting)
- Run a minimal probe to verify the full pipeline
- "Your system is ready. Try `/pipeline` to start your first experiment."

### `/diagnose` — Troubleshooting Assistant
When things go wrong:
- Parse backend logs for known error patterns
- Check GPU memory with `nvidia-smi`
- Identify port conflicts and zombie processes
- Suggest fixes based on error signatures
- "The backend OOM'd because another process is using 8GB of VRAM. Kill PID 12345?"

---

## Skill Infrastructure Improvements

### Dependency Verification
Skills should verify prerequisites before executing. `/analyze` should confirm that `/categorize` was already run for the target session. `/probe` should confirm the backend is ready.

### Skill Versioning
Track skill versions so changes don't silently alter behavior. A `version` field in skill frontmatter, logged when the skill is invoked, would create an audit trail.

### Composable Skill Chains
Allow skills to invoke sub-skills. `/pipeline` already acts as an orchestrator — formalize this pattern so skills can declare dependencies and Claude can resolve the execution order.

---

## Pipeline Improvements

### Startup Timing and Reporting
Measure and report model loading time, GPU memory after load, and time-to-first-probe. Store timing data so Claude can set realistic expectations: "Based on your last 5 startups, model loading takes 3-4 minutes on your RTX 5070 Ti."

### Session Resume
If a probe capture is interrupted (crash, OOM, user abort), detect the partial session and offer to resume from the last completed batch rather than starting over.

### Automatic Confound Detection
After categorization, scan for potential confounds (sentence length correlating with label, lexical overlap between categories) and warn before analysis. Currently, `/probe` guides confound-aware design — extend this to post-hoc detection.

### Cross-Session Aggregation
Infrastructure for asking questions across sessions: "Across all 50 polysemy experiments, which experts consistently activate for spatial meanings?" Requires either a top-level index or a query layer over the session-isolated data lake.

---

## Analysis Improvements

### Richer Statistical Tests
Beyond chi-square: mutual information between routing patterns and labels, permutation tests for route significance, effect size measures (Cramér's V) alongside p-values.

### Interactive Hypothesis Testing
Let users specify hypotheses in natural language: "I think expert 14 in layer 3 is a syntax detector." Claude translates this into a statistical test, runs it, and reports whether the data supports the hypothesis.

### Export to LaTeX
Generate publication-ready tables and figure descriptions from analysis results. Route summary tables, statistical test results, and cluster descriptions formatted for direct inclusion in papers.

---

## UI Improvements

### Model Selector
When multiple models are supported, a model selector in the workspace page. Sessions are tagged with their model, and Claude knows which model to reference when analyzing.

### Comparison View
Side-by-side Sankey diagrams for two sessions. Same layout, same color mapping, visual diff highlighting where routing patterns diverge.

### Annotation Layer
Let users annotate Sankey nodes and routes with notes. Annotations persist with the session and are available to Claude during analysis: "You previously noted that expert 14 in layer 3 seems to activate for spatial prepositions."
