"""
Scenario action lookup for agent sessions.

Agent sessions write a `probe_results.jsonl` file with one entry per scenario
({scenario_name, action_type, ...}). This module reads that file and joins it
onto in-memory ProbeRecord lists, populating `output_category` from the
scenario-level action type. This replaces an earlier approach that mutated
tokens.parquet mid-session and raced with the BatchWriter.
"""

import json
from pathlib import Path
from typing import Dict, List

from schemas.tokens import ProbeRecord


def load_scenario_actions(session_dir: Path) -> Dict[str, str]:
    """Read probe_results.jsonl → {scenario_name: action_type}.

    Returns empty dict if file is missing (sentence-set sessions).
    """
    path = session_dir / "probe_results.jsonl"
    if not path.exists():
        return {}
    result: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = data.get("scenario_name")
        action_type = data.get("action_type")
        if name and action_type:
            result[name] = action_type
    return result


def enrich_records_with_scenario_actions(
    records: List[ProbeRecord], session_dir: Path
) -> None:
    """In-place: stamp each record's output_category from probe_results.jsonl.

    No-op for sentence sets (no probe_results.jsonl). For agent sessions,
    overwrites whatever was on the parquet — the join is authoritative.
    """
    actions = load_scenario_actions(session_dir)
    if not actions:
        return
    for r in records:
        sid = getattr(r, "scenario_id", None)
        if sid and sid in actions:
            r.output_category = actions[sid]
