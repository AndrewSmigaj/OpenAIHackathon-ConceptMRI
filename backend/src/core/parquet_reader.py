#!/usr/bin/env python3
"""
Simple Parquet reader with dataclass reconstruction.
Each dataclass handles its own deserialization logic.
"""

from typing import List, Type, TypeVar
from pathlib import Path
import pyarrow.parquet as pq

T = TypeVar('T')


def read_records(file_path: str, dataclass_type: Type[T]) -> List[T]:
    """
    Read Parquet file and reconstruct dataclass objects.
    
    Args:
        file_path: Path to Parquet file
        dataclass_type: Dataclass type to reconstruct
        
    Returns:
        List of dataclass instances
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If data can't be converted to dataclass
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {file_path}")
    
    try:
        # Read Parquet table
        table = pq.read_table(path)
        
        # Convert to list of dictionaries
        records_data = table.to_pylist()
        
        # Let each dataclass handle its own reconstruction
        records = []
        for record_dict in records_data:
            record = dataclass_type.from_parquet_dict(record_dict)
            records.append(record)
        
        return records
        
    except Exception as e:
        raise ValueError(f"Failed to read records from {file_path}: {e}")