#!/usr/bin/env python3
"""
PCA generation service to create features_pca128.parquet from expert output states.
Applies PCA to reduce 2880D expert outputs to 128D for clustering and visualization.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from datetime import datetime

from schemas.expert_output_states import ExpertOutputState
from schemas.features_pca128 import PCAFeatureRecord, create_pca_features

logger = logging.getLogger(__name__)


class PCAGenerationService:
    """Generate PCA features from expert output states for clustering."""
    
    def __init__(self, n_components: int = 128):
        """
        Initialize PCA generation service.
        
        Args:
            n_components: Number of PCA components to keep (default 128)
        """
        self.n_components = n_components
        self.pca_models = {}  # Per-layer, per-position PCA models
        
    def generate_pca_features(self, session_id: str, data_lake_path: str = "data/lake") -> str:
        """
        Generate PCA features for a capture session.
        
        Args:
            session_id: Capture session ID
            data_lake_path: Path to data lake
            
        Returns:
            Path to generated features_pca128.parquet file
        """
        session_path = Path(data_lake_path) / f"session_{session_id}"
        
        # Read expert output states
        expert_outputs_path = session_path / "expert_output_states.parquet"
        if not expert_outputs_path.exists():
            raise FileNotFoundError(f"Expert output states not found: {expert_outputs_path}")
        
        logger.info(f"Loading expert output states from {expert_outputs_path}")
        df = pd.read_parquet(expert_outputs_path)
        
        # Group by layer and token position to fit PCA models
        pca_features_records = []
        
        for layer in range(24):
            for token_position in [0, 1]:  # Context and target
                # Filter data
                mask = (df['layer'] == layer) & (df['token_position'] == token_position)
                layer_pos_df = df[mask]
                
                if layer_pos_df.empty:
                    logger.warning(f"No data for layer {layer}, position {token_position}, skipping")
                    continue
                
                # Extract expert output states efficiently
                n_samples = len(layer_pos_df)
                if n_samples < self.n_components:
                    logger.warning(f"Layer {layer}, pos {token_position}: Only {n_samples} samples, "
                                 f"reducing components to {n_samples}")
                    n_components_actual = min(n_samples, self.n_components)
                else:
                    n_components_actual = self.n_components
                
                # Pre-allocate array for efficiency
                states = np.zeros((n_samples, 2880), dtype=np.float32)
                for idx, (_, row) in enumerate(layer_pos_df.iterrows()):
                    states[idx] = np.array(row['expert_output_state'], dtype=np.float32)
                
                logger.info(f"Layer {layer}, pos {token_position}: "
                          f"Fitting PCA on {states.shape[0]} samples of dim {states.shape[1]}")
                
                # Fit PCA for this layer and position
                pca = PCA(n_components=n_components_actual, random_state=42)
                pca_features = pca.fit_transform(states)
                
                # Pad with zeros if we had to reduce components
                if n_components_actual < self.n_components:
                    padding = np.zeros((n_samples, self.n_components - n_components_actual))
                    pca_features = np.hstack([pca_features, padding])
                
                # Store PCA model for later use
                model_key = f"{layer}_{token_position}"
                self.pca_models[model_key] = pca
                
                # Log explained variance
                total_variance = np.sum(pca.explained_variance_ratio_)
                logger.info(f"Layer {layer}, pos {token_position}: "
                          f"PCA explains {total_variance:.2%} of variance")
                
                # Create PCA feature records
                for idx, (_, row) in enumerate(layer_pos_df.iterrows()):
                    # Create PCAFeatures object using the schema function
                    pca_feat = create_pca_features(
                        probe_id=row['probe_id'],
                        layer=layer,
                        token_position=token_position,
                        pca128=pca_features[idx]
                    )
                    
                    # Convert to dict for DataFrame
                    record = {
                        'probe_id': pca_feat.probe_id,
                        'layer': pca_feat.layer,
                        'token_position': pca_feat.token_position,
                        'pca128': pca_feat.pca128.tolist()
                    }
                    pca_features_records.append(record)
        
        # Save PCA features to parquet
        output_path = session_path / "features_pca128.parquet"
        pca_df = pd.DataFrame(pca_features_records)
        pca_df.to_parquet(output_path, index=False)
        
        logger.info(f"Saved {len(pca_features_records)} PCA features to {output_path}")
        
        # Save PCA model metadata
        metadata_path = session_path / "pca_metadata.json"
        metadata = {
            'n_components': self.n_components,
            'generated_at': datetime.now().isoformat(),
            'explained_variance_per_layer_position': {}
        }
        
        for model_key, pca in self.pca_models.items():
            layer, position = model_key.split('_')
            key = f"layer_{layer}_pos_{position}"
            metadata['explained_variance_per_layer_position'][key] = {
                'total_variance_explained': float(np.sum(pca.explained_variance_ratio_)),
                'n_components_used': pca.n_components_,
                'per_component_variance': pca.explained_variance_ratio_.tolist()[:10]  # First 10
            }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved PCA metadata to {metadata_path}")
        
        return str(output_path)
    
    def transform_new_states(
        self, 
        states: np.ndarray, 
        layer: int, 
        token_position: int
    ) -> np.ndarray:
        """
        Transform new expert output states using fitted PCA model.
        
        Args:
            states: Expert output states (N x 2880)
            layer: Layer number
            token_position: Token position (0=context, 1=target)
            
        Returns:
            PCA features (N x 128)
        """
        model_key = f"{layer}_{token_position}"
        if model_key not in self.pca_models:
            raise ValueError(f"No PCA model fitted for layer {layer}, position {token_position}")
        
        pca = self.pca_models[model_key]
        pca_features = pca.transform(states)
        
        # Pad if necessary
        if pca_features.shape[1] < self.n_components:
            padding = np.zeros((pca_features.shape[0], self.n_components - pca_features.shape[1]))
            pca_features = np.hstack([pca_features, padding])
        
        return pca_features
    
    def get_pca_components_for_viz(
        self, 
        n_dims: int = 3,
        token_position: int = 1
    ) -> Dict[int, np.ndarray]:
        """
        Get first N PCA components for visualization.
        
        Args:
            n_dims: Number of dimensions (2, 3, 5, 10, etc.)
            token_position: Token position to get components for (default target=1)
            
        Returns:
            Dict mapping layer to PCA components matrix
        """
        components = {}
        for layer in range(24):
            model_key = f"{layer}_{token_position}"
            if model_key in self.pca_models:
                pca = self.pca_models[model_key]
                # Get min of requested dims and available components
                n_available = min(n_dims, pca.n_components_)
                components[layer] = pca.components_[:n_available]
        return components


def main():
    """Generate PCA features for existing capture sessions."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PCA features from expert output states")
    parser.add_argument("session_id", help="Capture session ID")
    parser.add_argument("--n-components", type=int, default=128, help="Number of PCA components")
    parser.add_argument("--data-lake", default="data/lake", help="Path to data lake")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Generate PCA features
    service = PCAGenerationService(n_components=args.n_components)
    output_path = service.generate_pca_features(args.session_id, args.data_lake)
    
    print(f"✅ PCA features generated: {output_path}")


if __name__ == "__main__":
    main()