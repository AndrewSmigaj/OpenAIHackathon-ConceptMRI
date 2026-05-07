#!/usr/bin/env python3
"""
Combined analysis across all 4 per-token sessions.

Produces headline tables for the per-token separation report:
  Table A: Cramér's V at L23 per token, per session.
  Table B: per-N UMAP-6D fic-vs-real distance per token, for v2 and v3.

Also writes a JSON dump of the per-token per-N distances so plots can be
made later without re-running clustering.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

import umap
from sklearn.cluster import AgglomerativeClustering
from scipy.stats import chi2_contingency


SESSIONS = {
    "single": "session_9358c2a1",   # 198 single-sentence basin probes
    "v3": "session_7529c5a2",       # 42 cumulative neutral
    "v2": "session_440c9818",       # 42 cumulative fictional-writing
    "v1": "session_e7d13156",       # 80 cumulative suicide-content
}

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

# Tokens we focus on (drop redundant target=1 since it's the same absolute pos as " want"=3)
TOKENS_FOCUS = [2, 3, 4, 5, 6, 7, 8]


def cramers_v(cluster_ids: np.ndarray, labels: np.ndarray) -> float:
    contingency = pd.crosstab(pd.Series(cluster_ids), pd.Series(labels))
    chi2, _, _, _ = chi2_contingency(contingency.values, correction=False)
    n = contingency.values.sum()
    r, c = contingency.shape
    denom = n * (min(r, c) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0


def umap_then_cluster(residuals: np.ndarray, k: int = 4, n_neighbors: int = 15, seed: int = 1):
    n = len(residuals)
    actual_neighbors = min(n_neighbors, n - 1)
    reducer = umap.UMAP(
        n_components=6, n_neighbors=actual_neighbors, random_state=seed,
        init="random", n_jobs=1,
    )
    emb = reducer.fit_transform(residuals)
    if len(emb) < k:
        return emb, np.zeros(n, dtype=int)
    clust = AgglomerativeClustering(n_clusters=k, linkage="ward")
    cids = clust.fit_predict(emb)
    return emb, cids


def load_session(sid):
    res = pd.read_parquet(f"data/lake/{sid}/residual_streams.parquet")
    tok = pd.read_parquet(f"data/lake/{sid}/tokens.parquet")
    cols = ["probe_id", "label"]
    if "categories_json" in tok.columns:
        cols.append("categories_json")
    df = res.merge(tok[cols], on="probe_id")
    if "categories_json" in df.columns:
        df["cats"] = df["categories_json"].apply(lambda s: json.loads(s) if s else {})
    return df


def cramers_at_layer(df, layer):
    """Compute Cramér's V per token at a given layer for all probes in the session."""
    out = {}
    for tp in TOKENS_FOCUS:
        sub = df[(df["layer"] == layer) & (df["token_position"] == tp)]
        if len(sub) < 4:
            continue
        residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
        labels = sub["label"].values
        _, cids = umap_then_cluster(residuals, k=4, n_neighbors=15)
        out[TOKEN_LABELS[tp]] = cramers_v(cids, labels)
    return out


def per_n_distance(df, layer, tag):
    """Per-N UMAP-6D fic-vs-real distance, per token.

    For v2/v3: n=context_length (from cats), ending=test_ending (from cats).
    For v1: n=cumulative_n (from cats), ending=label (already set to
            latest_sentence_kind during capture).
    """
    out = {}
    if "cats" not in df.columns:
        return out
    for tp in TOKENS_FOCUS:
        sub = df[(df["layer"] == layer) & (df["token_position"] == tp)].copy()
        if len(sub) < 4:
            continue
        residuals = np.stack([np.asarray(r) for r in sub["residual_stream"]])
        emb, _ = umap_then_cluster(residuals, k=4, n_neighbors=15)
        sub = sub.reset_index(drop=True).copy()
        sub["emb"] = list(emb)
        if tag == "v1":
            sub["n"] = sub["cats"].apply(lambda c: int(c.get("cumulative_n", 0)))
            sub["ending"] = sub["label"]
        else:
            sub["n"] = sub["cats"].apply(lambda c: int(c.get("context_length", 0)))
            sub["ending"] = sub["cats"].apply(lambda c: c.get("test_ending"))
        per_n = {}
        for n in sorted(sub["n"].unique()):
            f = sub[(sub["n"] == n) & (sub["ending"] == "fictional")]
            r = sub[(sub["n"] == n) & (sub["ending"] == "real")]
            if len(f) >= 1 and len(r) >= 1:
                # v1 may have multiple probes per (n, ending) due to ordering — average distance to opposite-ending centroid
                # Simplest: average pairwise distance between fic and real probes at same n.
                f_arr = np.stack(list(f["emb"].values))
                r_arr = np.stack(list(r["emb"].values))
                # mean pairwise
                d = np.linalg.norm(f_arr.mean(0) - r_arr.mean(0))
                per_n[int(n)] = float(d)
        out[TOKEN_LABELS[tp]] = per_n
    return out


def main(layers=(8, 16, 23)):
    results = {}
    for tag, sid in SESSIONS.items():
        path = Path(f"data/lake/{sid}/residual_streams.parquet")
        if not path.exists():
            print(f"  [skip] {tag} ({sid}) — not found")
            continue
        print(f"\n=== {tag} ({sid}) ===")
        df = load_session(sid)
        results[tag] = {"session_id": sid, "n_probes": df["probe_id"].nunique(),
                        "by_layer": {}}
        for L in layers:
            print(f"\n--- L{L:02d} ---")
            print("Per-token Cramér's V (cluster × label):")
            cv = cramers_at_layer(df, L)
            for tok, v in cv.items():
                print(f"  {tok:14s} {v:.3f}")
            results[tag]["by_layer"][f"L{L}"] = {"cramers_v": cv}

            if tag in ("v2", "v3", "v1"):
                pn = per_n_distance(df, L, tag)
                results[tag]["by_layer"][f"L{L}"]["per_n_distance"] = pn

    # Save raw results
    with open("docs/scratchpad/per_token_combined_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved combined results to docs/scratchpad/per_token_combined_results.json")


if __name__ == "__main__":
    main()
