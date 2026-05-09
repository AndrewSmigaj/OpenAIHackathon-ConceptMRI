#!/usr/bin/env python3
"""KV-cache splice helper for harmony-format expanding sequences.

Used by callers (currently temporal-capture) that want to capture residuals
through a growing user-message context without re-encoding the prefix on
every step.

The harmony chat-template wraps a user turn as:
    <prefix...><|start|>user<|message|>{content}<|end|><|start|>assistant

When `content` grows by appending another sentence, the cached `past_kv`
from step N can't be appended to directly because the suffix tokens
`<|end|><|start|>assistant` sit AFTER the user content in the cache.
The fix: crop the cache by the suffix length, splice in the new content
plus suffix, run the next forward pass.

Verified invariants (see plan):
- Splice tokens equal cumulative tokens for 17,270 + 385 real-content pairs.
- transformers.DynamicCache.crop is in-place; supports negative indices
  (crop(-N) drops the last N tokens).
"""

from __future__ import annotations

from typing import List

from transformers import PreTrainedTokenizerBase


SUFFIX_LITERAL = "<|end|><|start|>assistant"


class HarmonyKVChain:
    """Encapsulates the suffix-tokens + crop-and-splice math for cache-on
    expanding harmony sequences. Stateless across separate sequences;
    callers create one instance per sequence."""

    def __init__(self, tokenizer: PreTrainedTokenizerBase):
        self._tok = tokenizer
        self._suffix_ids: List[int] = tokenizer.encode(
            SUFFIX_LITERAL, add_special_tokens=False
        )
        if not self._suffix_ids:
            raise RuntimeError(
                f"Tokenizer produced empty suffix for {SUFFIX_LITERAL!r} — "
                "harmony format may have changed; refusing to splice."
            )
        self._suffix_len = len(self._suffix_ids)

    @property
    def suffix_len(self) -> int:
        return self._suffix_len

    def first_step_tokens(self, content: str) -> List[int]:
        """Full harmony chat-template wrap for the first step. The forward
        pass run on these tokens populates a fresh KV cache that ends with
        `self._suffix_ids` — `next_step_tokens` will crop those before
        splicing the next sentence."""
        enc = self._tok.apply_chat_template(
            [{"role": "user", "content": content}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        return enc["input_ids"][0].tolist()

    def next_step_tokens(self, sentence: str, past_kv) -> List[int]:
        """Crop past_kv in place to drop the suffix from the prior step,
        then return the new tokens to feed: ` ` + sentence + suffix.

        The leading space is required: BPE tokenizes ' B.' differently
        from 'B.', and the cumulative cache-off tokenization of the prior
        content is followed by ' '+next_sentence on the wire. Verified
        across 17,270 sentence pairs in our basin pools.

        After this call the past_kv covers `<prefix>...<prior_content>` and
        the returned token_ids continue with ` <new_sentence><|end|>
        <|start|>assistant`. After the next forward pass, the cache covers
        the same shape ready for another `next_step_tokens` call."""
        past_kv.crop(-self._suffix_len)
        new_content_ids = self._tok.encode(
            " " + sentence, add_special_tokens=False
        )
        return new_content_ids + list(self._suffix_ids)
