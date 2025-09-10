#!/usr/bin/env python3
"""
Clustering schema for PCA-based clustering with configurable dimensions.
Captures cluster assignments from k-means/hierarchical/DBSCAN clustering of PCA features.
Mirrors RoutingRecord structure for consistent trajectory analysis.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from datetime import datetime


@dataclass
class ClusteringRecord:
    """PCA-based clustering record with configurable dimensions for trajectory analysis."""
    
    # Core identifiers  
    probe_id: str               # Links to tokens and features
    layer: int                  # Layer number (0-23 for GPT-OSS-20B)
    token_position: int         # Token position in sequence (0=context, 1=target)
    
    # Clustering data (mirrors routing structure)
    cluster_id: int             # Assigned cluster ID 
    cluster_confidence: float   # Distance-based confidence score
    pca_dimensions: int         # Number of PCA components used for clustering
    
    # Clustering method metadata
    clustering_method: str      # "kmeans", "hierarchical", or "dbscan"
    num_clusters: int           # Total clusters in this layer (k for kmeans, excludes noise for DBSCAN)
    
    # Distance metrics
    distance_to_centroid: float # Distance to assigned cluster center
    silhouette_score: float     # Silhouette score for cluster quality
    
    # Metadata
    captured_at: str            # ISO timestamp for debugging
    
    def __post_init__(self):
        """Validate clustering data consistency."""
        context = f"Probe {self.probe_id} Layer {self.layer}"
        
        if not (0 <= self.layer <= 23):
            raise ValueError(f"{context}: Layer {self.layer} out of range [0, 23]")
        
        if not (0 <= self.token_position <= 1):
            raise ValueError(f"{context}: Token position {self.token_position} out of range [0, 1]")
        
        if not (2 <= self.pca_dimensions <= 128):
            raise ValueError(f"{context}: PCA dimensions {self.pca_dimensions} out of range [2, 128]")
        
        if self.clustering_method not in ["kmeans", "hierarchical", "dbscan"]:
            raise ValueError(f"{context}: Invalid clustering method {self.clustering_method}")
        
        # Validate cluster ID based on method
        if self.clustering_method == "dbscan":
            # DBSCAN allows noise points (cluster_id = -1) or valid clusters [0, num_clusters)
            if not (self.cluster_id == -1 or 0 <= self.cluster_id < self.num_clusters):
                raise ValueError(f"{context}: DBSCAN cluster ID {self.cluster_id} invalid (must be -1 or in [0, {self.num_clusters}))")
        else:
            # K-means and hierarchical use 0-based cluster IDs
            if not (0 <= self.cluster_id < self.num_clusters):
                raise ValueError(f"{context}: Cluster ID {self.cluster_id} out of range [0, {self.num_clusters})")

    def is_noise(self) -> bool:
        """Check if this is a noise point (DBSCAN only)."""
        return self.clustering_method == "dbscan" and self.cluster_id == -1
    
    def clustering_quality(self) -> str:
        """Assess clustering quality based on silhouette score."""
        if self.silhouette_score > 0.7:
            return "excellent"
        elif self.silhouette_score > 0.5:
            return "good" 
        elif self.silhouette_score > 0.25:
            return "fair"
        else:
            return "poor"

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'ClusteringRecord':
        """Reconstruct from Parquet dictionary."""
        return cls(
            probe_id=data['probe_id'],
            layer=data['layer'],
            token_position=data['token_position'],
            cluster_id=data['cluster_id'],
            cluster_confidence=data['cluster_confidence'],
            pca_dimensions=data['pca_dimensions'],
            clustering_method=data['clustering_method'],
            num_clusters=data['num_clusters'],
            distance_to_centroid=data['distance_to_centroid'],
            silhouette_score=data['silhouette_score'],
            captured_at=data['captured_at']
        )


# Parquet schema definition
CLUSTERING_PARQUET_SCHEMA = {
    "probe_id": "string",
    "layer": "int32",
    "token_position": "int32",
    "cluster_id": "int32",
    "cluster_confidence": "float",
    "pca_dimensions": "int32", 
    "clustering_method": "string",
    "num_clusters": "int32",
    "distance_to_centroid": "float",
    "silhouette_score": "float",
    "captured_at": "string"
}


def create_clustering_record(
    probe_id: str,
    layer: int,
    token_position: int,
    cluster_id: int,
    cluster_confidence: float,
    pca_dimensions: int,
    clustering_method: str,
    num_clusters: int,
    distance_to_centroid: float,
    silhouette_score: float,
    captured_at: Optional[str] = None
) -> ClusteringRecord:
    """
    Create clustering record from clustering algorithm output.
    
    Args:
        probe_id: Unique probe identifier
        layer: Layer number (0-23)
        token_position: Token position in sequence (0=context, 1=target)
        cluster_id: Assigned cluster ID (-1 for DBSCAN noise)
        cluster_confidence: Distance-based confidence score
        pca_dimensions: Number of PCA components used
        clustering_method: "kmeans", "hierarchical", or "dbscan"
        num_clusters: Total number of clusters in this layer
        distance_to_centroid: Distance to cluster center
        silhouette_score: Clustering quality metric
        captured_at: Capture timestamp (defaults to now)
    
    Returns:
        ClusteringRecord for trajectory analysis
    """
    if captured_at is None:
        captured_at = datetime.now().isoformat()
    
    return ClusteringRecord(
        probe_id=probe_id,
        layer=layer,
        token_position=token_position,
        cluster_id=cluster_id,
        cluster_confidence=cluster_confidence,
        pca_dimensions=pca_dimensions,
        clustering_method=clustering_method,
        num_clusters=num_clusters,
        distance_to_centroid=distance_to_centroid,
        silhouette_score=silhouette_score,
        captured_at=captured_at
    )


def cluster_highway_signature(clustering_records: List[ClusteringRecord], target_tokens_only: bool = True) -> str:
    """
    Generate cluster highway signature from clustering records.
    Mirrors highway_signature from routing.py but uses cluster_id instead of expert_id.
    
    Args:
        clustering_records: List of clustering records across layers
        target_tokens_only: If True, only use target token (position=1) records
    
    Returns:
        Cluster highway signature like "L0C2→L1C5→L2C1" (for target token clustering)
    """
    if not clustering_records:
        return ""
    
    # Filter to target tokens only for consistency with routing
    if target_tokens_only:
        target_records = [r for r in clustering_records if r.token_position == 1]
        if not target_records:
            return ""
        records_to_use = target_records
    else:
        records_to_use = clustering_records
    
    # Sort by layer to build signature in order
    sorted_records = sorted(records_to_use, key=lambda r: r.layer)
    
    # Build signature parts
    signature_parts = []
    for record in sorted_records:
        if record.is_noise():
            part = f"L{record.layer}C-1"  # Noise points marked as C-1
        else:
            part = f"L{record.layer}C{record.cluster_id}"
        signature_parts.append(part)
    
    return "→".join(signature_parts)