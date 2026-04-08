#!/usr/bin/env python3
"""
Model inference and hook lifecycle management.

Owns the model forward pass, hook registration/removal, text generation,
and GPU memory cleanup. The most complex component but with the clearest
boundary — everything that touches the GPU lives here.
"""

import torch
import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from services.probes.routing_capture import EnhancedRoutingCapture

if TYPE_CHECKING:
    from adapters.base_adapter import ModelAdapter

logger = logging.getLogger(__name__)


class CaptureOrchestrator:
    """Manages model inference, hook lifecycle, and GPU memory."""

    def __init__(self, model, tokenizer, adapter: Optional['ModelAdapter'], layers_to_capture: List[int]):
        self.model = model
        self.tokenizer = tokenizer
        self.adapter = adapter
        self.layers_to_capture = layers_to_capture
        self.routing_capture: Optional[EnhancedRoutingCapture] = None

    def initialize_hooks(self, session_id: str) -> None:
        """Initialize routing capture hooks (lazy — only first call creates them)."""
        if self.routing_capture is None:
            self.routing_capture = EnhancedRoutingCapture(
                self.model, self.layers_to_capture, adapter=self.adapter
            )
            self.routing_capture.register_hooks()
            logger.info(f"Registered hooks for session {session_id}")

    def cleanup_hooks(self) -> None:
        """Remove all hooks and free GPU memory."""
        if self.routing_capture is not None:
            self.routing_capture.remove_hooks()
            self.routing_capture = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Cleaned up routing capture and GPU memory")

    def clear_captured_data(self) -> None:
        """Clear data from the last forward pass."""
        if self.routing_capture is not None:
            self.routing_capture.clear_data()

    def run_forward_pass(
        self, input_tensor: torch.Tensor,
        past_key_values=None, use_cache: bool = False,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[object, Optional[object]]:
        """Run a single forward pass through the model.

        Returns (outputs, new_past_key_values or None).
        """
        with torch.no_grad():
            forward_kwargs = {"input_ids": input_tensor}
            if attention_mask is not None:
                forward_kwargs["attention_mask"] = attention_mask
            if past_key_values is not None:
                forward_kwargs["past_key_values"] = past_key_values
            if use_cache:
                forward_kwargs["use_cache"] = True
            outputs = self.model(**forward_kwargs)

        new_past_key_values = None
        if use_cache and hasattr(outputs, "past_key_values"):
            new_past_key_values = outputs.past_key_values

        return outputs, new_past_key_values

    def generate_continuation(
        self, input_tensor: torch.Tensor, max_new_tokens: int = 50,
        attention_mask: Optional[torch.Tensor] = None,
        skip_special_tokens: bool = True,
    ) -> str:
        """Generate a text continuation from the model.

        Temporarily removes routing hooks before calling model.generate(),
        since generate() runs multiple forward passes that would conflict
        with the single-pass routing capture hooks.
        """
        if self.routing_capture is not None:
            self.routing_capture.remove_hooks()

        try:
            with torch.no_grad():
                gen_kwargs = {
                    "input_ids": input_tensor,
                    "max_new_tokens": max_new_tokens,
                    "do_sample": False,
                    "pad_token_id": self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                }
                if attention_mask is not None:
                    gen_kwargs["attention_mask"] = attention_mask
                gen_output = self.model.generate(**gen_kwargs)
            generated_ids = gen_output[0, input_tensor.shape[1]:]
            return self.tokenizer.decode(generated_ids, skip_special_tokens=skip_special_tokens)
        finally:
            if self.routing_capture is not None:
                self.routing_capture.register_hooks(verbose=False)

    def generate_continuation_with_ids(
        self, input_tensor: torch.Tensor, max_new_tokens: int = 50,
        attention_mask: Optional[torch.Tensor] = None,
        skip_special_tokens: bool = True,
    ) -> Tuple[str, List[int]]:
        """Generate text continuation, returning both decoded text and token IDs.

        Like generate_continuation() but also returns the raw token IDs,
        enabling token-level concatenation without BPE re-tokenization.
        """
        if self.routing_capture is not None:
            self.routing_capture.remove_hooks()

        try:
            with torch.no_grad():
                gen_kwargs = {
                    "input_ids": input_tensor,
                    "max_new_tokens": max_new_tokens,
                    "do_sample": False,
                    "pad_token_id": self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                }
                if attention_mask is not None:
                    gen_kwargs["attention_mask"] = attention_mask
                gen_output = self.model.generate(**gen_kwargs)
            generated_ids = gen_output[0, input_tensor.shape[1]:]
            text = self.tokenizer.decode(generated_ids, skip_special_tokens=skip_special_tokens)
            return text, generated_ids.tolist()
        finally:
            if self.routing_capture is not None:
                self.routing_capture.register_hooks(verbose=False)

    def get_captured_data(self) -> Tuple[Dict, Dict, Dict]:
        """Return the three captured data dicts from the last forward pass."""
        return (
            self.routing_capture.routing_data,
            self.routing_capture.embedding_data,
            self.routing_capture.residual_stream_data,
        )
