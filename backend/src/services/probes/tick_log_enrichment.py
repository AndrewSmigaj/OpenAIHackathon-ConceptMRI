"""
Tick log enrichment for agent sessions.

Agent sessions write a `tick_log.jsonl` file with one entry per game tick
({scenario_name, turn_id, game_text, analysis, action, ...}). This module
reads that file and returns a lookup dict keyed by (scenario_name, turn_id)
for merging into ProbeExample construction.

JSONL schema defined by agent_loop.py:278-294.
"""

import json
from pathlib import Path
from typing import Dict, Tuple, Any


def load_tick_log(session_dir: Path) -> Dict[Tuple[str, int], Dict[str, Any]]:
    """Read tick_log.jsonl -> {(scenario_name, turn_id): {game_text, analysis, action}}.

    Returns empty dict if file is missing (sentence-set sessions).
    Skips malformed lines silently.
    """
    path = session_dir / "tick_log.jsonl"
    if not path.exists():
        return {}
    result: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        scenario_name = data.get("scenario_name")
        turn_id = data.get("turn_id")
        if scenario_name is None or turn_id is None:
            continue
        result[(scenario_name, turn_id)] = {
            "game_text": data.get("game_text"),
            "analysis": data.get("analysis"),
            "action": data.get("action"),
        }
    return result
