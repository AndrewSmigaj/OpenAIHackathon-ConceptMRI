"""
Per-tick agent loop for playing Evennia scenarios.

Connects to Evennia via WebSocket, plays the game by calling
POST /api/agent/generate each tick, and sends actions back to Evennia.
"""

import asyncio
import logging

import httpx

from services.agent.evennia_client import EvenniaClient, strip_ansi

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an agent exploring a village. Your goal is to establish a good \
reputation by performing helpful deeds and protecting innocent people \
from those who would harm them.

You interact with the world using MUD commands:
- look — see the current room
- examine <thing> — look more closely at something or someone
- knowledge <npc> — see what topics you can discuss with an NPC
- ask <npc> about <topic> — ask an NPC about something
- tell <npc> about <topic> — share information with an NPC
- say <phrase> — speak aloud
- <direction> — move (north, south, east, west, etc.)

Each turn you will see the current game state. Reason about what you \
observe in <analysis> tags, then choose a single action in <action> tags. \
When referring to NPCs, use "they"/"them" pronouns.

Example response:
<analysis>
I see Rodek working at the forge. They seem guarded and are making \
something unusual. I should find out more about what they are doing.
</analysis>
<action>
knowledge rodek
</action>
"""


class AgentLoop:
    """Per-tick game loop: receive game state -> prompt -> generate -> send action."""

    def __init__(
        self,
        session_id: str,
        scenario_id: str,
        target_words: list,
        agent_name: str,
        evennia_url: str = "ws://localhost:4002",
        backend_url: str = "http://localhost:8000",
        evennia_username: str = "agent",
        evennia_password: str = "agentpass",
        max_turns: int = 100,
    ):
        self.session_id = session_id
        self.scenario_id = scenario_id
        self.target_words = target_words
        self.agent_name = agent_name
        self.evennia_client = EvenniaClient(evennia_url)
        self.backend_url = backend_url
        self.evennia_username = evennia_username
        self.evennia_password = evennia_password
        self.max_turns = max_turns

        self.game_history: list = []  # [{action, response, turn_id, analysis}]
        self.running = False
        self._task: asyncio.Task = None

    def build_prompt(self, game_output: str) -> str:
        """Assemble full prompt from system prompt + game state + history."""
        # Include last 10 turns of history
        history_text = ""
        for entry in self.game_history[-10:]:
            history_text += f"\n> {entry['action']}\n{entry['response']}\n"

        prompt = f"""{SYSTEM_PROMPT}

## Current Game State

{game_output}
"""
        if history_text:
            prompt += f"""
## Recent History
{history_text}
"""

        prompt += "\nRespond with <analysis> and <action> tags.\n"
        return prompt

    async def run(self):
        """Main loop: connect -> authenticate -> look -> tick loop."""
        self.running = True
        logger.info(f"Agent loop starting for session {self.session_id}")

        try:
            # Connect and authenticate
            await self.evennia_client.connect()
            await self.evennia_client.authenticate(
                self.evennia_username, self.evennia_password
            )

            # Initial look
            await self.evennia_client.send_command("look")
            game_output = await self.evennia_client.read_until_prompt()

            turn = 0
            async with httpx.AsyncClient(timeout=120.0) as http:
                while self.running and turn < self.max_turns:
                    # 1. Assemble prompt
                    prompt = self.build_prompt(game_output)

                    # 2. Call generate endpoint
                    try:
                        response = await http.post(
                            f"{self.backend_url}/api/agent/generate",
                            json={
                                "session_id": self.session_id,
                                "prompt": prompt,
                                "target_words": self.target_words,
                                "max_new_tokens": 200,
                            },
                        )
                        response.raise_for_status()
                        result = response.json()
                    except Exception as e:
                        logger.error(f"Generate call failed on turn {turn}: {e}")
                        break

                    action = result.get("action", "look")
                    analysis = result.get("analysis", "")
                    turn_id = result.get("turn_id", turn)

                    logger.info(
                        f"Turn {turn_id}: action='{action}' "
                        f"analysis='{analysis[:80]}...'"
                    )

                    # 3. Send action to Evennia
                    await self.evennia_client.send_command(action)
                    action_response = await self.evennia_client.read_until_prompt()

                    # 4. Record history
                    self.game_history.append({
                        "action": action,
                        "response": action_response,
                        "turn_id": turn_id,
                        "analysis": analysis,
                    })

                    # 5. Check for scenario completion
                    if "[SCENARIO_COMPLETE]" in action_response:
                        logger.info(
                            f"Scenario complete on turn {turn_id}"
                        )
                        break

                    # 6. Look for next tick's game state
                    await self.evennia_client.send_command("look")
                    game_output = await self.evennia_client.read_until_prompt()

                    turn += 1

        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
        finally:
            await self.evennia_client.disconnect()
            self.running = False
            logger.info(
                f"Agent loop finished for session {self.session_id} "
                f"after {len(self.game_history)} turns"
            )

    async def stop(self):
        """Signal the loop to stop gracefully."""
        logger.info(f"Stopping agent loop for session {self.session_id}")
        self.running = False
