#!/usr/bin/env python3
"""
Generic dimensionality reduction service supporting PCA and UMAP.
Computes reduction on demand from raw embeddings — no pre-computation.
"""

import json
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

# Source config: maps source name to parquet filename and column name
SOURCE_CONFIG = {
    "expert_output": {
        "parquet_file": "embeddings.parquet",
        "column": "embedding",
    },
    "residual_stream": {
        "parquet_file": "residual_streams.parquet",
        "column": "residual_stream",
    },
}


class ReductionService:
    """On-demand dimensionality reduction from raw embeddings."""

    def __init__(self, n_components: int = 128):
        self.n_components = n_components

    def reduce_on_demand(
        self,
        session_ids: list,
        layers: list,
        data_lake_path: str,
        source: str = "expert_output",
        method: str = "umap",
        n_components: int = 3,
        steps: list = None,
        last_occurrence_only: bool = False,
    ) -> list:
        """
        On-demand dimensionality reduction for one or more sessions.

        Loads raw embeddings, concatenates across sessions, fits PCA/UMAP
        per layer, and returns point dicts with coordinates + probe metadata.
        """
        from core.parquet_reader import read_records
        from schemas.tokens import ProbeRecord
        from services.experiments.token_filters import pick_last_occurrence_from_meta

        config = SOURCE_CONFIG.get(source)
        if not config:
            raise ValueError(f"Unknown source '{source}'")
        if method not in ("pca", "umap"):
            raise ValueError(f"Unknown method '{method}'")

        # Collect raw embeddings and token metadata from all sessions
        all_embeddings = []  # list of (session_id, probe_id, layer, embedding_vector)
        token_meta = {}  # probe_id -> {target_word, label, session_id}

        for sid in session_ids:
            session_path = Path(data_lake_path) / f"session_{sid}"
            if not session_path.exists():
                session_path = Path(data_lake_path) / sid
                if not session_path.exists():
                    raise ValueError(f"Session {sid} not found")

            # Load raw embeddings
            source_path = session_path / config["parquet_file"]
            if not source_path.exists():
                raise FileNotFoundError(f"Source data not found: {source_path}")

            df = pd.read_parquet(source_path)
            column_name = config["column"]

            # Load token records for metadata
            tokens_path = session_path / "tokens.parquet"
            if tokens_path.exists():
                token_records = read_records(str(tokens_path), ProbeRecord)
                for t in token_records:
                    key = f"{sid[:8]}_{t.probe_id}" if len(session_ids) > 1 else t.probe_id
                    turn_id = t.turn_id
                    step = turn_id if turn_id is not None else t.sentence_index
                    token_meta[key] = {
                        "target_word": t.target_word,
                        "label": t.label,
                        "session_id": sid,
                        "categories_json": t.categories_json,
                        "step": step,
                        "input_text": t.input_text,
                        "target_char_offset": t.target_char_offset,
                    }

            # Filter to target token (position=1) and requested layers
            mask = df["layer"].isin(layers)
            if "token_position" in df.columns:
                mask = mask & (df["token_position"] == 1)
            filtered = df[mask]

            prefix = f"{sid[:8]}_" if len(session_ids) > 1 else ""
            for _, row in filtered.iterrows():
                all_embeddings.append({
                    "probe_id": prefix + row["probe_id"],
                    "layer": row["layer"],
                    "vector": np.array(row[column_name], dtype=np.float32),
                })

        # Filter by sequence step if requested
        if steps is not None:
            allowed = {pid for pid, m in token_meta.items() if m.get("step") in steps}
            all_embeddings = [e for e in all_embeddings if e["probe_id"] in allowed]

        # Keep only the last target-word occurrence per (session_id, input_text, target_word)
        if last_occurrence_only:
            keep_ids = pick_last_occurrence_from_meta(token_meta)
            all_embeddings = [e for e in all_embeddings if e["probe_id"] in keep_ids]

        if not all_embeddings:
            return []

        # Group by layer and reduce
        emb_df = pd.DataFrame(all_embeddings)
        points = []

        for layer in sorted(layers):
            layer_data = emb_df[emb_df["layer"] == layer]
            if layer_data.empty:
                continue

            n_samples = len(layer_data)
            hidden_size = len(layer_data.iloc[0]["vector"])
            states = np.zeros((n_samples, hidden_size), dtype=np.float32)
            for idx, (_, row) in enumerate(layer_data.iterrows()):
                states[idx] = row["vector"]

            # Fit reducer
            actual_components = min(n_components, n_samples - 1, hidden_size)
            if actual_components < 1:
                actual_components = 1

            if method == "umap" and n_samples < 4:
                reducer = PCA(n_components=actual_components, random_state=42)
            else:
                reducer = self._create_reducer(method, actual_components)

            coords = reducer.fit_transform(states)

            # Build point dicts
            for idx, (_, row) in enumerate(layer_data.iterrows()):
                pid = row["probe_id"]
                meta = token_meta.get(pid, {})
                point = {
                    "probe_id": pid,
                    "session_id": meta.get("session_id", ""),
                    "layer": int(layer),
                    "x": float(coords[idx, 0]) if coords.shape[1] > 0 else 0.0,
                    "coordinates": [float(coords[idx, c]) for c in range(coords.shape[1])],
                    "target_word": meta.get("target_word", ""),
                    "label": meta.get("label"),
                    "categories": json.loads(meta["categories_json"]) if meta.get("categories_json") else None,
                    "step": meta.get("step"),
                }
                if coords.shape[1] > 1:
                    point["y"] = float(coords[idx, 1])
                if coords.shape[1] > 2:
                    point["z"] = float(coords[idx, 2])
                points.append(point)

        return points

    def _create_reducer(self, method: str, n_components: Optional[int] = None):
        """Create a reducer instance for the given method."""
        n = n_components or self.n_components

        if method == "pca":
            return PCA(n_components=n, random_state=42)
        elif method == "umap":
            import umap
            return umap.UMAP(
                n_components=n,
                random_state=42,
                n_neighbors=min(15, max(2, n - 1)),
                min_dist=0.1,
            )
        else:
            raise ValueError(f"Unknown method: {method}")
