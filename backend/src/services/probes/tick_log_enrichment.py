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
from typing import Dict, Iterable, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from schemas.tokens import ProbeRecord


def load_tick_log(
    session_dir: Path,
) -> Tuple[Dict[Tuple[str, int], Dict[str, Any]], Dict[str, str]]:
    """Read tick_log.jsonl.

    Returns:
        - per-turn dict: {(scenario_name, turn_id): {game_text, analysis, action}}
        - scenario→system_prompt dict: system_prompt is logged only on turn 0
          (see agent_loop.py:287), so we hoist it to apply across all turns
          of the same scenario.

    Returns ({}, {}) if file is missing. Skips malformed lines silently.
    """
    path = session_dir / "tick_log.jsonl"
    if not path.exists():
        return {}, {}
    per_turn: Dict[Tuple[str, int], Dict[str, Any]] = {}
    system_prompts: Dict[str, str] = {}
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
        per_turn[(scenario_name, turn_id)] = {
            "game_text": data.get("game_text"),
            "analysis": data.get("analysis"),
            "action": data.get("action"),
        }
        sp = data.get("system_prompt")
        if sp:
            system_prompts[scenario_name] = sp
    return per_turn, system_prompts


def enrich_records_with_tick_log(
    records: Iterable["ProbeRecord"],
    session_dir: Path,
) -> None:
    """Populate game_text / analysis / action / system_prompt on each record.

    Mutates records in place. No-op for sessions without a tick_log (sentence
    / temporal captures) — those records keep their default None values.
    """
    tick_data, system_prompts = load_tick_log(session_dir)
    if not tick_data and not system_prompts:
        return
    for r in records:
        scenario = getattr(r, 'scenario_id', None)
        turn_id = getattr(r, 'turn_id', None)
        if scenario is None or turn_id is None:
            continue
        tick = tick_data.get((scenario, turn_id))
        if tick:
            r.game_text = tick.get('game_text')
            r.analysis = tick.get('analysis')
            r.action = tick.get('action')
        prev_tick = tick_data.get((scenario, turn_id - 1)) if turn_id > 0 else None
        if prev_tick:
            r.previous_action = prev_tick.get('action')
        sp = system_prompts.get(scenario)
        if sp:
            r.system_prompt = sp
