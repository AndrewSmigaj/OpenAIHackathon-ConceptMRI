#!/usr/bin/env python3
"""
Query-time token filters shared across expert route, cluster route, and
reduction services.
"""

from typing import Dict, List, Set

from schemas.tokens import ProbeRecord


def pick_last_occurrence(token_records: List[ProbeRecord]) -> Set[str]:
    """Return probe_ids with max target_char_offset per
    (session_id, input_text, target_word).

    Probes where target_char_offset is None are always kept — the filter is
    a no-op for non-agent captures (sentence / temporal), which don't
    populate target_char_offset.
    """
    # group_key -> (max_offset, probe_id)
    best: Dict[tuple, tuple] = {}
    keep: Set[str] = set()

    for t in token_records:
        if t.target_char_offset is None:
            keep.add(t.probe_id)
            continue

        key = (t.session_id, t.input_text, t.target_word)
        current = best.get(key)
        if current is None or t.target_char_offset > current[0]:
            best[key] = (t.target_char_offset, t.probe_id)

    keep.update(pid for _, pid in best.values())
    return keep


def pick_last_occurrence_from_meta(token_meta: Dict[str, Dict]) -> Set[str]:
    """Same logic as pick_last_occurrence for reduction_service's flat
    meta dict.

    meta[key] must include: input_text, target_word, target_char_offset,
    session_id. Keys where target_char_offset is None are always kept.
    """
    best: Dict[tuple, tuple] = {}
    keep: Set[str] = set()

    for pid, m in token_meta.items():
        offset = m.get("target_char_offset")
        if offset is None:
            keep.add(pid)
            continue

        key = (m.get("session_id"), m.get("input_text"), m.get("target_word"))
        current = best.get(key)
        if current is None or offset > current[0]:
            best[key] = (offset, pid)

    keep.update(pid for _, pid in best.values())
    return keep
