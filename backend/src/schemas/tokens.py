#!/usr/bin/env python3
"""
Tokens schema - index table linking probe_id to context-target pairs.
Used by experiments to query specific token combinations.
"""

from dataclasses import dataclass


@dataclass
class TokenRecord:
    """Index linking probe_id to context-target token pairs."""
    
    probe_id: str            # Links to all MoE activation data for this pair
    context_text: str        # Context word (e.g., "the")
    target_text: str         # Target word (e.g., "cat") 
    context_token_id: int    # Tokenized context
    target_token_id: int     # Tokenized target

    @classmethod
    def from_parquet_dict(cls, data: dict) -> 'TokenRecord':
        """Reconstruct from Parquet dictionary (no special deserialization needed)."""
        return cls(**data)


# Parquet schema definition
TOKENS_PARQUET_SCHEMA = {
    "probe_id": "string",
    "context_text": "string", 
    "target_text": "string",
    "context_token_id": "int32",
    "target_token_id": "int32"
}


def create_token_record(
    probe_id: str,
    context_text: str,
    target_text: str, 
    context_token_id: int,
    target_token_id: int
) -> TokenRecord:
    """Create token record linking probe_id to context-target pair."""
    return TokenRecord(
        probe_id=probe_id,
        context_text=context_text,
        target_text=target_text,
        context_token_id=context_token_id,
        target_token_id=target_token_id
    )