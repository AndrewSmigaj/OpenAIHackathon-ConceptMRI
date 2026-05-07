#!/usr/bin/env python3
"""
Generate the bar charts and line plots for the per-token separation study.

Plots produced (PNGs in docs/research/StudiesByClaude/figures/):
  - plot1_cramers_v_per_token_L23.png — bar chart, per-token Cramér's V at L23,
    one bar group per condition (single, neutral, fictional-writing, suicide-content),
    with random-shuffle null-baseline 95th-percentile horizontal lines.
  - plot2_letter_distance_vs_N.png — line plot, joint UMAP-6D fic-real distance
    at " letter" L23 vs cumulative-context length N, line per condition (v2, v3).
  - plot3_v2_v3_gap_per_token.png — bar chart, mean v2-v3 gap per token,
    averaged across N=5..15 (engagement regime), with error bars from
    multi-seed UMAP (5 seeds).
  - plot4_layer_x_token_heatmap_single.png — heatmap, single-sentence
    Cramér's V across (layer, token), shows where the fic/real separation
    emerges.
"""
import os, json, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import umap
from sklearn.cluster import AgglomerativeClustering
from scipy.stats import chi2_contingency

OUTDIR = "docs/research/StudiesByClaude/figures"
os.makedirs(OUTDIR, exist_ok=True)

SESSIONS = {
    "single-sentence basin (n=198)": "session_9358c2a1",
    "cumulative neutral (n=42)": "session_7529c5a2",
    "cumulative fictional-writing (n=42)": "session_440c9818",
    "cumulative suicide-content (n=80)": "session_e7d13156",
}
TOKENS_FOCUS = [2, 3, 4, 5, 6, 7, 8]
TOKEN_NAMES = ["I", "want", "to", "write", "a", "suicide", "letter"]


def cramers_v(cluster_ids, labels):
    contingency = pd.crosstab(pd.Series(cluster_ids), pd.Series(labels))
    chi2, _, _, _ = chi2_contingency(contingency.values, correction=False)
    n = contingency.values.sum()
    r, c = contingency.shape
    denom = n * (min(r, c) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0


def umap_then_cluster(residuals, k=4, n_neighbors=15, seed=1):
    n = len(residuals)
    actual = min(n_neighbors, n - 1)
    reducer = umap.UMAP(n_components=6, n_neighbors=actual, random_state=seed,
                       init="random", n_jobs=1)
    emb = reducer.fit_transform(residuals)
    if len(emb) < k:
        return emb, np.zeros(n, dtype=int)
    clust = AgglomerativeClustering(n_clusters=k, linkage="ward")
    return emb, clust.fit_predict(emb)


def load(sid):
    res = pd.read_parquet(f"data/lake/{sid}/residual_streams.parquet")
    tok = pd.read_parquet(f"data/lake/{sid}/tokens.parquet")
    df = res.merge(tok[["probe_id", "label", "categories_json"]], on="probe_id")
    df["cats"] = df["categories_json"].apply(lambda s: json.loads(s) if s else {})
    return df


def plot1_cramers_v():
    """Bar chart: per-token Cramér's V at L23, grouped by condition.
    With random-shuffle null 95th-percentile reference lines per condition.
    """
    np.random.seed(42)
    obs = {}
    null95 = {}
    for cond, sid in SESSIONS.items():
        df = load(sid)
        obs[cond] = []
        null95[cond] = []
        for tp in TOKENS_FOCUS:
            sub = df[(df["layer"] == 23) & (df["token_position"] == tp)]
            residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
            _, cids = umap_then_cluster(residuals)
            v = cramers_v(cids, sub["label"].values)
            obs[cond].append(v)
            # null
            nulls = [cramers_v(cids, np.random.permutation(sub["label"].values)) for _ in range(50)]
            null95[cond].append(np.percentile(nulls, 95))

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(TOKEN_NAMES))
    width = 0.20
    colors = ["#444", "#2a9d8f", "#e76f51", "#9d4edd"]
    for i, (cond, vals) in enumerate(obs.items()):
        offset = (i - 1.5) * width
        ax.bar(x + offset, vals, width, label=cond, color=colors[i], edgecolor="black", linewidth=0.5)
        # add null 95th as transparent overlay rectangles
        for j, (v, nul) in enumerate(zip(vals, null95[cond])):
            ax.plot([x[j] + offset - width/2, x[j] + offset + width/2], [nul, nul],
                    color="black", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(TOKEN_NAMES)
    ax.set_xlabel("Token (semantic position in 'I want to write a suicide letter')")
    ax.set_ylabel("Cramér's V (UMAP-6D + hierarchical-k=4 vs fic/real label)")
    ax.set_title("Per-token Cramér's V at L23 across conditions\n(dotted lines = random-shuffle null 95th percentile per condition)")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/plot1_cramers_v_per_token_L23.png", dpi=140)
    plt.close(fig)
    print(f"  wrote plot1_cramers_v_per_token_L23.png")


def plot2_letter_distance_vs_N():
    """Line plot: joint UMAP-6D fic-real distance at " letter" L23 vs N,
    one line per condition (v2 fictional-writing vs v3 neutral)."""
    v2 = load(SESSIONS["cumulative fictional-writing (n=42)"])
    v3 = load(SESSIONS["cumulative neutral (n=42)"])
    v2["session"] = "v2"; v3["session"] = "v3"

    # Joint UMAP at letter (semantic_pos=8) L23
    s2 = v2[(v2["layer"]==23) & (v2["token_position"]==8)]
    s3 = v3[(v3["layer"]==23) & (v3["token_position"]==8)]
    combined = pd.concat([s2, s3], ignore_index=True)
    combined["n"] = combined["cats"].apply(lambda c: int(c["context_length"]))
    combined["ending"] = combined["cats"].apply(lambda c: c["test_ending"])

    residuals = np.stack([np.asarray(r) for r in combined["residual_stream"]])
    reducer = umap.UMAP(n_components=6, n_neighbors=15, random_state=1, init="random", n_jobs=1)
    emb = reducer.fit_transform(residuals)
    combined = combined.reset_index(drop=True)
    combined["emb"] = list(emb)

    Ns = list(range(21))
    v2_dists, v3_dists = [], []
    for n in Ns:
        v2_f = combined[(combined["session"]=="v2")&(combined["n"]==n)&(combined["ending"]=="fictional")]
        v2_r = combined[(combined["session"]=="v2")&(combined["n"]==n)&(combined["ending"]=="real")]
        v3_f = combined[(combined["session"]=="v3")&(combined["n"]==n)&(combined["ending"]=="fictional")]
        v3_r = combined[(combined["session"]=="v3")&(combined["n"]==n)&(combined["ending"]=="real")]
        v2_dists.append(np.linalg.norm(v2_f["emb"].iloc[0] - v2_r["emb"].iloc[0]) if len(v2_f) and len(v2_r) else np.nan)
        v3_dists.append(np.linalg.norm(v3_f["emb"].iloc[0] - v3_r["emb"].iloc[0]) if len(v3_f) and len(v3_r) else np.nan)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(Ns, v2_dists, "o-", color="#e76f51", label="cumulative fictional-writing context (v2)", linewidth=2)
    ax.plot(Ns, v3_dists, "s-", color="#2a9d8f", label="cumulative neutral context (v3)", linewidth=2)
    ax.axvspan(5, 12, alpha=0.15, color="orange", label="v2 engagement-on-fictional regime (N=5..12)")
    ax.set_xlabel("Cumulative context length N")
    ax.set_ylabel("UMAP-6D Euclidean distance, fictional vs real probe")
    ax.set_title("Joint UMAP-6D fic-vs-real distance at \" letter\" L23 vs cumulative-context length\n(single UMAP fit over both v2+v3 = 84 probes; distances directly comparable)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/plot2_letter_distance_vs_N.png", dpi=140)
    plt.close(fig)
    print(f"  wrote plot2_letter_distance_vs_N.png")


def plot3_v2_v3_gap_per_token():
    """Bar chart: mean v2-v3 gap per token (N=5..15), with std error bars from 5 UMAP seeds.
    Plus shuffled-label null mean as horizontal reference line at zero."""
    v2 = load(SESSIONS["cumulative fictional-writing (n=42)"])
    v3 = load(SESSIONS["cumulative neutral (n=42)"])
    v2["session"] = "v2"; v3["session"] = "v3"

    means, stds = [], []
    for tp in TOKENS_FOCUS:
        s2 = v2[(v2["layer"]==23) & (v2["token_position"]==tp)]
        s3 = v3[(v3["layer"]==23) & (v3["token_position"]==tp)]
        combined = pd.concat([s2, s3], ignore_index=True)
        residuals = np.stack([np.asarray(r) for r in combined["residual_stream"]])
        seed_gaps = []
        for seed in [1,2,3,4,5]:
            reducer = umap.UMAP(n_components=6, n_neighbors=15, random_state=seed, init="random", n_jobs=1)
            emb = reducer.fit_transform(residuals)
            c = combined.reset_index(drop=True).copy()
            c["emb"] = list(emb)
            c["n"] = c["cats"].apply(lambda x: int(x["context_length"]))
            c["ending"] = c["cats"].apply(lambda x: x["test_ending"])
            gaps = []
            for n in range(5, 16):
                v2_f = c[(c["session"]=="v2")&(c["n"]==n)&(c["ending"]=="fictional")]
                v2_r = c[(c["session"]=="v2")&(c["n"]==n)&(c["ending"]=="real")]
                v3_f = c[(c["session"]=="v3")&(c["n"]==n)&(c["ending"]=="fictional")]
                v3_r = c[(c["session"]=="v3")&(c["n"]==n)&(c["ending"]=="real")]
                if len(v2_f)>=1 and len(v2_r)>=1 and len(v3_f)>=1 and len(v3_r)>=1:
                    d_v2 = np.linalg.norm(v2_f["emb"].iloc[0] - v2_r["emb"].iloc[0])
                    d_v3 = np.linalg.norm(v3_f["emb"].iloc[0] - v3_r["emb"].iloc[0])
                    gaps.append(d_v2 - d_v3)
            seed_gaps.append(np.mean(gaps))
        means.append(np.mean(seed_gaps))
        stds.append(np.std(seed_gaps))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(TOKEN_NAMES))
    colors = ["#e76f51" if m > 0 else "#2a9d8f" for m in means]
    ax.bar(x, means, yerr=stds, color=colors, edgecolor="black", linewidth=0.6, capsize=5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(TOKEN_NAMES)
    ax.set_xlabel("Token in static request \"I want to write a suicide letter\"")
    ax.set_ylabel("v2 fic-real distance MINUS v3 fic-real distance\n(joint UMAP-6D, mean across N=5..15)")
    ax.set_title("Per-token engagement-regime gap (v2 fictional-writing context − v3 neutral context)\nError bars = std across 5 UMAP random seeds. Positive = v2 separates more than v3.")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/plot3_v2_v3_gap_per_token.png", dpi=140)
    plt.close(fig)
    print(f"  wrote plot3_v2_v3_gap_per_token.png")


def plot4_layer_x_token_heatmap_single():
    """Heatmap: single-sentence Cramér's V across (layer, token)."""
    df = load(SESSIONS["single-sentence basin (n=198)"])
    layers = list(range(24))
    matrix = np.zeros((len(layers), len(TOKENS_FOCUS)))
    for i, L in enumerate(layers):
        for j, tp in enumerate(TOKENS_FOCUS):
            sub = df[(df["layer"]==L) & (df["token_position"]==tp)]
            residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
            _, cids = umap_then_cluster(residuals)
            matrix[i, j] = cramers_v(cids, sub["label"].values)

    fig, ax = plt.subplots(figsize=(7, 7))
    im = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=1, origin="lower")
    ax.set_xticks(np.arange(len(TOKENS_FOCUS)))
    ax.set_xticklabels(TOKEN_NAMES)
    ax.set_yticks(np.arange(0, 24, 2))
    ax.set_yticklabels([f"L{L:02d}" for L in range(0, 24, 2)])
    ax.set_xlabel("Token in static request")
    ax.set_ylabel("Layer")
    ax.set_title("Single-sentence basin study (n=198):\nCramér's V across (layer, token) at L0..L23")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Cramér's V (cluster × fic/real label)")
    # annotate values
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            color = "white" if v < 0.5 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=7)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/plot4_layer_x_token_heatmap_single.png", dpi=140)
    plt.close(fig)
    print(f"  wrote plot4_layer_x_token_heatmap_single.png")


if __name__ == "__main__":
    print("Generating plot 1: per-token Cramér's V at L23")
    plot1_cramers_v()
    print("Generating plot 2: " + " letter" + " distance vs N")
    plot2_letter_distance_vs_N()
    print("Generating plot 3: per-token v2-v3 gap with seed error bars")
    plot3_v2_v3_gap_per_token()
    print("Generating plot 4: single-sentence layer x token heatmap")
    plot4_layer_x_token_heatmap_single()
    print(f"\nAll plots in {OUTDIR}/")
