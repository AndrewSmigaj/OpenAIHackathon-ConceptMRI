#!/usr/bin/env python3
"""
Per-token separation analysis on multi-token capture sessions.

Reads residual_streams.parquet for each session, computes UMAP-6D +
hierarchical-k=4 clustering at each (layer, token_position), and reports
Cramér's V (cluster × ground-truth label) per cell.

For cumulative-context sessions, also computes per-N UMAP-6D Euclidean
distance between fictional and real probes (the "separation score per N").

Usage:
    .venv/bin/python docs/scratchpad/per_token_analysis.py <session_id>

Output: prints tables; optionally writes findings rows to
docs/research/StudiesByClaude/per_token_separation_findings.md
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path

import umap
from sklearn.cluster import AgglomerativeClustering
from scipy.stats import chi2_contingency


# ---------- helpers ----------

TOKEN_LABELS = {
    1: "want(target)",
    2: "I",
    3: " want",
    4: " to",
    5: " write",
    6: " a",
    7: " suicide",
    8: " letter",
}


def cramers_v(cluster_ids: np.ndarray, labels: np.ndarray) -> float:
    """Cramér's V between cluster_id (k=4) and binary label (fictional/real)."""
    contingency = pd.crosstab(pd.Series(cluster_ids), pd.Series(labels))
    chi2, _, _, _ = chi2_contingency(contingency.values, correction=False)
    n = contingency.values.sum()
    r, c = contingency.shape
    denom = n * (min(r, c) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0


def umap_then_cluster(residuals: np.ndarray, k: int = 4, n_neighbors: int = 15, seed: int = 1):
    """UMAP-6D + hierarchical-k clustering. Returns (embedding, cluster_ids)."""
    n = len(residuals)
    actual_neighbors = min(n_neighbors, n - 1)
    reducer = umap.UMAP(
        n_components=6, n_neighbors=actual_neighbors, random_state=seed, init="random",
        n_jobs=1,
    )
    emb = reducer.fit_transform(residuals)
    if len(emb) < k:
        return emb, np.zeros(n, dtype=int)
    clust = AgglomerativeClustering(n_clusters=k, linkage="ward")
    cids = clust.fit_predict(emb)
    return emb, cids


def load_session(session_id: str):
    """Load residuals + tokens for a session, return dataframe with parsed categories."""
    res = pd.read_parquet(f"data/lake/{session_id}/residual_streams.parquet")
    tok = pd.read_parquet(f"data/lake/{session_id}/tokens.parquet")
    cols = ["probe_id", "label"]
    if "categories_json" in tok.columns:
        cols.append("categories_json")
    df = res.merge(tok[cols], on="probe_id")
    if "categories_json" in df.columns:
        df["cats"] = df["categories_json"].apply(lambda s: json.loads(s) if s else {})
    return df


# ---------- analysis ----------

def per_token_cramers_v(df: pd.DataFrame, layer: int) -> pd.DataFrame:
    """For one layer, compute Cramér's V per token across all probes in the session."""
    rows = []
    for tp in sorted(df["token_position"].unique()):
        sub = df[(df["layer"] == layer) & (df["token_position"] == tp)]
        if len(sub) < 4:
            continue
        residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
        labels = sub["label"].values
        _, cids = umap_then_cluster(residuals, k=4, n_neighbors=15)
        v = cramers_v(cids, labels)
        rows.append({"layer": layer, "token_position": tp, "token_label": TOKEN_LABELS.get(tp, str(tp)),
                     "n_probes": len(sub), "cramers_v": v})
    return pd.DataFrame(rows)


def per_n_umap_distance(df: pd.DataFrame, layer: int, n_key: str = "context_length",
                       ending_key: str = "test_ending") -> pd.DataFrame:
    """For cumulative-context sessions: per-N UMAP-6D distance between fic/real probes per token."""
    if "cats" not in df.columns:
        return pd.DataFrame()
    rows = []
    for tp in sorted(df["token_position"].unique()):
        sub = df[(df["layer"] == layer) & (df["token_position"] == tp)].copy()
        if len(sub) < 4:
            continue
        residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
        emb, _ = umap_then_cluster(residuals, k=4, n_neighbors=15)
        sub = sub.reset_index(drop=True).copy()
        sub["emb"] = list(emb)
        sub["n"] = sub["cats"].apply(lambda c: int(c.get(n_key, 0)))
        sub["ending"] = sub["cats"].apply(lambda c: c.get(ending_key))
        for n in sorted(sub["n"].unique()):
            f = sub[(sub["n"] == n) & (sub["ending"] == "fictional")]
            r = sub[(sub["n"] == n) & (sub["ending"] == "real")]
            if len(f) >= 1 and len(r) >= 1:
                dist = np.linalg.norm(f["emb"].iloc[0] - r["emb"].iloc[0])
                rows.append({"layer": layer, "token_position": tp,
                            "token_label": TOKEN_LABELS.get(tp, str(tp)),
                            "n": n, "umap_distance": dist})
    return pd.DataFrame(rows)


def main(session_id: str, layers=(8, 16, 23), with_per_n=True):
    df = load_session(session_id)
    print(f"\n=== session {session_id} ===")
    print(f"rows: {len(df)}, probes: {df['probe_id'].nunique()}, "
          f"token_positions: {sorted(df['token_position'].unique().tolist())}")

    for L in layers:
        print(f"\n--- L{L:02d} per-token Cramér's V (cluster × label) ---")
        out = per_token_cramers_v(df, L)
        if len(out):
            print(out.to_string(index=False))

        if with_per_n and "cats" in df.columns:
            n_table = per_n_umap_distance(df, L)
            if len(n_table):
                pivot = n_table.pivot(index="n", columns="token_label", values="umap_distance")
                print(f"\n  Per-N UMAP-6D fic-vs-real distance at L{L:02d}:")
                print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: per_token_analysis.py <session_id> [layer ...]")
        sys.exit(1)
    sid = sys.argv[1]
    layers = [int(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else (8, 16, 23)
    main(sid, layers=layers)
