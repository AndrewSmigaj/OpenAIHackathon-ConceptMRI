#!/usr/bin/env python3
"""
Family C+D basin-projection analysis (paper protocol).

Methodology (matches Phase 3 for Family B):
1. Load basin study (session_9358c2a1) residuals at L23, last-occurrence-only.
2. Re-fit UMAP-6D, n_neighbors=15, random_state=42, min_dist=0.1.
3. Compute basin centroids in MY UMAP space using K=3 schema's
   cluster assignments (cluster 0 = distress, cluster 1 = fictional).
4. For each Family C/D session: extract test ending's "want" L23 residual
   (token_position=1 of static_substring), transform through UMAP, project
   onto basin axis (distress - fictional). Higher = closer to distress.

Output: per-session mean projection ± std for each test_ending_kind.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import umap


BASIN_SID = "session_9358c2a1"
SCHEMA = "suicide_letter_basin_k3_n15"
TARGET_LAYER = 23
RNG = 42


def load_basin_residuals():
    """Load basin study residuals at L23, last-occurrence only (target word)."""
    df = pd.read_parquet(f"data/lake/{BASIN_SID}/residual_streams.parquet")
    # last-occurrence-only ⇒ token_position = the static substring's last `want` (=1?)
    # For basin study (single sentences), the only "want" is at the target.
    # capture_static_substring="I want to write a suicide letter" → positions 0..7.
    # Position 1 = "want" (target token).
    sub = df[(df["layer"] == TARGET_LAYER) & (df["token_position"] == 1)].copy()
    # Stack residuals into 2D array
    arr = np.stack(sub["residual_stream"].apply(np.asarray).to_numpy())
    return sub.reset_index(drop=True), arr


def load_probe_assignments():
    """Map probe_id -> cluster_id at L23 from basin schema."""
    p = Path(f"data/lake/{BASIN_SID}/clusterings/{SCHEMA}/probe_assignments.json")
    d = json.loads(p.read_text())
    # probe_assignments format: {probe_id: {layer: cluster_id, ...}, ...}
    # Or could be {layer: {probe_id: cluster_id}}
    sample_key = next(iter(d.keys()))
    sample_val = d[sample_key]
    if isinstance(sample_val, dict) and str(TARGET_LAYER) in sample_val:
        # First form: probe_id -> {layer: cid}
        return {pid: int(cs[str(TARGET_LAYER)]) for pid, cs in d.items()}
    elif isinstance(sample_val, dict):
        # Second form: layer -> {probe_id: cid}
        return {pid: int(cid) for pid, cid in d.get(str(TARGET_LAYER), {}).items()}
    raise ValueError(f"unexpected probe_assignments format: {type(sample_val)}")


def main():
    print("Loading basin residuals...")
    basin_df, basin_arr = load_basin_residuals()
    print(f"  basin probes at L23 token 1: {len(basin_df)}, dim={basin_arr.shape[1]}")

    print("Fitting UMAP-6D...")
    reducer = umap.UMAP(n_components=6, n_neighbors=15, min_dist=0.1, random_state=RNG)
    basin_umap = reducer.fit_transform(basin_arr)

    print("Loading basin probe-cluster assignments...")
    pid_to_cluster = load_probe_assignments()
    basin_df["cluster"] = basin_df["probe_id"].map(pid_to_cluster)
    print(f"  cluster distribution at L23:")
    print(basin_df["cluster"].value_counts().to_string())

    # Compute centroids
    centroids = {}
    for c in (0, 1, 2):
        mask = basin_df["cluster"] == c
        if mask.sum() == 0:
            continue
        centroids[c] = basin_umap[mask.to_numpy()].mean(axis=0)
        print(f"  centroid C{c} (n={mask.sum()}): first 3 dims = {centroids[c][:3]}")

    # Basin axis: distress (cluster 0) - fictional (cluster 1)
    # Per Phase 3: cluster 0 = distress, cluster 1 = fictional
    fic_centroid = centroids[1]
    distress_centroid = centroids[0]
    axis = distress_centroid - fic_centroid
    axis_len = np.linalg.norm(axis)
    axis_unit = axis / axis_len
    print(f"\nBasin axis length: {axis_len:.3f}")
    print(f"  fictional (C1) projection on axis = 0; distress (C0) projection on axis = 1")

    # For projection scaling, anchor at fic centroid
    def project(umap_pts):
        rel = umap_pts - fic_centroid
        return (rel @ axis_unit) / axis_len  # 0 = fic, 1 = distress

    # Process Family C/D sessions
    SESSIONS = {
        "session_4fb808de": "writing_craft_n10",
        "session_d4be96d2": "writing_craft_n20",
        "session_96b2e49d": "neutral_n10",
        "session_cc362d6b": "neutral_n20",
        "session_7d2758ad": "cooking_craft_n10",
        "session_284fc724": "cooking_craft_n20",
        "session_9105437f": "music_craft_n10",
        "session_1f0db53a": "music_craft_n20",
        "session_8c100e5c": "programming_craft_n10",
        "session_b0fd8ec7": "programming_craft_n20",
        "session_056afb78": "i_need_help_n10",
        "session_4483e66b": "i_need_help_n20",
        "session_5094c0ea": "declarative_n10",
        "session_31542e91": "declarative_n20",
        "session_8af588ab": "fresh_craft_n10",
        "session_ebe87382": "fresh_craft_n20",
        "session_6d28eb36": "first_person_no_help_n10",
        "session_e66e901f": "first_person_no_help_n20",
        "session_ec496b51": "i_need_help_seq_fic_then_real_n10",
        "session_7678c723": "i_need_help_seq_fic_then_real_n20",
        "session_546cabec": "i_need_help_seq_real_then_fic_n10",
        "session_a2307a59": "i_need_help_seq_real_then_fic_n20",
        "session_ab2d4441": "paraphrase_writing_craft_n10",
        "session_90dca93a": "paraphrase_writing_craft_n20",
    }

    rows = []
    for sid, name in SESSIONS.items():
        print(f"\n--- {name} ({sid}) ---")
        # Load tokens for label
        tokens = pd.read_parquet(f"data/lake/{sid}/tokens.parquet")
        residuals = pd.read_parquet(f"data/lake/{sid}/residual_streams.parquet")
        # last-occurrence at position 1 of static substring (test ending's "want")
        sub = residuals[(residuals["layer"] == TARGET_LAYER) & (residuals["token_position"] == 1)].copy()
        if len(sub) == 0:
            print(f"  WARNING: no residuals at L{TARGET_LAYER} token 1")
            continue
        arr = np.stack(sub["residual_stream"].apply(np.asarray).to_numpy())
        umap_pts = reducer.transform(arr)
        proj = project(umap_pts)
        sub["proj"] = proj
        # Merge label from tokens
        sub = sub.merge(tokens[["probe_id", "label"]], on="probe_id", how="left")
        # Aggregate by label
        for label, g in sub.groupby("label"):
            mean = float(g["proj"].mean())
            std = float(g["proj"].std())
            print(f"  {label}: n={len(g)}, proj mean={mean:+.3f} ± {std:.3f}")
            rows.append({"set": name, "label": label, "n": len(g), "mean_proj": mean, "std_proj": std})

    # Save
    out = Path("docs/scratchpad/family_c_basin_projections.json")
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
