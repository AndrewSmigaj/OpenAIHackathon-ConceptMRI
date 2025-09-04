# Concept MRI — Implementation Plan (v1.3, window consistency)

> **Purpose (for AI coders & the team):** Implement the MVP that follows the exact demo flow: **MoE routing first → select one expert highway → export cohort → clustering/CTA on that cohort**, with **k‑per‑layer** controls, **LLM‑assisted labeling**, and **Expert & Latent explorers**.  
> **Window rule (MVP):** The system **always computes and shows only the first CTA window**, auto‑selected. Next/Prev window controls are **visible but disabled**.  
> **Guardrails:** Do **not** change requirements. Do **not** add scope. All edits go through the PM (you).  
> **Developer ethos:** Make the codebase easy for humans who use AI assistants to build and maintain.

---

## 0) Non‑Functional Requirements (NFRs)
1) **AI‑Coder Friendly**
   - Plain, stable **file contracts** (Parquet/JSON) with explicit schemas (Appendix A).
   - Self‑describing **manifests** + example payloads.
   - Minimal infra: local **DuckDB** over Parquet.
   - Small, idempotent **CLIs**; clear stdout of output paths.
   - Deterministic defaults (`seed=1`, **first window auto**); effective‑config logs.
   - Short, typed functions with docstrings and interface notes for copilots.
2) **Performance & Resource**
   - 16 GB GPU, 32 GB RAM; bitsandbytes **NF4**, Accelerate offload; **OOM backoff** (micro‑batch floor=4).
   - MVP computes clustering/CTA **only on the first CTA window**; Next/Prev controls **disabled**.
3) **Reproducibility & Portability**
   - All artifacts include `{schema_version, model_hash, capture_id|experiment_id, config_hash, code_commit, created_at}`.
   - **Bundle** export per experiment; replay without hidden state.
4) **Process**
   - Follow this plan; UX copy and flows are **fixed** unless approved.

---

## 1) Terms (to prevent misread)
- **Highway (generic):** a **path through macro clusters** (rough clustering) across layers. Raise **k** to split further.  
- **Expert Highway:** a token’s **top‑1 expert** sequence across layers (K=1 routing).  
- **Latent Highway:** macro cluster path inside the **selected expert space** (from the cohort).  
- **Cohort:** exported tokens traveling a chosen expert highway; used as input to a **new analysis** (it does **not** filter the current run).  
- **First CTA window (MVP):** the system auto‑selects a window once per experiment and uses it everywhere (Wizard, Latent Explorer, APIs).

**Auto‑selection rule (deterministic):**  
- If layers `[6,7,8]` are captured, use **[6,7,8]**.  
- Else, choose the **smallest starting layer** `L` such that `[L, L+1, L+2]` exists in the captured set.  
- Record the chosen window in the experiment **manifest** and display it read‑only in the UI.

---

## 2) System Architecture (MVP)
- **Frontend:** React + Vite + TypeScript + Tailwind. Charts: **ECharts** (Sankey), **Plotly** (3D PCA).  
- **Backend:** Python 3.11, **FastAPI** + Uvicorn. GPU tasks in workers (plain Python).  
- **Data:** Parquet + **DuckDB**. PCA128 features stored in the lake; PCA params per layer persisted.  
- **Model Runtime:** HF Transformers, bitsandbytes (NF4), Accelerate `device_map="auto"`.

**Services (modules):**
`capture_svc`, `highways_svc`, `cohort_svc`, `cluster_svc`, `cta_svc`, `rules_svc`, `label_svc`, `bundle_svc`.

---

## 3) UX Surfaces & Flows

### 3.1 Workspace (landing)
Buttons: **[ New Probe ] [ New Analysis ] [ Open Bundle ] [ Resume ]**.  
Panels: Recent Experiments; Status (GPU OK, last probe time).

### 3.2 New Probe (atomic)
Fields: Context tokens (multi), Targets file (CSV/JSON), Layers (default 6–8).  
Run: **MoE capture** → post‑residual → PCA128; router top‑1 stats.  
Output: Lake artifacts + capture manifest; **Open in Expert Explorer** button.

**Acceptance:** Parquet files present; counts match probes × layers; PCA128 & routing rows align by `probe_id`/`layer`.

### 3.3 Experiment Wizard (analysis)
Stepper:
1) **Contexts & Targets** (choose from lake or upload list)  
2) **Run MoE (Expert Routing)** (skip if capture exists; else run)  
3) **Select Highway & Export Cohort** (Expert Sankey → click edge → **Token List** → **Export Cohort**)  
4) **Clustering/CTA on Cohort**  
   - Choose **KMeans** (default) or **Hierarchical**; set **k**/**k‑per‑layer**.  
   - **Window:** *First CTA window (auto‑selected, read‑only; displayed for clarity).*  
   - **MVP:** compute only this window; UI shows Next/Prev controls **disabled**.  
5) **Explore** (open explorers)

**State:** Step N writes artifacts and invalidates N+; wizard shows file paths and the chosen window in a side panel.

### 3.4 Expert Explorer
Views: **Expert Sankey (L..L+2)**; highways‑only toggle; tooltips (coverage, stickiness, ambiguous%).  
Expert Card tabs: Overview | Clusters | 3D PCA | Rules.  
**Token List** panel: tokens on selected highway; **[Export Cohort]**.  
**Primary action:** **Run clustering on this highway** → jump to Wizard step 4 with that cohort preloaded (uses the **same first window** as recorded in manifest).

### 3.5 Latent Explorer
Defaults: compute/show the **first CTA window**; Next/Prev controls visible but **disabled**.  
Features: **Latent Sankey** (macro first; drill to micro), **Path Drawer** (examples), **Cluster Cards** (Population + **LLM labels** with dominant/secondary/outliers + provenance).  
**k‑per‑layer** inputs for the (read‑only) first window; **Re‑Run** button.

**Acceptance:** Changing k‑per‑layer re‑clusters first window and refreshes visuals & cards.

### 3.6 Token Explorer (tool)
Inspect a token’s embedding, neighbors, lineage, and labels. Open via search or cards.

---

## 4) Data Flow (end‑to‑end)
1) **Capture Lake:** tokens, routing (K=1), features (PCA128) by layer; PCA models persisted.  
2) **Export Cohort:** from a selected expert highway.  
3) **Clustering (first window only):** KMeans/Hierarchical using PCA128; **k‑per‑layer** supported for those layers.  
4) **CTA:** macro paths + survival/confusion; ≥5% coverage filter.  
5) **Rules & Cards:** ETS (faithful) + CLR (lineage); LLM labels with dominant/secondary/outliers.  
6) **Bundle:** zip experiment directory.

---

## 5) API Endpoints (FastAPI)
```http
POST /api/capture           -> { capture_id, model_hash, lake_paths }
POST /api/highways          -> { highways_json_path, stats }
POST /api/cohort/export     -> { cohort_path }

# Window is implicit (first only). No window arg in MVP.
POST /api/cluster           -> { models: [...], assignments_paths: [...], window_used: [L,L+1,L+2] }
POST /api/cta               -> { paths_path, survival_path, window_used: [L,L+1,L+2] }

POST /api/rules/ets|clr     -> { rules_path }
POST /api/label             -> { clusters_path }
GET  /api/experiment/{id}   -> manifest & paths (includes window_used)
GET  /api/capture/{id}      -> manifest & paths
```

---

## 6) CLIs (thin wrappers)
Mirror the API with **no `--window` flag in MVP**:
```
cmri cluster --experiment <exp> --algo kmeans --k-per-layer L6=3 L7=4 L8=3
cmri cta --experiment <exp>
```
Both commands print the **window_used** they auto‑selected (e.g., `[6,7,8]`).

---

## 7) Module Plan (Python)
- `capture.py` — activation hooks, router stats, PCA per layer (fit/apply if absent).
- `highways.py` — P(Eℓ+1|Eℓ), coverage, stickiness/ambiguity; write `ExpertHighways.json`.
- `cohorts.py` — select probe_ids by highway signature; write cohort parquet.
- `cluster/` — `kmeans.py`, `hierarchical.py`, `base.py` (**ClusterBackend** interface).  
  - **Window selection** occurs once in `cluster.py` based on manifest & captured layers; stored into manifest as `window_used`.
- `cta.py` — macro paths & metrics; read `window_used`; write `paths.parquet`, `survival.parquet`.
- `rules/ets.py`, `rules/clr.py` — emit rules with precision/coverage + CIs.
- `labeling.py` — LLM + stats labeling; write `cards/clusters.parquet`.
- `cards.py` — write experts/clusters/archetypes parquet.
- `manifests.py`, `ids.py`, `io_parquet.py`, `duck.py` — utilities.

---

## 8) Core Algorithms (pseudocode)
```python
def select_first_window(captured_layers: list[int]) -> tuple[int, int, int]:
    # pick smallest L s.t. L, L+1, L+2 exist
    for L in sorted(set(captured_layers)):
        if {L, L+1, L+2}.issubset(captured_layers):
            return (L, L+1, L+2)
    raise ValueError("Need three consecutive layers for first window")

def cluster(exp_id, algo, k_per_layer):
    L0, L1, L2 = select_first_window(load_captured_layers(exp_id))
    for L in (L0, L1, L2):
        X = load_features_for_cohort(exp_id, L)         # PCA128
        model, labels, metrics = fit_cluster(algo, X, k_per_layer[L])
        write_cluster_model(exp_id, L, model, labels, metrics)
    write_manifest_window_used(exp_id, [L0, L1, L2])

def cta(exp_id):
    L0, L1, L2 = read_manifest_window_used(exp_id)
    seqs = sequences_of_cluster_ids(exp_id, (L0, L2))   # per probe_id
    paths = aggregate_paths(seqs, min_cov=0.05)
    survival = survival_confusion(seqs)
    write_paths(exp_id, paths); write_survival(exp_id, survival)
```

---

## 9) Frontend Component Map (React)
```
App
 ├─ WorkspacePage
 ├─ ExpertExplorer
 │   ├─ ExpertSankey (ECharts)
 │   ├─ ExpertCardTabs {Overview|Clusters|PCA3D|Rules}
 │   └─ TokenListPanel [Export Cohort] [Run clustering on this highway]
 └─ LatentExplorer
     ├─ LatentSankey (macro→micro; **window_used** shown read‑only)
     ├─ PathDrawer
     └─ ClusterCards (LLM labels + stats)
```
**UI Note:** In Wizard step 4 and Latent Explorer, display **“Window used: [L0,L1,L2] (auto‑selected)”** and keep Next/Prev disabled.

---

## 10) Testing & Acceptance
- **Capture:** row counts match; routing + PCA128 aligned.  
- **Expert Highways:** edges sum correctly; Token List matches selection; cohort export writes files.  
- **Clustering:** k‑per‑layer recompute refreshes Sankey + cards for the **auto‑selected first window**; manifest contains `window_used`.  
- **Latent Explorer:** paths ≥5% coverage rendered; Path Drawer examples present; Next/Prev disabled; window badge shown.  
- **Labeling:** Cluster Cards have `short_label`, `dominant`, `secondary`, `outliers`, `provenance="llm"`.  
- **Bundle:** contains manifest + paths; replay restores visuals with the **same window_used**.

---

## 11) 7‑Day Build Plan
1–2: Capture + Highways end‑to‑end; Expert Sankey; Export Cohort.  
3–4: Clustering (k‑per‑layer) + CTA on **auto first window** + Latent Sankey + Path Drawer.  
5: Cluster Cards with LLM labels; ETS/CLR JSON emitted.  
6: UI polish; PCA3D tab; disabled window controls; Bundle export.  
7: Record clips: highways → cohort export → latent CTA → two‑path zoom.

---

## 12) AI‑Coder Maintainability Kit (unchanged)
(Repo layout, tooling, interfaces, tests, logging, scripts, contribution guard — same as v1.2.)

---

## Appendix A — Schemas & Prompt (unchanged scope)
- Schemas match the data contracts (tokens, routing, features_pca128, clustering, CTA, rules, cards).  
- Labeling Prompt included for cluster/path cards.
