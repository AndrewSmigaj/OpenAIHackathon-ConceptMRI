#!/usr/bin/env python3
"""
SentenceSet data model, validation, and I/O for experiments.
N-group design: supports arbitrary number of groups (not hardcoded A/B/C).
"""

import json
import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class SentenceEntry:
    """A single sentence for an experiment."""
    text: str                                        # The sentence (10-30 words)
    group: str                                       # Matches parent SentenceGroup.label
    target_word: str                                 # e.g. "tank"
    categories: Optional[Dict[str, str]] = None      # Multi-axis (e.g. {"structure": "action"})


@dataclass
class SentenceGroup:
    """A group of sentences sharing one semantic label."""
    label: str                                       # e.g. "aquarium" — the identity
    description: str                                 # Longer text for generation prompts
    sentences: List[SentenceEntry] = field(default_factory=list)


@dataclass
class SentenceSet:
    """Complete sentence set for one experiment. Supports N groups."""
    name: str                                        # Identifier (e.g. "tank_polysemy_v3")
    version: str                                     # Schema version "3.0"
    target_word: str                                 # Shared target word for all entries
    groups: List[SentenceGroup]                      # N groups, each with label + sentences
    axes: Optional[List[Dict[str, Any]]] = None      # Input category axes
    output_axes: Optional[List[Dict[str, Any]]] = None  # Output classification axes
    generate_output: bool = True
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

    if existing_texts is not None and entry.text in existing_texts:
        errors.append(f"Duplicate sentence: {entry.text[:60]}...")

    return errors


def validate_sentence_set(ss: SentenceSet) -> List[str]:
    """Validate an entire sentence set. Returns list of error strings."""
    errors = []
    existing_texts = set()

    for g in ss.groups:
        for i, entry in enumerate(g.sentences):
            if entry.group != g.label:
                errors.append(
                    f"{g.label}[{i}]: group='{entry.group}' expected '{g.label}'"
                )

            if entry.target_word != ss.target_word:
                errors.append(
                    f"{g.label}[{i}]: target_word='{entry.target_word}' "
                    f"!= set target '{ss.target_word}'"
                )

            sentence_errors = validate_sentence(entry, existing_texts)
            for err in sentence_errors:
                errors.append(f"{g.label}[{i}]: {err}")

            existing_texts.add(entry.text)

    return errors


# --- I/O ---

def _entry_to_dict(entry: SentenceEntry) -> dict:
    d = {
        "text": entry.text,
        "group": entry.group,
        "target_word": entry.target_word,
    }
    if entry.categories is not None:
        d["categories"] = entry.categories
    return d


def _entry_from_dict(d: dict) -> SentenceEntry:
    return SentenceEntry(
        text=d["text"],
        group=d.get("group", ""),
        target_word=d["target_word"],
        categories=d.get("categories"),
    )


def save_sentence_set(ss: SentenceSet, path: str) -> None:
    """Serialize SentenceSet to JSON file."""
    data = {
        "name": ss.name,
        "version": ss.version,
        "target_word": ss.target_word,
        "groups": [
            {
                "label": g.label,
                "description": g.description,
                "sentences": [_entry_to_dict(e) for e in g.sentences],
            }
            for g in ss.groups
        ],
        "metadata": ss.metadata,
    }
    if ss.axes is not None:
        data["axes"] = ss.axes
    if ss.output_axes is not None:
        data["output_axes"] = ss.output_axes
    if not ss.generate_output:
        data["generate_output"] = False

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_sentence_set(path: str) -> SentenceSet:
    """Load SentenceSet from JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)

    groups = []
    for g in data["groups"]:
        entries = [_entry_from_dict(d) for d in g.get("sentences", [])]
        groups.append(SentenceGroup(
            label=g["label"],
            description=g.get("description", ""),
            sentences=entries,
        ))

    ss = SentenceSet(
        name=data["name"],
        version=data["version"],
        target_word=data["target_word"],
        groups=groups,
        axes=data.get("axes"),
        output_axes=data.get("output_axes"),
        generate_output=data.get("generate_output", True),
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
    """Load sentence set by name from base directory (searches subdirectories)."""
    matches = list(Path(base_dir).rglob(f"{name}.json"))
    if not matches:
        raise FileNotFoundError(f"Sentence set '{name}' not found in {base_dir}")
    return load_sentence_set(str(matches[0]))


def list_available_sentence_sets(
    base_dir: str = "data/sentence_sets"
) -> List[Dict[str, Any]]:
    """List available sentence sets with quick metadata."""
    results = []
    base = Path(base_dir)

    if not base.exists():
        return results

    for json_file in sorted(base.rglob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            groups = data.get("groups", [])
            labels = [g["label"] for g in groups]
            counts = {g["label"]: len(g.get("sentences", [])) for g in groups}
            entry = {
                "name": data["name"],
                "target_word": data["target_word"],
                "labels": labels,
                "counts": counts,
                "total": sum(counts.values()),
            }
            results.append(entry)
        except Exception:
            continue

    return results
