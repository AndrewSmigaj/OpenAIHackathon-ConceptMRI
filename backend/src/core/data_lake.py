#!/usr/bin/env python3
"""
Data lake file path utilities for consistent organization.
Simple flat structure: data/lake/{schema_name}.parquet
"""

from pathlib import Path


def get_schema_path(schema_name: str) -> Path:
    """
    Get the file path for a schema's Parquet file.
    
    Args:
        schema_name: Name of the schema (e.g., 'tokens', 'routing')
        
    Returns:
        Path to the schema's Parquet file
    """
    lake_path = Path("data/lake")
    lake_path.mkdir(parents=True, exist_ok=True)
    return lake_path / f"{schema_name}.parquet"