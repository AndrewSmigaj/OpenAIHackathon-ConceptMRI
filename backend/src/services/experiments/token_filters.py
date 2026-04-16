#!/usr/bin/env python3
"""
Query-time token filters shared across expert route, cluster route, and
reduction services.
"""

from typing import Dict, List, Optional, Set

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


def _stratified_take(
    by_label: Dict[Optional[str], List[str]],
    max_probes: int,
) -> Set[str]:
    """Shared monotonic stratified picker.

    Monotonicity guarantee: subsample(N) ⊂ subsample(N+1) for all N.

    Achieved by:
      1. Sorting probe_ids ascending within each label group (stable; caller's job).
      2. Sorting label keys deterministically (stable, key=str for None safety).
      3. Allocating `per_label = max_probes // num_labels` to each group, then
         distributing the remainder `extra = max_probes - per_label*num_labels`
         as +1 to the FIRST `extra` labels in the sorted label order. The same
         labels always get priority, so growing max_probes only adds probes,
         never reshuffles.
      4. When max_probes < num_labels, take 1 probe from each of the FIRST
         `max_probes` labels (same sorted label order) — still monotonic with
         the stratified case because label ordering is stable.
    """
    sorted_labels = sorted(by_label.keys(), key=lambda k: (k is None, str(k)))
    num_labels = len(sorted_labels)

    if max_probes <= 0 or num_labels == 0:
        return set()

    if max_probes < num_labels:
        return {by_label[label][0] for label in sorted_labels[:max_probes]}

    per_label = max_probes // num_labels
    extra = max_probes - per_label * num_labels

    keep: Set[str] = set()
    for i, label in enumerate(sorted_labels):
        count = per_label + (1 if i < extra else 0)
        keep.update(by_label[label][:count])
    return keep


def subsample_probes(
    token_records: List[ProbeRecord],
    max_probes: Optional[int],
) -> Optional[Set[str]]:
    """Return a deterministic, monotonic subset of probe_ids stratified by label.

    Returns None when max_probes is None (caller skips the filter).
    """
    if max_probes is None:
        return None
    by_label: Dict[Optional[str], List[str]] = {}
    for t in token_records:
        by_label.setdefault(t.label, []).append(t.probe_id)
    for ids in by_label.values():
        ids.sort()
    return _stratified_take(by_label, max_probes)


def subsample_probes_from_meta(
    token_meta: Dict[str, Dict],
    max_probes: Optional[int],
) -> Optional[Set[str]]:
    """Mirror of subsample_probes for reduction_service's flat meta dict.

    meta[pid] must include 'label'.
    """
    if max_probes is None:
        return None
    by_label: Dict[Optional[str], List[str]] = {}
    for pid, m in token_meta.items():
        by_label.setdefault(m.get("label"), []).append(pid)
    for ids in by_label.values():
        ids.sort()
    return _stratified_take(by_label, max_probes)


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
