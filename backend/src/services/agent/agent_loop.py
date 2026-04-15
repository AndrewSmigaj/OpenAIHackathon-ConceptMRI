"""
Agent loop for playing Evennia scenarios with probe capture.

Connects to Evennia via WebSocket, plays scenarios using Harmony-formatted
multi-turn conversations, captures residual stream activations at target
word positions via forward pass on the full token sequence.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from services.agent.evennia_client import EvenniaClient
from services.agent.harmony_parser import parse_harmony_channels

logger = logging.getLogger(__name__)

_ARTICLE_RE = re.compile(r'\b(the|a|an)\s+', re.IGNORECASE)


def strip_articles(cmd: str) -> str:
    """Strip English articles from MUD commands for exact Evennia key matching."""
    return _ARTICLE_RE.sub('', cmd)


DEFAULT_SYSTEM_PROMPT = """\
You are exploring a world. You encounter people along the way.
Help or comfort friends. Avoid or confront enemies — do not
appease them. These are intentions you express by selecting one
of the room's listed actions, NOT commands you can type. "Help",
"comfort", "avoid", "confront", and "appease" are not verbs you
can use.

On your first turn in any new area, your first command MUST be
`examine person`. Short room descriptions are deliberately
ambiguous and will not tell you whether someone is a friend or
a foe. Examine is how you learn more about someone. Once you
have the examine text, choose from the room's listed actions.

The scenario actions for the current room appear in the game
text as `command — description`. The command on the LEFT of the
dash is what you type — it may be one word (`withdraw`) or two
words (`inquire person`). Type the full command exactly as shown.
Do not type the description on the right. Do not type only part
of the command. The listed actions are the ONLY scenario actions
available — do not invent commands like `approach`, `confront`,
`help`, or `assist` unless they appear in the list.

Use they/them pronouns. Check your inventory — you may already
be carrying something useful.

You interact with the world using MUD commands. The basic ones:
- look — see the current room
- examine <thing> — look more closely at something or someone
- inventory — see what you are carrying

Each turn you will see the current game state. Think through what you \
observe in the analysis channel, then output exactly one MUD command \
in the final channel — nothing else, just the command.
"""

SCENARIOS_DIR = Path(__file__).resolve().parents[4] / "data" / "worlds" / "scenarios"


class AgentLoop:
    """Scenario loop: iterate scenarios, capture activations, play via Harmony format."""

    def __init__(
        self,
        session_id: str,
        scenario_id: str,
        target_words: list,
        agent_name: str,
        service=None,
        scenario_list: list = None,
        data_lake_path: str = None,
        evennia_url: str = "ws://localhost:4002",
        evennia_username: str = "agent",
        evennia_password: str = "",
        max_ticks: int = 5,
        system_prompt: str = None,
        session_name: str = None,
    ):
        self.session_id = session_id
        self.session_name = session_name or session_id
        self.scenario_id = scenario_id
        self.target_words = target_words
        self.agent_name = agent_name
        self.service = service
        self.scenario_list = scenario_list or []
        self.data_lake_path = data_lake_path
        self.evennia_client = EvenniaClient(evennia_url)
        self.evennia_username = evennia_username
        self.evennia_password = evennia_password
        self.max_ticks = max_ticks
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.running = False

    async def run(self):
        """Connect to Evennia, iterate scenarios, disconnect."""
        self.running = True
        logger.info(f"Agent loop starting for session {self.session_id}")

        results_path = None
        if self.data_lake_path:
            results_dir = Path(self.data_lake_path) / self.session_id
            results_dir.mkdir(parents=True, exist_ok=True)
            results_path = results_dir / "probe_results.jsonl"

        try:
            await self.evennia_client.connect()
            await self.evennia_client.authenticate(
                self.evennia_username, self.evennia_password
            )

            # Collect condition labels from scenario configs and update session metadata
            labels = []
            for sname in self.scenario_list:
                cfg = self._load_scenario_config(sname)
                if cfg:
                    cond = cfg.get("condition", sname)
                    if cond not in labels:
                        labels.append(cond)
            if labels and self.service:
                session_file = Path(self.service.session_mgr.sessions_dir) / f"{self.session_id}.json"
                if session_file.exists():
                    with open(session_file, "r") as f:
                        metadata = json.load(f)
                    metadata["labels"] = labels
                    with open(session_file, "w") as f:
                        json.dump(metadata, f, indent=2)

            for scenario_name in self.scenario_list:
                if not self.running:
                    break
                await self._run_one_scenario(scenario_name, results_path)

            # Write human-readable session analysis
            if self.data_lake_path:
                session_dir = Path(self.data_lake_path) / self.session_id
                self._write_session_analysis(session_dir)

        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
        finally:
            await self.evennia_client.disconnect()
            self.running = False
            logger.info(f"Agent loop finished for session {self.session_id}")

    async def _run_one_scenario(self, scenario_name: str, results_path: Path):
        """Play one scenario with multi-turn Harmony format + probe capture."""
        config = self._load_scenario_config(scenario_name)
        if not config:
            self._write_probe_result(results_path, {
                "scenario_name": scenario_name, "error": "yaml_not_found",
                "timestamp": datetime.now().isoformat(),
            })
            return

        room_name = config["rooms"][0]["name"]
        target_words = config.get("target_words", self.target_words)
        condition_label = config.get("condition", scenario_name)
        action_lookup = self._build_action_lookup(config)

        # Tick log file for replay/review
        tick_log_path = None
        if results_path:
            tick_log_path = results_path.parent / "tick_log.jsonl"

        # Teleport to scenario room
        logger.info(f"Teleporting to '{room_name}'")
        await self.evennia_client.send_command(f"goto {room_name} scenario={scenario_name}")
        tel_response = await self.evennia_client.read_until_prompt()
        logger.info(f"Teleport response: {tel_response[:200]}")
        if "could not find" in tel_response.lower():
            self._write_probe_result(results_path, {
                "scenario_name": scenario_name, "error": "teleport_failed",
                "timestamp": datetime.now().isoformat(),
            })
            return

        # Bootstrap: initial look + inventory + actions
        await self.evennia_client.send_command("look")
        look_output = await self.evennia_client.read_until_prompt()
        await self.evennia_client.send_command("inventory")
        inv_output = await self.evennia_client.read_until_prompt()
        await self.evennia_client.send_command("actions")
        actions_output = await self.evennia_client.read_until_prompt()

        # Multi-turn conversation: developer instructions + game state turns
        messages = [
            {"role": "developer", "content": self.system_prompt},
            {"role": "user", "content": look_output + "\n" + inv_output + "\n" + actions_output},
        ]

        tokenizer = self.service.orchestrator.tokenizer
        device = self.service.orchestrator.model.device
        complete = False
        tick = 0
        last_action = ""
        last_analysis = ""

        while not complete and self.running and tick < self.max_ticks:
            # Current game text is the latest user message
            game_text = messages[-1]["content"]
            logger.info(
                f"--- {scenario_name} tick {tick} ---\n"
                f"  Game text ({len(game_text)} chars): {game_text[:200]}..."
            )

            # 1. Tokenize full conversation with Harmony chat template
            inputs = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
                model_identity="You are an agent exploring a world.",
            )
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs["attention_mask"].to(device)

            # 2. Generate action (hooks OFF)
            generated_text, gen_ids = await asyncio.to_thread(
                self.service.orchestrator.generate_continuation_with_ids,
                input_ids, 800, attention_mask, False,
            )
            channels = parse_harmony_channels(generated_text)
            last_action = channels["action"] or "look"
            last_analysis = channels["analysis"]
            logger.info(
                f"  Generated ({len(generated_text)} chars):\n{generated_text}"
            )
            logger.info(f"  Parsed action: '{last_action}'")

            # 3. Capture on full sequence (hooks ON): input + generated
            #    Only capture at positions in the current turn (skip system prompt + history)
            full_ids = input_ids[0].tolist() + gen_ids
            if len(messages) > 1:
                prefix_inputs = tokenizer.apply_chat_template(
                    messages[:-1], add_generation_prompt=False,
                    return_dict=True, return_tensors="pt",
                    model_identity="You are an agent exploring a world.",
                )
                current_turn_start = prefix_inputs["input_ids"].shape[1]
            else:
                current_turn_start = 0
            prompt_token_count = input_ids.shape[1]
            result, _ = await asyncio.to_thread(
                self.service.probe_tick,
                self.session_id, game_text, target_words,
                turn_id=tick, scenario_id=scenario_name,
                token_ids=full_ids,
                label=condition_label,
                min_position=current_turn_start,
                prompt_token_count=prompt_token_count,
            )
            logger.info(
                f"  Captured {result['probes_written']} probes, "
                f"positions: {result['target_positions']}, "
                f"total tokens: {len(full_ids)}"
            )

            # 4. Send action to Evennia (strip articles for exact key matching)
            last_action = strip_articles(last_action)
            await self.evennia_client.send_command(last_action)
            response = await self.evennia_client.read_until_prompt()
            logger.info(f"  Evennia response: {response[:300]}")

            # 5. Update conversation (clean text only — template raises on channel tags)
            messages.append({"role": "assistant", "content": last_action})
            messages.append({"role": "user", "content": response})

            # 6. Write tick log
            if tick_log_path:
                tick_entry = {
                    "scenario_name": scenario_name,
                    "turn_id": tick,
                    "system_prompt": self.system_prompt if tick == 0 else None,
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                    "game_text": game_text,
                    "generated_text": generated_text,
                    "analysis": last_analysis,
                    "action": last_action,
                    "evennia_response": response,
                    "probes_written": result["probes_written"],
                    "target_positions": result["target_positions"],
                    "total_tokens": len(full_ids),
                    "timestamp": datetime.now().isoformat(),
                }
                with open(tick_log_path, "a") as f:
                    f.write(json.dumps(tick_entry) + "\n")

            # 7. Check exit
            if "[SCENARIO_COMPLETE]" in response:
                complete = True

            tick += 1

        # Record result
        action_meta = action_lookup.get(last_action.lower().strip(), {})
        self._write_probe_result(results_path, {
            "scenario_name": scenario_name,
            "scene_id": config.get("scene_id", scenario_name),
            "condition": config.get("condition", ""),
            "ground_truth": config.get("ground_truth", ""),
            "target_words": target_words,
            "action_id": action_meta.get("action_id"),
            "action_command": last_action,
            "action_type": action_meta.get("action_type", "unknown"),
            "correct": action_meta.get("correct"),
            "canary": action_meta.get("canary", False),
            "ticks": tick,
            "analysis": last_analysis,
            "timestamp": datetime.now().isoformat(),
            "error": None if complete else "max_ticks_exceeded",
        })

        logger.info(
            f"Scenario {scenario_name} finished: "
            f"action='{last_action}' correct={action_meta.get('correct')} ticks={tick}"
        )

    def _load_scenario_config(self, scenario_name: str) -> dict:
        """Load scenario YAML from data/worlds/scenarios/."""
        yaml_path = SCENARIOS_DIR / f"{scenario_name}.yaml"
        if not yaml_path.exists():
            logger.error(f"Scenario YAML not found: {yaml_path}")
            return None
        with open(yaml_path) as f:
            return yaml.safe_load(f)

    def _build_action_lookup(self, config: dict) -> dict:
        """Build command string → action metadata dict from scenario config."""
        lookup = {}
        for room in config.get("rooms", []):
            for state in room.get("states", {}).values():
                for action in state.get("actions", []):
                    key = action["command"].lower().strip()
                    lookup[key] = {
                        "action_id": action.get("id"),
                        "action_type": action.get("type", "unknown"),
                        "correct": action.get("correct"),
                        "canary": action.get("canary", False),
                    }
        return lookup

    def _write_probe_result(self, results_path: Path, data: dict):
        """Append one JSON line to probe_results.jsonl."""
        if results_path is None:
            return
        with open(results_path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def _write_session_analysis(self, session_dir: Path):
        """Generate human-readable session_analysis.md from tick_log."""
        tick_log = session_dir / "tick_log.jsonl"
        if not tick_log.exists():
            return

        ticks = [json.loads(line) for line in tick_log.open() if line.strip()]
        lines = []
        lines.append(f"# Agent Session Analysis — {self.session_name}")
        lines.append(f"Session: {self.session_id}")
        lines.append(f"Total ticks: {len(ticks)}")
        lines.append(f"Scenarios: {', '.join(self.scenario_list)}")
        lines.append("")
        lines.append("**System prompt:**")
        lines.append(f"```")
        lines.append(self.system_prompt.strip())
        lines.append(f"```")
        lines.append("")

        for t in ticks:
            action = t.get("action", "?")
            scenario = t.get("scenario_name", "?")
            label = t.get("label", "?")
            lines.append(f"## Tick {t.get('turn_id', '?')} — {scenario} — action=\"{action}\" label={label}")
            lines.append(f"total_tokens={t.get('total_tokens', '?')}  probes_written={t.get('probes_written', '?')}")
            lines.append("")

            game_text = t.get("game_text", "")
            lines.append(f"**Game text ({len(game_text)} chars):**")
            lines.append(game_text[:500])
            lines.append("")

            analysis = t.get("analysis", "")
            lines.append(f"**Analysis ({len(analysis)} chars):**")
            lines.append(analysis[:300])
            lines.append("")

            lines.append(f"**Action:** {action}")

            response = t.get("evennia_response", "")
            lines.append(f"**Evennia response ({len(response)} chars):**")
            lines.append(response[:300])
            lines.append("\n---\n")

        # Write to session directory
        (session_dir / "session_analysis.md").write_text("\n".join(lines))

        # Also write to reports directory with descriptive filename
        reports_dir = session_dir.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        labels_str = "-".join(self.target_words[:2]) if self.target_words else ""
        session_short = self.session_id.replace("session_", "")
        report_name = f"{date_str}_{self.session_name}_{labels_str}_{session_short}.md"
        (reports_dir / report_name).write_text("\n".join(lines))
        logger.info(f"Session analysis written to {reports_dir / report_name}")

    async def stop(self):
        """Signal the loop to stop gracefully."""
        logger.info(f"Stopping agent loop for session {self.session_id}")
        self.running = False
