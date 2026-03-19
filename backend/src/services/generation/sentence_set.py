#!/usr/bin/env python3
"""
SentenceSet data model, validation, and I/O for experiments.
Defines sentence entries with group labels and provides validation
to ensure sentences meet experiment requirements.
"""

import json
import re
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


@dataclass
class SentenceEntry:
    """A single sentence for an experiment."""
    text: str               # The sentence (10-30 words)
    group: str              # "A", "B", or "neutral"
    target_word: str        # e.g. "said", "tank", etc.
    char_span: List[int]    # [start, end) 0-based, end-exclusive


@dataclass
class SentenceSet:
    """Complete sentence set for one experiment."""
    name: str                              # Identifier (e.g. "tank_polysemy_v1")
    version: str                           # Schema version "1.0"
    target_word: str                       # Shared target word for all entries
    label_a: str                           # Short label (e.g. "narrative", "military")
    label_b: str                           # Short label (e.g. "factual", "aquatic")
    description_a: str                     # Longer description for generation prompts
    description_b: str
    sentences_a: List[SentenceEntry]
    sentences_b: List[SentenceEntry]
    sentences_neutral: List[SentenceEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)


# --- Validation ---

def compute_char_span(text: str, target_word: str) -> List[int]:
    """Find [start, end) char span of target_word in text using word boundaries.

    Raises ValueError if word not found or found multiple times.
    """
    pattern = r'\b' + re.escape(target_word) + r'\b'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    if len(matches) == 0:
        raise ValueError(f"Target word '{target_word}' not found in: {text}")
    if len(matches) > 1:
        raise ValueError(
            f"Target word '{target_word}' found {len(matches)} times in: {text}"
        )

    m = matches[0]
    return [m.start(), m.end()]


def validate_sentence(
    entry: SentenceEntry,
    existing_texts: Optional[set] = None
) -> List[str]:
    """Validate a single sentence entry. Returns list of error strings (empty = valid)."""
    errors = []

    word_count = len(entry.text.split())
    if word_count < 10:
        errors.append(f"Too few words ({word_count}): {entry.text[:60]}...")
    if word_count > 30:
        errors.append(f"Too many words ({word_count}): {entry.text[:60]}...")

    if entry.text and entry.text[-1] not in '.!?"\':):':
        errors.append(f"Missing ending punctuation: {entry.text[:60]}...")

    pattern = r'\b' + re.escape(entry.target_word) + r'\b'
    matches = list(re.finditer(pattern, entry.text, re.IGNORECASE))
    if len(matches) == 0:
        errors.append(f"Target '{entry.target_word}' not found: {entry.text[:60]}...")
    elif len(matches) > 1:
        errors.append(
            f"Target '{entry.target_word}' appears {len(matches)} times: "
            f"{entry.text[:60]}..."
        )

    if matches and len(matches) == 1:
        expected = [matches[0].start(), matches[0].end()]
        if entry.char_span != expected:
            errors.append(
                f"char_span {entry.char_span} != expected {expected}: "
                f"{entry.text[:60]}..."
            )

    if existing_texts is not None and entry.text in existing_texts:
        errors.append(f"Duplicate sentence: {entry.text[:60]}...")

    return errors


def validate_sentence_set(ss: SentenceSet) -> List[str]:
    """Validate an entire sentence set. Returns list of error strings."""
    errors = []
    existing_texts = set()

    for label, entries, group_code in [
        (ss.label_a, ss.sentences_a, "A"),
        (ss.label_b, ss.sentences_b, "B"),
        ("neutral", ss.sentences_neutral, "neutral"),
    ]:
        for i, entry in enumerate(entries):
            if entry.group != group_code:
                errors.append(
                    f"{label}[{i}]: group='{entry.group}' expected '{group_code}'"
                )

            if entry.target_word != ss.target_word:
                errors.append(
                    f"{label}[{i}]: target_word='{entry.target_word}' "
                    f"!= set target '{ss.target_word}'"
                )

            sentence_errors = validate_sentence(entry, existing_texts)
            for err in sentence_errors:
                errors.append(f"{label}[{i}]: {err}")

            existing_texts.add(entry.text)

    return errors


# --- I/O ---

def _entry_to_dict(entry: SentenceEntry) -> dict:
    return {
        "text": entry.text,
        "group": entry.group,
        "target_word": entry.target_word,
        "char_span": entry.char_span,
    }


def _entry_from_dict(d: dict) -> SentenceEntry:
    return SentenceEntry(
        text=d["text"],
        group=d.get("group", d.get("regime", "A")),  # Backward compat: "regime" → "group"
        target_word=d["target_word"],
        char_span=d["char_span"],
    )


def save_sentence_set(ss: SentenceSet, path: str) -> None:
    """Serialize SentenceSet to JSON file."""
    data = {
        "name": ss.name,
        "version": ss.version,
        "target_word": ss.target_word,
        "label_a": ss.label_a,
        "label_b": ss.label_b,
        "description_a": ss.description_a,
        "description_b": ss.description_b,
        "sentences_a": [_entry_to_dict(e) for e in ss.sentences_a],
        "sentences_b": [_entry_to_dict(e) for e in ss.sentences_b],
        "sentences_neutral": [_entry_to_dict(e) for e in ss.sentences_neutral],
        "metadata": ss.metadata,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_sentence_set(path: str) -> SentenceSet:
    """Load SentenceSet from JSON file. Supports both old and new field names."""
    with open(path, 'r') as f:
        data = json.load(f)

    ss = SentenceSet(
        name=data["name"],
        version=data["version"],
        target_word=data["target_word"],
        label_a=data.get("label_a", data.get("regime_a_label", "")),
        label_b=data.get("label_b", data.get("regime_b_label", "")),
        description_a=data.get("description_a", data.get("regime_a_description", "")),
        description_b=data.get("description_b", data.get("regime_b_description", "")),
        sentences_a=[_entry_from_dict(d) for d in data["sentences_a"]],
        sentences_b=[_entry_from_dict(d) for d in data["sentences_b"]],
        sentences_neutral=[_entry_from_dict(d) for d in data["sentences_neutral"]],
        metadata=data.get("metadata", {}),
    )

    errors = validate_sentence_set(ss)
    if errors:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Validation warnings for {ss.name}: {len(errors)} issues")
        for err in errors:
            logger.warning(f"  {err}")

    return ss


def load_sentence_set_by_name(
    name: str,
    base_dir: str = "data/sentence_sets"
) -> SentenceSet:
    """Load sentence set by name from base directory."""
    path = os.path.join(base_dir, f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sentence set not found: {path}")
    return load_sentence_set(path)


def list_available_sentence_sets(
    base_dir: str = "data/sentence_sets"
) -> List[Dict[str, Any]]:
    """List available sentence sets with quick metadata."""
    results = []
    base = Path(base_dir)

    if not base.exists():
        return results

    for json_file in sorted(base.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            results.append({
                "name": data["name"],
                "target_word": data["target_word"],
                "label_a": data.get("label_a", data.get("regime_a_label", "")),
                "label_b": data.get("label_b", data.get("regime_b_label", "")),
                "count_a": len(data.get("sentences_a", [])),
                "count_b": len(data.get("sentences_b", [])),
                "count_neutral": len(data.get("sentences_neutral", [])),
            })
        except Exception:
            continue

    return results
