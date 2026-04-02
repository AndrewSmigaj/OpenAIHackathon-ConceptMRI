#!/usr/bin/env python3
"""
Data lake file path utilities for consistent organization.
Simple flat structure: data/lake/{schema_name}.parquet
"""

from pathlib import Path

from api.config import DATA_LAKE_PATH


def get_schema_path(schema_name: str) -> Path:
    """
    Get the file path for a schema's Parquet file.

    Args:
        schema_name: Name of the schema (e.g., 'tokens', 'routing')

    Returns:
        Path to the schema's Parquet file
    """
    DATA_LAKE_PATH.mkdir(parents=True, exist_ok=True)
    return DATA_LAKE_PATH / f"{schema_name}.parquet"