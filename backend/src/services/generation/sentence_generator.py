#!/usr/bin/env python3
"""
LLM-powered sentence generation for experiments.
Generates label-specific sentences with validation and retry logic.
"""

import json
import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from services.generation.sentence_set import (
    SentenceEntry, SentenceSet, compute_char_span,
    validate_sentence, save_sentence_set
)

logger = logging.getLogger(__name__)


class SentenceGenerator:
    """Generate sentence sets for experiments using LLMs."""

    async def generate_sentence_set(
        self,
        name: str,
        target_word: str,
        label_a: str,
        label_b: str,
        description_a: str,
        description_b: str,
        count_per_group: int = 20,
        neutral_count: int = 5,
        api_key: Optional[str] = None,
        provider: str = "openai",
        batch_size: int = 10,
        max_retries: int = 3,
    ) -> SentenceSet:
        """Generate a complete sentence set with validation and retries."""
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No API key provided and OPENAI_API_KEY not set")

        logger.info(
            f"Generating sentence set '{name}': {count_per_group} per label, "
            f"{neutral_count} neutral, target='{target_word}'"
        )

        sentences_a = await self._generate_group_sentences(
            target_word, "A", label_a, description_a,
            count_per_group, batch_size, max_retries, api_key, provider,
            existing_texts=set()
        )

        existing_texts = {s.text for s in sentences_a}
        sentences_b = await self._generate_group_sentences(
            target_word, "B", label_b, description_b,
            count_per_group, batch_size, max_retries, api_key, provider,
            existing_texts=existing_texts
        )

        existing_texts.update(s.text for s in sentences_b)
        sentences_neutral = await self._generate_group_sentences(
            target_word, "neutral", "neutral",
            f"Neutral context — the word '{target_word}' is used in an ambiguous or "
            f"generic way that doesn't clearly belong to either '{label_a}' or "
            f"'{label_b}'",
            neutral_count, batch_size, max_retries, api_key, provider,
            existing_texts=existing_texts
        )

        ss = SentenceSet(
            name=name,
            version="1.0",
            target_word=target_word,
            label_a=label_a,
            label_b=label_b,
            description_a=description_a,
            description_b=description_b,
            sentences_a=sentences_a,
            sentences_b=sentences_b,
            sentences_neutral=sentences_neutral,
            metadata={
                "generator": "SentenceGenerator",
                "provider": provider,
                "requested_count_per_group": count_per_group,
                "requested_neutral_count": neutral_count,
            }
        )

        logger.info(
            f"Generated set '{name}': {len(sentences_a)}A + "
            f"{len(sentences_b)}B + {len(sentences_neutral)}N"
        )
        return ss

    async def _generate_group_sentences(
        self,
        target_word: str,
        group_code: str,
        label: str,
        description: str,
        total_count: int,
        batch_size: int,
        max_retries: int,
        api_key: str,
        provider: str,
        existing_texts: set,
    ) -> List[SentenceEntry]:
        """Generate sentences for one group with batching and retries."""
        collected: List[SentenceEntry] = []
        all_texts = set(existing_texts)

        remaining = total_count
        for attempt in range(max_retries + 1):
            if remaining <= 0:
                break

            batch_count = min(remaining, batch_size)
            logger.info(
                f"  [{label}] attempt {attempt+1}: "
                f"requesting {batch_count} (have {len(collected)}/{total_count})"
            )

            try:
                batch = await self._generate_batch(
                    target_word, group_code, label, description,
                    batch_count, all_texts, api_key, provider
                )

                for entry in batch:
                    errs = validate_sentence(entry, all_texts)
                    if not errs:
                        collected.append(entry)
                        all_texts.add(entry.text)
                    else:
                        logger.warning(f"  Rejected: {errs[0]}")

                remaining = total_count - len(collected)

            except Exception as e:
                logger.error(f"  Batch generation failed: {e}")
                if attempt == max_retries:
                    logger.warning(
                        f"  Max retries reached for {label}, "
                        f"got {len(collected)}/{total_count}"
                    )

        return collected

    async def _generate_batch(
        self,
        target_word: str,
        group_code: str,
        label: str,
        description: str,
        count: int,
        existing_texts: set,
        api_key: str,
        provider: str,
    ) -> List[SentenceEntry]:
        """Generate one batch of sentences via LLM."""
        prompt = self._build_generation_prompt(
            target_word, label, description, count, existing_texts
        )

        raw = await self._call_llm(prompt, api_key, provider)
        return self._parse_llm_response(raw, target_word, group_code)

    def _build_generation_prompt(
        self,
        target_word: str,
        label: str,
        description: str,
        count: int,
        existing_texts: set,
    ) -> str:
        """Build the prompt for sentence generation."""
        avoid_block = ""
        if existing_texts:
            samples = list(existing_texts)[:5]
            avoid_block = (
                "\n\nAvoid duplicating these existing sentences:\n"
                + "\n".join(f"- {s}" for s in samples)
            )

        return f"""Generate exactly {count} English sentences for a linguistics experiment.

REQUIREMENTS:
1. Each sentence must contain the word "{target_word}" EXACTLY ONCE.
2. Each sentence must be 10-30 words long.
3. Each sentence must end with punctuation (. ! or ?).
4. The word "{target_word}" must appear as a whole word (not as part of another word).
5. All sentences must be unique and diverse in structure.
6. Sentences should be natural, fluent English.

CONTEXT: {label}
{description}

The sentences should clearly establish this context through surrounding words and meaning, so that the word "{target_word}" is interpreted in the "{label}" sense.{avoid_block}

Return a JSON object with a single key "sentences" containing an array of objects, each with a "text" field:
{{"sentences": [{{"text": "..."}}, {{"text": "..."}}, ...]}}

Generate exactly {count} sentences."""

    async def _call_llm(self, prompt: str, api_key: str, provider: str) -> str:
        """Call LLM API and return raw response text."""
        if provider == "openai":
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            return response.choices[0].message.content
        else:
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

    def _parse_llm_response(
        self, raw: str, target_word: str, group_code: str
    ) -> List[SentenceEntry]:
        """Parse LLM response into SentenceEntry objects."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines[1:] if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON: {text[:200]}...")
            return []

        if isinstance(data, dict):
            for key in ["sentences", "results", "data"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                items = next(
                    (v for v in data.values() if isinstance(v, list)), []
                )
        elif isinstance(data, list):
            items = data
        else:
            logger.error(f"Unexpected JSON shape: {type(data)}")
            return []

        entries = []
        for item in items:
            if isinstance(item, str):
                sentence_text = item
            elif isinstance(item, dict):
                sentence_text = item.get("text", item.get("sentence", ""))
            else:
                continue

            sentence_text = sentence_text.strip()
            if not sentence_text:
                continue

            try:
                span = compute_char_span(sentence_text, target_word)
                entries.append(SentenceEntry(
                    text=sentence_text,
                    group=group_code,
                    target_word=target_word,
                    char_span=span,
                ))
            except ValueError as e:
                logger.warning(f"  Skipping sentence: {e}")

        return entries

    async def generate_and_save(
        self, path: str, **kwargs
    ) -> SentenceSet:
        """Generate a sentence set and save it to disk."""
        ss = await self.generate_sentence_set(**kwargs)
        save_sentence_set(ss, path)
        logger.info(f"Saved sentence set to {path}")
        return ss
