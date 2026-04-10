#!/usr/bin/env python3
"""
Probe text processing and schema conversion.

Owns tokenization helpers and conversion of raw capture data to schema records.
No model inference, no I/O, no GPU state.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from schemas.tokens import ProbeRecord, create_probe_record
from schemas.routing import RoutingRecord, create_routing_record
from schemas.embedding import EmbeddingRecord, create_embedding_record
from schemas.residual_stream import ResidualStreamState, create_residual_stream_state

if TYPE_CHECKING:
    from adapters.base_adapter import ModelAdapter

logger = logging.getLogger(__name__)


@dataclass
class ProbeCapture:
    """Complete capture data for a single probe."""
    probe_id: str
    session_id: str
    probe_record: ProbeRecord
    routing_records: List[RoutingRecord]
    embedding_records: List[EmbeddingRecord]
    residual_stream_records: List[ResidualStreamState]


class ProbeProcessor:
    """Text processing and schema conversion for probe captures."""

    def __init__(self, tokenizer, adapter: Optional['ModelAdapter'], layers_to_capture: List[int]):
        self.tokenizer = tokenizer
        self.adapter = adapter
        self.layers_to_capture = layers_to_capture

    def find_word_token_position(self, token_ids: list, word: str) -> Tuple[int, int]:
        """Find a word's token position in a tokenized sequence.

        Returns (position, token_id). Picks last occurrence if multiple matches.
        Handles BPE whitespace sensitivity by trying both 'word' and ' word'.
        Raises ValueError if word is multi-token or not found.
        """
        word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
        space_word_tokens = self.tokenizer.encode(f" {word}", add_special_tokens=False)

        if len(word_tokens) == 1:
            target_token_id = word_tokens[0]
        elif len(space_word_tokens) == 1:
            target_token_id = space_word_tokens[0]
        else:
            raise ValueError(
                f"Word '{word}' must be a single token. "
                f"Got {len(word_tokens)} tokens without space, "
                f"{len(space_word_tokens)} tokens with space."
            )

        positions = [i for i, tid in enumerate(token_ids) if tid == target_token_id]
        if not positions:
            alt_id = space_word_tokens[0] if len(word_tokens) == 1 else word_tokens[0]
            positions = [i for i, tid in enumerate(token_ids) if tid == alt_id]
            if positions:
                target_token_id = alt_id

        if not positions:
            raise ValueError(f"Word '{word}' (token_id={target_token_id}) not found in tokenized input")

        return positions[-1], target_token_id

    def find_all_word_token_positions(self, token_ids: list, word: str) -> List[Tuple[int, int]]:
        """Find ALL positions where a word appears in a tokenized sequence.

        Like find_word_token_position but returns every occurrence, not just the last.
        Returns empty list (not ValueError) if word not found — absent target words
        are expected per-tick in agent sessions.

        Returns list of (position, token_id) tuples.
        """
        word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
        space_word_tokens = self.tokenizer.encode(f" {word}", add_special_tokens=False)

        if len(word_tokens) == 1:
            target_token_id = word_tokens[0]
        elif len(space_word_tokens) == 1:
            target_token_id = space_word_tokens[0]
        else:
            logger.warning(
                f"Word '{word}' is multi-token ({len(word_tokens)} without space, "
                f"{len(space_word_tokens)} with space) — skipping"
            )
            return []

        positions = [i for i, tid in enumerate(token_ids) if tid == target_token_id]
        if not positions:
            alt_id = space_word_tokens[0] if len(word_tokens) == 1 else word_tokens[0]
            positions = [i for i, tid in enumerate(token_ids) if tid == alt_id]
            if positions:
                target_token_id = alt_id

        return [(pos, target_token_id) for pos in positions]

    def convert_to_schemas(
        self,
        probe_id: str,
        session_id: str,
        input_text: str,
        target_word: str,
        target_token_id: int,
        target_token_position: int,
        total_tokens: int,
        routing_data: Dict,
        embedding_data: Dict,
        residual_stream_data: Dict,
        context_word: str = None,
        context_token_position: int = None,
        experiment_id: str = None,
        sequence_id: str = None,
        sentence_index: int = None,
        label: str = None,
        label2: str = None,
        categories: Optional[Dict[str, str]] = None,
        transition_step: int = None,
        turn_id: int = None,
        scenario_id: str = None,
        capture_type: str = None,
        target_char_offset: int = None,
    ) -> ProbeCapture:
        """Convert raw capture data to schema records.

        Extracts activation data at the target position (always) and
        context position (if context_word provided). Stores with semantic
        token_position: 0=context, 1=target.
        """
        probe_record = create_probe_record(
            probe_id=probe_id,
            session_id=session_id,
            input_text=input_text,
            target_word=target_word,
            target_token_id=target_token_id,
            target_token_position=target_token_position,
            total_tokens=total_tokens,
            context_word=context_word,
            context_token_position=context_token_position,
            experiment_id=experiment_id,
            sequence_id=sequence_id,
            sentence_index=sentence_index,
            label=label,
            label2=label2,
            categories=categories,
            transition_step=transition_step,
            created_at=datetime.now().isoformat(),
            turn_id=turn_id,
            scenario_id=scenario_id,
            capture_type=capture_type,
            target_char_offset=target_char_offset,
        )

        routing_records = []
        embedding_records = []
        residual_stream_records = []

        positions_to_extract = [(target_token_position, 1)]
        if context_token_position is not None:
            positions_to_extract.append((context_token_position, 0))

        for layer in self.layers_to_capture:
            layer_key = f"layer_{layer}"

            if layer_key not in routing_data:
                logger.warning(f"No routing data for layer {layer}")
                continue

            layer_routing = routing_data[layer_key]

            for actual_pos, semantic_pos in positions_to_extract:
                routing_weights = layer_routing["routing_weights"][0, actual_pos, :]
                routing_records.append(create_routing_record(
                    probe_id=probe_id, layer=layer,
                    token_position=semantic_pos,
                    routing_weights=routing_weights.numpy(),
                    turn_id=turn_id, scenario_id=scenario_id,
                    capture_type=capture_type,
                ))

            if layer_key in embedding_data:
                emb_layer = embedding_data[layer_key]
                for actual_pos, semantic_pos in positions_to_extract:
                    emb_vec = emb_layer["embedding"][0, actual_pos, :]
                    embedding_records.append(create_embedding_record(
                        probe_id=probe_id, layer=layer,
                        token_position=semantic_pos,
                        embedding=emb_vec.numpy(),
                        turn_id=turn_id, scenario_id=scenario_id,
                        capture_type=capture_type,
                    ))

            if layer_key in residual_stream_data:
                res_layer = residual_stream_data[layer_key]
                for actual_pos, semantic_pos in positions_to_extract:
                    residual_state = res_layer["residual_stream"][0, actual_pos, :]
                    residual_stream_records.append(create_residual_stream_state(
                        probe_id=probe_id, layer=layer,
                        token_position=semantic_pos,
                        residual_stream=residual_state.numpy(),
                        turn_id=turn_id, scenario_id=scenario_id,
                        capture_type=capture_type,
                    ))

        return ProbeCapture(
            probe_id=probe_id,
            session_id=session_id,
            probe_record=probe_record,
            routing_records=routing_records,
            embedding_records=embedding_records,
            residual_stream_records=residual_stream_records,
        )
