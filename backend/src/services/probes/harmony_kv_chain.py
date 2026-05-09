#!/usr/bin/env python3
"""KV-cache splice helper for harmony-format expanding sequences.

Used by callers (currently temporal-capture) that want to capture residuals
through a growing user-message context without re-encoding the prefix on
every step.

**Design note:** This helper drops the harmony suffix (`<|end|><|start|>
assistant`) from the cache. Why we can do this: temporal captures don't
generate; we only read residuals at the target word position. Causal
(autoregressive) attention means the residual at position P depends only
on tokens 0..P, NEVER on tokens after P. The target word is always BEFORE
the suffix, so dropping the suffix from the cache produces identical
residuals to keeping it.

Why we MUST do this: gpt-oss-20b uses sliding-window attention with
window=128 in half its layers. After the cache exceeds 128 tokens, those
layers can't be cropped (the discarded tokens are gone), so the
"crop suffix + extend with new content" approach fails after a few steps.
Avoiding the suffix entirely sidesteps the problem.

Verified invariants (see plan):
- Splice tokens equal cumulative tokens (sans suffix) for 17,270 + 385
  real-content pairs, plus 3-step sanity check.
"""

from __future__ import annotations

from typing import List

from transformers import PreTrainedTokenizerBase


SUFFIX_LITERAL = "<|end|><|start|>assistant"


class HarmonyKVChain:
    """Stateless helper for cache-on harmony expanding sequences.

    Step 0: feed `first_step_tokens(content)` → forward pass with no cache.
    Step k>0: feed `next_step_tokens(sentence)` → forward pass with the
    past_kv from step k-1. The model extends its cache; nothing is dropped.
    """

    def __init__(self, tokenizer: PreTrainedTokenizerBase):
        self._tok = tokenizer
        suffix_ids = tokenizer.encode(SUFFIX_LITERAL, add_special_tokens=False)
        if not suffix_ids:
            raise RuntimeError(
                f"Tokenizer produced empty suffix for {SUFFIX_LITERAL!r} — "
                "harmony format may have changed."
            )
        self._suffix_len = len(suffix_ids)

    @property
    def suffix_len(self) -> int:
        return self._suffix_len

    def first_step_tokens(self, content: str) -> List[int]:
        """Full harmony chat-template wrap MINUS the trailing suffix tokens.
        The cache after the forward pass covers `<system_prefix> + content`."""
        enc = self._tok.apply_chat_template(
            [{"role": "user", "content": content}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        full_ids = enc["input_ids"][0].tolist()
        return full_ids[: -self._suffix_len]

    def next_step_tokens(self, sentence: str) -> List[int]:
        """Just `' ' + sentence` tokens. No suffix, no crop. The cache
        from the prior step covers everything up through the previous
        sentence; the next forward pass extends it.

        Leading space is required — BPE tokenizes ' B.' differently from
        'B.' and the cumulative cache-off tokenization expects ' '+next."""
        return self._tok.encode(" " + sentence, add_special_tokens=False)
