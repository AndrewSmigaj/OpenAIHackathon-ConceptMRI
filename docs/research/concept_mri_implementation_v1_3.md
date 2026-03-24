# Concept MRI — Implementation Plan (v1.4, probe-separated, experiment-centric)

> **Purpose (for AI coders & the team):** Build the MVP of Concept MRI that follows **your exact flow**:
> - **Probes are separate**: a probe capture writes *all inputs* needed for analyses (routing+features), **not** clustering/CTA.
> - **Experiments consume captures**: within **one experiment**, you do Expert Highways → select one highway → **export cohort (inside the experiment)** → Clustering/CTA (first window only) → Rules/Labels.
> - **Two-token regime**, **K=1** expert routing. **First CTA window only** (auto-selected and read-only). No “wizard” language — call it **Experiment Flow**.
> - Optional views to support clips: **Context Diff** in Expert Explorer; **Transformation Matrix** (routing mode) for contexts.

> **Guardrails:** Do **not** change requirements. Do **not** add scope. Ask before altering UX copy or flows. All defaults deterministic (`seed=1`).

---

## 0) Locked Rules (do not drift)
- **Probes** are standalone and write lake artifacts (routing K=1, PCA128 features). No clustering/CTA in probes.
- **Experiments** are the whole analysis: consume a capture → highways → cohort → clustering/CTA → cards/labels → export bundle.
- **First CTA window only** (auto-selected triplet `[L0,L1,L2]`; persisted as `window_used`; Next/Prev shown disabled).
- **Two-token inputs**; **MoE routing K=1**; per-expert interpretations; **k-per-layer** controls for clustering.
- **Backends** (MVP): KMeans (MiniBatch, default) and Hierarchical (Ward). ETS/CLR rules on cards; LLM-assisted labels.
- **No side-by-side compare screen**. Routing **diff** and **matrix** are single views you can open/close to record clips.

---

## 1) System Architecture (MVP)
- **Frontend:** React + Vite + TypeScript + Tailwind. Visuals: **ECharts** (Sankey, heatmap), **Plotly** (3D PCA).
- **Backend:** Python 3.11, **FastAPI** + Uvicorn. GPU tasks in plain Python workers.
- **Data:** Parquet on disk + **DuckDB** for queries. PCA params per layer persisted.
- **Runtime:** HF Transformers, bitsandbytes **NF4**, Accelerate `device_map="auto"`. Micro-batch backoff (floor=4).

**Services (top-level modules):**
- `probes/` → `capture_service` (routing + PCA128 to lake)
- `experiments/` → `highways_service`, `cohort_service`, `cluster_service`, `cta_service`, `rules_service`, `labeling_service`, `transform_service` (routing similarity utilities), `bundle_service`

---

## 2) UX Surfaces & Flows

### 2.1 Workspace (landing)
Buttons: **[ New Probe ]  [ New Experiment ]  [ Open Experiment ]  [ Open Transformation Matrix ]**
Panels: Recent Experiments, Recent Captures, Status (GPU OK, last probe time).

**Acceptance:** Buttons route correctly; both recents load immediately.

---

### 2.2 New Probe (atomic, standalone)
Fields: Context tokens (multi / CSV), Targets file (CSV/JSON), Layers (default 6–8).  
Action: Run capture → record **post-residual activations → PCA128** per layer, and **router top‑1 stats** per layer.  
Output: `data/lake/<capture_id>/...` + `capture_manifest.json`. UI shows **Open Experiment** on success.

**Acceptance:** Row counts = probes × layers; routing & features align by `(probe_id, layer)`.

---

### 2.3 New Experiment → **Experiment Flow** (consumes a capture)
Steps (shown as sections, not a wizard):
1. **Select Capture & Inputs**  
   - Pick an existing **capture**. Optionally narrow to a subset of contexts/targets.  
   - The **first CTA window** is auto-selected and shown read-only (`window_used`).

2. **Expert Highways** (from capture)  
   - **Expert Sankey** over `[L0→L1→L2]`; tooltips: coverage, stickiness, ambiguous%.  
   - **Context filter (1 or 2 contexts)** from the same capture.  
   - **Diff toggle**: if 2 contexts selected, show **ΔP** on edges and a small “Top Δ highways” table.  
   - Click a highway → **Token List** opens with **badges**: **Highway Signature** (e.g., `L6E2→L7E3→L8E1`) and **Context**.

3. **Export Cohort** (inside this experiment)  
   - Writes `experiments/<id>/cohort/…` + `cohort_manifest.json` (includes *Highway Signature*, *Context Tokens*).

4. **Clustering/CTA (first window only)**  
   - Choose backend (**KMeans** or **Hierarchical**).  
   - Set **k-per-layer** (for `[L0,L1,L2]` only).  
   - Run clustering → run CTA (macro paths + survival/confusion; coverage filter ≥5%).

5. **Explore & Label**  
   - **Latent Explorer**: **macro paths**; drill to **two latent paths** (k=2) for the “zoom” clip.  
   - **Cluster Cards**: Population + **ETS (faithful)** & **CLR (lineage)**; LLM labels (dominant / secondary / outliers + provenance).  
   - **3D PCA (per expert)** tab: color=cluster; size=margin; lasso filters.

6. **Export Bundle** (zip of experiment directory).

**Acceptance:** Each section writes artifacts; re-running **Clustering** invalidates CTA + cards only.

---

### 2.4 Transformation Matrix (routing mode; optional clip)
- Opens from Workspace or the Experiment Flow toolbar.  
- Select 2–10 contexts from a **capture**; backend computes pairwise **JS similarity** between **highway distributions** (first window).  
- **Heatmap** (ECharts); optional dendrogram (backlog). Clicking a cell opens Experiment Flow focused on that context.

**Acceptance:** Matrix returns values in `[0,1]`, symmetric; labels match selected contexts.

---

## 3) Data Flow (end-to-end)
1) **Probe** → Lake: `tokens.parquet`, `routing/layer=*`, `features_pca128/layer=*`, `capture_manifest.json`.
2) **Experiment** consumes capture: compute **ExpertHighways.json** (`window_used` persisted).
3) **Export Cohort**: select probes by **(Highway Signature, Context)** → write cohort parquet + manifest.
4) **Clustering (first window)**: fit on PCA128 for `[L0,L1,L2]` with **k-per-layer**; write models + assignments.
5) **CTA**: aggregate macro paths + survival/confusion; path examples.
6) **Rules/Labels**: ETS & CLR JSON; Cluster Cards with LLM labels.
7) **Bundle**: zip experiment dir.

---

## 4) APIs (FastAPI, stable, experiment-centric)

### Probes (standalone capture)
```
POST /api/probes
  body: { contexts:[str], targets_file:str, layers:[int] }
  -> { capture_id, model_hash, lake_paths }

GET  /api/probes
GET  /api/probes/{id}
  -> { manifest, lake_paths }
```

### Experiments (consume capture; no re-capture)
```
POST /api/experiments
  body: { capture_id:str, label?:str }
  -> { experiment_id }

POST /api/experiments/{id}/highways
  -> { highways_json_path, stats, window_used:[L0,L1,L2] }

POST /api/experiments/{id}/cohort
  body: { highway_signature:str, context:str }  # Format: "L6E2→L7E3→L8E1"
  -> { cohort_path }

POST /api/experiments/{id}/cluster
  body: { algo:'kmeans'|'hierarchical', k_per_layer:{L0:int, L1:int, L2:int} }
  -> { models:[...], assignments_paths:[...], window_used:[L0,L1,L2] }

POST /api/experiments/{id}/cta
  -> { paths_path, survival_path, window_used:[L0,L1,L2] }

POST /api/experiments/{id}/rules/ets
POST /api/experiments/{id}/rules/clr
  -> { rules_path }

POST /api/experiments/{id}/label
  -> { clusters_path }

GET  /api/experiments
  -> [{ id, created_at, capture_id, label?, window_used?, last_stage? }]

GET  /api/experiments/{id}
  -> { manifest, artifact_paths }
```

### Routing similarity (for optional clips; routing mode only)
```
POST /api/transform/matrix
  body: { capture_id:str, contexts:[str] }
  -> { labels:[str], matrix:[[float]], mode:'routing' }
```

---

## 5) CLIs (thin wrappers; stdout prints output paths)
```
cmri probe   --contexts ctx.csv --targets targets.csv --layers 6,7,8
cmri exp-new --capture <capture_id>
cmri exp-highways --exp <id>
cmri exp-cohort   --exp <id> --highway "L6E2→L7E3→L8E1" --context "the"
cmri exp-cluster  --exp <id> --algo kmeans --k-per-layer L6=3 L7=4 L8=3
cmri exp-cta      --exp <id>
cmri exp-rules    --exp <id> --mode ets|clr
cmri exp-label    --exp <id>
cmri transform-matrix --capture <capture_id> --contexts the,a,an
```

---

## 6) Modules (Python)

```
src/services/
  probes/
    capture.py            # K=1 routing + PCA128; NF4; backoff; capture_manifest
  experiments/
    highways.py           # P(Eℓ+1|Eℓ), coverage, stickiness, ambiguity; window_used
    cohorts.py            # select_by(highway_signature, context) -> parquet + manifest
    cluster/
      base.py             # ClusterBackend Protocol
      kmeans.py           # MiniBatch
      hierarchical.py     # Ward
    cta.py                # macro paths, survival/confusion, examples
    rules/
      ets.py              # thresholds over prior layer units (faithful)
      clr.py              # lineage over parent clusters/experts (readable)
    labeling.py           # LLM + stats → cards
    transform.py          # routing_distribution, js_similarity (first window)
    bundle.py
core/
  io_parquet.py manifests.py ids.py duck.py config.py types.py pca.py
```

---

## 7) Schemas (MVP; lean; with badges)

**tokens** (`lake/tokens.parquet`)
- `probe_id`, `context_text`, `target_text`, `context_token_ids`, `target_token_id`, `freq_bin?`, `pos_guess?`

**routing** (`lake/routing/layer=*/…`)
- `probe_id`, `layer`, `expert_top1_id`, `gate_top1_p`, `gate_entropy`, `margin`  
  *(No `routing_weights` or `expert_output` in MVP.)*

**features_pca128** (`lake/features_pca128/layer=*/…`)
- `probe_id`, `layer`, `pca128`, `pca_version`, `fit_sample_n`

**capture_manifest.json**
- `schema_version`, `capture_id`, `model_hash`, `contexts`, `layers`, `created_at`

**experiment_manifest.json**
- `schema_version`, `experiment_id`, `capture_id`, `window_used:[L0,L1,L2]`, `clustering:{algo,k_per_layer}`, `created_at`

**cohort_manifest.json**
- `schema_version`, `experiment_id`, `capture_id`, `highway_signature`, `context_tokens`, `created_at`

**clusters/** (per layer in window)
- `model.parquet` (algo, params, metrics), `assignments.parquet` (`probe_id`, `cluster_id`)

**cta/** 
- `paths.parquet` (`path_signature`, `coverage`, `examples[]`), `survival.parquet`

**rules/** 
- `ets.json` (faithful thresholds + prec/cov + CIs), `clr.json` (lineage rules + prec/cov)

**cards/** 
- `clusters.parquet` (population stats + LLM labels: `short_label`, `dominant`, `secondary`, `outliers`, `provenance`)

---

## 8) Core Algorithms (pseudocode snippets)

**Window selection (first only)**
```python
def select_first_window(captured_layers: list[int]) -> tuple[int,int,int]:
    for L in sorted(set(captured_layers)):
        if {L, L+1, L+2}.issubset(captured_layers):
            return (L, L+1, L+2)
    raise ValueError("Need three consecutive layers")
```

**Routing similarity (routing mode)**
```python
def routing_distribution(capture_id: str, context: str) -> dict[str, float]:
    # Count highways in first window, normalize to probability
    ...

def js_similarity(p: dict, q: dict) -> float:
    # 1 - Jensen–Shannon distance over aligned support
    ...
```

---

## 9) Testing & Acceptance

**Unit**
- Capture: correct row counts; PCA128 present; routing fields aligned.
- Cluster backends: deterministic labels for toy inputs; k-per-layer errors are actionable.
- Transform: routing_distribution normalized; js_similarity ∈ [0,1], symmetric.

**Integration**
- Probe → Experiment → Highways → Cohort → Cluster → CTA → Cards → Bundle (golden run on `samples/`).
- First-window rule: manifests include `window_used`; Latent Explorer shows badge; Next/Prev disabled.
- Expert Explorer: ΔP appears when selecting two contexts; “Top Δ highways” table populates.

**Acceptance (visual)**
- Expert Sankey tooltips: coverage, stickiness, ambiguous%; badges show Context + Highway Signature.
- Latent Sankey: macro paths visible; 2‑path zoom works; Cluster Cards show LLM labels with dominant/secondary/outliers.

---

## 10) Demo Storyboard (exact sequence to record)

**Clip 1 — New Probe (fast)**
1) Run **New Probe** for context `the` (and optionally `a`), targets file. Show “Capture complete.”

**Clip 2 — Start Experiment (select capture)**
2) **New Experiment**, choose the capture. The header shows **Window Used: [L6,L7,L8]** (read-only).

**Clip 3 — Expert Highways**
3) Show **Expert Sankey**; narrate coverage/stickiness.  
4) *(Optional sub‑clip)* Select contexts `the` & `a`; toggle **Diff** → ΔP tooltips + **Top Δ highways** mini-table.

**Clip 4 — Select Highway → Export Cohort**
5) Click a dominant highway → **Token List**; badges show **Highway Signature** & **Context**.  
6) Click **Export Cohort** (inside this experiment).

**Clip 5 — Clustering/CTA (first window)**
7) Choose **KMeans**; set **k-per-layer** (e.g., `[3,4,3]`). Run clustering → CTA.  
8) Open **Latent Explorer**: show **macro paths**; then **zoom to two latent paths** (k=2).

**Clip 6 — Cluster Cards + PCA**
9) Open **Cluster Cards**: Population + **ETS/CLR** + **LLM labels** (dominant/secondary/outliers).  
10) Open **3D PCA (per expert)** tab to illustrate geometry; quick lasso highlight.

**Clip 7 — (Optional) Transformation Matrix**
11) From Workspace, open **Transformation Matrix** (routing mode) for the capture; show similar contexts cluster (heatmap). Click a cell to jump back to the Experiment Flow (if desired).

**Clip 8 — Export Bundle**
12) Export bundle to show reproducibility.

---

## 11) 7‑Day Build Plan (MVP)
- **Day 1–2:** Probes (capture) → Highways end‑to‑end; Experiment Flow skeleton; Sankey renders.
- **Day 3:** Cohort export + k‑per‑layer clustering (first window) + CTA (macro paths + survival).
- **Day 4:** Latent Explorer (macro→micro), Path Drawer, badges; manifest wiring.
- **Day 5:** Cluster Cards (Population + ETS/CLR), LLM labels; 3D PCA tab.
- **Day 6:** Context Diff in Expert Explorer; Transformation Matrix (routing mode); polish; golden tests.
- **Day 7:** Record demo clips; bundle export; paper cuts.

---

## 12) AI‑Coder Maintainability Kit (unchanged essence)
- **Repo layout:** feature folders; `probes/` separate from `experiments/`.
- **Tooling:** `ruff`, `black` (100 cols), `mypy --strict`, `pytest -q`, `nbstripout`.
- **Make targets:** `setup`, `test`, `run-api`, `run-ui`, `fmt`, `typecheck`, `data-sample`.
- **Contracts:** Pydantic configs/manifests; Protocols for backends; docstrings with `AI_CONTRACT` notes.
- **Golden tests:** run `samples/` pipeline; determinism checks; JSONL structured logs.

---

## Appendix A — Labeling Prompt (cluster cards)
```
You are labeling a cluster of words from a language model’s latent space.
Task: provide a concise human-readable label and a structured breakdown.

Input:
- Cluster tokens: {token_list}
- Population stats: {stats_summary}

Instructions:
1. Group by higher-order ontology (examples): 
   - Animate objects (animals, people, living beings)
   - Inanimate objects (vehicles, tools, artifacts, places, food items, …)
   - Abstract concepts (qualities, emotions, ideas, relations)
   - Function words (pronouns, determiners, auxiliaries, prepositions, …)
   - Other
2. Identify dominant meaning, secondary meanings, and outliers.
3. Return:
   - short_label (2–5 words)
   - breakdown (counts or %)
   - outliers list
4. If uncertain, short_label = "Unknown" and return raw groups only.

Output (JSON):
{
  "short_label": "Animate Objects (Animals)",
  "dominant": "Animals",
  "secondary": ["Vehicles"],
  "outliers": ["sandwich"],
  "breakdown": {"Animals": 6, "Vehicles": 2, "Food": 1}
}
```
