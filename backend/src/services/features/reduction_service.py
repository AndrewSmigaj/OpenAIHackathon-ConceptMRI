#!/usr/bin/env python3
"""
Generic dimensionality reduction service supporting PCA and UMAP.
Replaces the PCA-only service with switchable reduction methods and embedding sources.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

# Source config: maps source name to parquet filename and column name
SOURCE_CONFIG = {
    "expert_output": {
        "parquet_file": "expert_output_states.parquet",
        "column": "expert_output_state",
    },
    "residual_stream": {
        "parquet_file": "residual_streams.parquet",
        "column": "residual_stream",
    },
}


class ReductionService:
    """Generate dimensionality-reduced features from expert output or residual stream data."""

    def __init__(self, n_components: int = 128):
        self.n_components = n_components
        self.models = {}  # keyed by "{method}_{layer}_{position}"

    def generate_features(
        self,
        session_id: str,
        data_lake_path: str,
        source: str = "expert_output",
        method: str = "pca",
    ) -> str:
        """
        Generate reduced features for a capture session.

        Args:
            session_id: Capture session ID
            data_lake_path: Path to data lake
            source: "expert_output" or "residual_stream"
            method: "pca" or "umap"

        Returns:
            Path to generated features parquet file
        """
        if source not in SOURCE_CONFIG:
            raise ValueError(f"Unknown source '{source}', must be one of {list(SOURCE_CONFIG.keys())}")
        if method not in ("pca", "umap"):
            raise ValueError(f"Unknown method '{method}', must be 'pca' or 'umap'")

        config = SOURCE_CONFIG[source]
        session_path = Path(data_lake_path) / f"session_{session_id}"

        # Read source data
        source_path = session_path / config["parquet_file"]
        if not source_path.exists():
            raise FileNotFoundError(f"Source data not found: {source_path}")

        logger.info(f"Loading {source} data from {source_path}")
        df = pd.read_parquet(source_path)
        column_name = config["column"]

        # Create reducer
        reducer = self._create_reducer(method)

        # Group by layer and token position to fit models
        feature_records = []

        for layer in sorted(df["layer"].unique()):
            for token_position in [0, 1]:
                mask = (df["layer"] == layer) & (df["token_position"] == token_position)
                layer_pos_df = df[mask]

                if layer_pos_df.empty:
                    logger.warning(f"No data for layer {layer}, position {token_position}, skipping")
                    continue

                n_samples = len(layer_pos_df)
                n_components_actual = min(n_samples, self.n_components)

                # Build state matrix
                hidden_size = len(layer_pos_df.iloc[0][column_name])
                states = np.zeros((n_samples, hidden_size), dtype=np.float32)
                for idx, (_, row) in enumerate(layer_pos_df.iterrows()):
                    states[idx] = np.array(row[column_name], dtype=np.float32)

                logger.info(
                    f"Layer {layer}, pos {token_position}: "
                    f"{method.upper()} on {states.shape[0]} samples of dim {states.shape[1]}"
                )

                # Fit and transform
                if method == "umap" and n_samples < 4:
                    logger.warning(f"Layer {layer}, pos {token_position}: too few samples for UMAP ({n_samples}), using PCA fallback")
                    local_reducer = PCA(n_components=n_components_actual, random_state=42)
                else:
                    local_reducer = self._create_reducer(method, n_components_actual)

                features = local_reducer.fit_transform(states)

                # Pad with zeros if we had to reduce components
                if features.shape[1] < self.n_components:
                    padding = np.zeros((n_samples, self.n_components - features.shape[1]))
                    features = np.hstack([features, padding])

                # Store model
                model_key = f"{method}_{layer}_{token_position}"
                self.models[model_key] = local_reducer

                # Create feature records
                for idx, (_, row) in enumerate(layer_pos_df.iterrows()):
                    feature_records.append(
                        {
                            "probe_id": row["probe_id"],
                            "layer": layer,
                            "token_position": token_position,
                            "features": features[idx].tolist(),
                            "method": method,
                            "source": source,
                        }
                    )

        # Write output
        output_filename = f"features_{source}_{method}{self.n_components}.parquet"
        output_path = session_path / output_filename
        features_df = pd.DataFrame(feature_records)
        features_df.to_parquet(output_path, index=False)

        logger.info(f"Saved {len(feature_records)} {method}/{source} features to {output_path}")

        # Backward compat: if this is expert_output + pca, also write features_pca128.parquet
        if source == "expert_output" and method == "pca":
            compat_path = session_path / f"features_pca{self.n_components}.parquet"
            # Write a copy with the old column name for backward compat
            compat_df = features_df.copy()
            compat_df = compat_df.rename(columns={"features": "pca128"})
            compat_df = compat_df.drop(columns=["method", "source"])
            compat_df.to_parquet(compat_path, index=False)
            logger.info(f"Backward compat: wrote {compat_path}")

        # Save metadata
        metadata_path = session_path / f"{output_filename.replace('.parquet', '_metadata.json')}"
        metadata = {
            "method": method,
            "source": source,
            "n_components": self.n_components,
            "generated_at": datetime.now().isoformat(),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return str(output_path)

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
