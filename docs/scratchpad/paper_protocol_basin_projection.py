#!/usr/bin/env python3
"""Paper-protocol basin-projection analysis on the new unified-path data.

For each probe family (polysemy, suicide letter):
- Re-fit UMAP-6D on basin study residuals at L23 (target token only).
- Compute basin centroids in this UMAP using the basin schema's K=3/K=6
  cluster assignments at L23.
- Project each paper-protocol session's residual at the target word's
  position through the same UMAP, project on basin axis (B-A direction).
- Aggregate per (direction, position) across the 10 orderings.

For cache-on captures, each step's residual at target word lives at a
specific token position in that step's NEW tokens. We extract the
residual at the target_token_position field, which the capture path
already stored correctly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import umap


BASIN_LAYER = 23
RNG = 42


def _load_basin_residuals_l23(source_sid: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Load L23 residuals at semantic_pos=1 (target token) for the basin study."""
    df = pd.read_parquet(f"data/lake/{source_sid}/residual_streams.parquet")
    sub = df[(df["layer"] == BASIN_LAYER) & (df["token_position"] == 1)].copy()
    arr = np.stack(sub["residual_stream"].apply(np.asarray).to_numpy())
    return sub.reset_index(drop=True), arr


def _load_probe_assignments_l23(source_sid: str, schema: str) -> dict[str, int]:
    """probe_id -> cluster_id at L23 from basin schema."""
    p = Path(f"data/lake/{source_sid}/clusterings/{schema}/probe_assignments.json")
    d = json.loads(p.read_text())
    sample_pid = next(iter(d.keys()))
    sample_val = d[sample_pid]
    if isinstance(sample_val, dict) and str(BASIN_LAYER) in sample_val:
        return {pid: int(cs[str(BASIN_LAYER)]) for pid, cs in d.items()}
    return {pid: int(cid) for pid, cid in d.get(str(BASIN_LAYER), {}).items()}


def analyze_family(name: str, source_sid: str, schema: str,
                   cluster_a: int, cluster_b: int,
                   session_log_filter) -> list[dict]:
    """Run basin-projection trajectory for one probe family."""
    print(f"\n=== {name} ({source_sid} / {schema}) — A={cluster_a} B={cluster_b} ===")
    basin_df, basin_arr = _load_basin_residuals_l23(source_sid)
    print(f"basin probes at L23 token 1: {len(basin_df)}")

    reducer = umap.UMAP(n_components=6, n_neighbors=15, min_dist=0.1, random_state=RNG)
    basin_umap = reducer.fit_transform(basin_arr)

    pid_to_cluster = _load_probe_assignments_l23(source_sid, schema)
    basin_df["cluster"] = basin_df["probe_id"].map(pid_to_cluster)

    # Compute centroids for cluster A and B in UMAP space
    a_mask = (basin_df["cluster"] == cluster_a).to_numpy()
    b_mask = (basin_df["cluster"] == cluster_b).to_numpy()
    centroid_a = basin_umap[a_mask].mean(axis=0)
    centroid_b = basin_umap[b_mask].mean(axis=0)
    axis = centroid_b - centroid_a
    axis_len = np.linalg.norm(axis)
    axis_unit = axis / axis_len
    print(f"  cluster A (n={a_mask.sum()}), B (n={b_mask.sum()}); axis length = {axis_len:.3f}")

    def project(arr2d):
        upts = reducer.transform(arr2d)
        rel = upts - centroid_a
        return (rel @ axis_unit) / axis_len  # 0 = A basin, 1 = B basin

    # Load chain log for this family
    log = pd.read_csv("docs/scratchpad/paper_protocol_log.tsv", sep="\t")
    fam_rows = log[session_log_filter(log)]
    print(f"  found {len(fam_rows)} sessions in chain log")

    all_points = []
    for _, row in fam_rows.iterrows():
        sid = row["new_session"]
        ordering = int(row["ord"])
        direction = row["dir"]
        tok = pd.read_parquet(f"data/lake/{sid}/tokens.parquet")
        res = pd.read_parquet(f"data/lake/{sid}/residual_streams.parquet")
        # For cache-on captures, residuals are stored at semantic position 1 (the target token)
        l23 = res[(res["layer"] == BASIN_LAYER) & (res["token_position"] == 1)]
        if len(l23) != len(tok):
            print(f"    WARN {sid}: tokens={len(tok)} but L23 residuals={len(l23)}")
            continue
        l23 = l23.merge(tok[["probe_id", "sentence_index", "label"]], on="probe_id")
        l23 = l23.sort_values("sentence_index")
        arr = np.stack(l23["residual_stream"].apply(np.asarray).to_numpy())
        proj = project(arr)
        for i, (pos, regime, p) in enumerate(zip(l23["sentence_index"], l23["label"], proj)):
            all_points.append({
                "ordering": ordering,
                "direction": direction,
                "position": int(pos),
                "regime": regime,
                "projection": float(p),
            })

    return all_points


def main():
    all_results = []

    # POLYSEMY (harmony basin)
    pts = analyze_family(
        "POLYSEMY", "session_e2be37dd", "tank_polysemy_basin_harmony_k6_n15",
        cluster_a=3, cluster_b=4,  # aquarium=A (C3 92%), vehicle=B (C4 97%)
        session_log_filter=lambda log: log["family"] == "polysemy_h",
    )
    for p in pts:
        p["probe_family"] = "polysemy"
    all_results.extend(pts)

    # SUICIDE LETTER
    pts = analyze_family(
        "SUICIDE LETTER", "session_9358c2a1", "suicide_letter_basin_k3_n15",
        cluster_a=1, cluster_b=0,  # fictional=A, distress=B
        session_log_filter=lambda log: log["family"] == "suicide",
    )
    for p in pts:
        p["probe_family"] = "suicide"
    all_results.extend(pts)

    # Save raw points
    out_json = "docs/scratchpad/paper_protocol_basin_points.json"
    Path(out_json).write_text(json.dumps(all_results, indent=2))
    print(f"\nSaved {len(all_results)} points -> {out_json}")

    # Aggregate: mean ± std per (probe_family, direction, position) across orderings
    df = pd.DataFrame(all_results)
    print("\n=== Trajectory summary (mean ± std at key positions) ===")
    for fam in ("polysemy", "suicide"):
        for direction in ("block_ab", "block_ba"):
            sub = df[(df["probe_family"] == fam) & (df["direction"] == direction)]
            if len(sub) == 0:
                continue
            agg = sub.groupby("position")["projection"].agg(["mean", "std", "count"])
            print(f"\n{fam.upper()} / {direction}:")
            print(f"  pos 1:  {agg.loc[0, 'mean']:+.3f} ± {agg.loc[0, 'std']:.3f}  (n={agg.loc[0,'count']:.0f})")
            print(f"  pos 10: {agg.loc[9, 'mean']:+.3f} ± {agg.loc[9, 'std']:.3f}")
            print(f"  pos 20: {agg.loc[19, 'mean']:+.3f} ± {agg.loc[19, 'std']:.3f}  (regime boundary)")
            print(f"  pos 30: {agg.loc[29, 'mean']:+.3f} ± {agg.loc[29, 'std']:.3f}")
            print(f"  pos 40: {agg.loc[39, 'mean']:+.3f} ± {agg.loc[39, 'std']:.3f}")


if __name__ == "__main__":
    main()
