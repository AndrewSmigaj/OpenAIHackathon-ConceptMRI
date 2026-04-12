"""
Scenario action lookup for agent sessions.

Agent sessions write a `probe_results.jsonl` file with one entry per scenario
({scenario_name, action_type, ground_truth, correct, ...}). This module reads
that file and joins it onto in-memory ProbeRecord lists, populating
`output_category` and `output_category_json` from the scenario-level action
data. This replaces an earlier approach that mutated tokens.parquet mid-session
and raced with the BatchWriter.
"""

import json
from pathlib import Path
from typing import Dict, List

from schemas.tokens import ProbeRecord


def load_scenario_actions(session_dir: Path) -> Dict[str, Dict[str, str]]:
    """Read probe_results.jsonl → {scenario_name: {axis_id: value}}.

    Returns empty dict if file is missing (sentence-set sessions). Each
    scenario maps to a dict of three axes:
      - action_type: "friend" | "enemy"  (what the agent picked)
      - ground_truth: "friend" | "foe"   (what the NPC actually was)
      - correct: "correct" | "incorrect" (whether the agent picked correctly)
    """
    path = session_dir / "probe_results.jsonl"
    if not path.exists():
        return {}
    result: Dict[str, Dict[str, str]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = data.get("scenario_name")
        action_type = data.get("action_type")
        if not name or not action_type:
            continue
        result[name] = {
            "action_type": action_type,
            "ground_truth": data.get("ground_truth") or data.get("condition") or "",
            "correct": "correct" if data.get("correct") else "incorrect",
        }
    return result


def enrich_records_with_scenario_actions(
    records: List[ProbeRecord], session_dir: Path
) -> None:
    """In-place: stamp each record's output_category + output_category_json
    from probe_results.jsonl.

    No-op for sentence sets (no probe_results.jsonl). For agent sessions,
    overwrites whatever was on the parquet — the join is authoritative.

    `output_category` is the primary string used for grouping the rightmost
    Sankey output nodes (kept as action_type for backwards compatibility with
    existing rendered sessions). `output_category_json` exposes three coloring
    axes — `_compute_output_axes` in output_category_nodes.py picks them up
    automatically and they show up in the frontend Output Color dropdown.
    """
    actions = load_scenario_actions(session_dir)
    if not actions:
        return
    for r in records:
        sid = getattr(r, "scenario_id", None)
        if sid and sid in actions:
            axes = actions[sid]
            r.output_category = axes["action_type"]
            r.output_category_json = json.dumps(axes)
