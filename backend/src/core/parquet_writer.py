#!/usr/bin/env python3
"""
Batch Parquet writer for consistent data storage across all schemas.
Handles numpy array serialization and batch accumulation.
"""

from typing import List, Any, Dict
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
from dataclasses import asdict

from utils.parquet_utils import serialize_array_for_parquet


class BatchWriter:
    """Batch writer for Parquet files with automatic numpy array handling."""
    
    def __init__(self, file_path: str, batch_size: int = 1000):
        """
        Initialize batch writer.
        
        Args:
            file_path: Path to write Parquet file
            batch_size: Number of records to accumulate before writing
        """
        self.file_path = Path(file_path)
        self.batch_size = batch_size
        self.records: List[Dict] = []
        
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def add_record(self, record: Any) -> None:
        """
        Add a dataclass record to the batch.
        
        Args:
            record: Dataclass instance to add
        """
        # Convert dataclass to dict
        record_dict = asdict(record)
        
        # Convert numpy arrays to lists for Parquet storage
        record_dict = self._serialize_numpy_arrays(record_dict)
        
        self.records.append(record_dict)
        
        # Auto-flush when batch is full
        if len(self.records) >= self.batch_size:
            self.flush()
    
    def _serialize_numpy_arrays(self, record_dict: Dict) -> Dict:
        """Convert numpy arrays to lists for Parquet storage."""
        serialized = {}
        
        for key, value in record_dict.items():
            if isinstance(value, np.ndarray):
                serialized[key] = serialize_array_for_parquet(value)
            else:
                serialized[key] = value
        
        return serialized
    
    def flush(self) -> None:
        """Write accumulated records to Parquet file."""
        if not self.records:
            return
        
        try:
            # Convert to Arrow table
            table = pa.Table.from_pylist(self.records)
            
            # Handle appending for older PyArrow versions
            if self.file_path.exists():
                # Read existing data and combine
                existing_table = pq.read_table(self.file_path)
                combined_table = pa.concat_tables([existing_table, table])
                pq.write_table(combined_table, self.file_path)
            else:
                pq.write_table(table, self.file_path)
            
            # Clear batch
            self.records.clear()
            
        except Exception as e:
            # Log error but don't crash - just keep records for retry
            print(f"Failed to write batch to {self.file_path}: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush any remaining records."""
        self.flush()


def write_records_batch(records: List[Any], file_path: str, batch_size: int = 1000) -> None:
    """
    Convenience function to write a list of records in batches.
    
    Args:
        records: List of dataclass instances
        file_path: Path to write Parquet file
        batch_size: Batch size for writing
    """
    with BatchWriter(file_path, batch_size) as writer:
        for record in records:
            writer.add_record(record)