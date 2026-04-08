"""
Scenario interaction commands for LLMud Institute.

Commands: ask, tell, knowledge, agent start, agent stop.
These enable NPC dialogue and agent session management.
"""

import json
import logging
import os

from commands.command import Command
from typeclasses.npcs import ScenarioNPC

logger = logging.getLogger(__name__)


def _find_npc_in_room(caller, npc_name):
    """Find a ScenarioNPC in the caller's location by name (case-insensitive partial match)."""
    if not caller.location:
        return None
    npc_name_lower = npc_name.strip().lower()
    for obj in caller.location.contents:
        if isinstance(obj, ScenarioNPC) and (
            obj.key.lower() == npc_name_lower or npc_name_lower in obj.key.lower()
        ):
            return obj
    return None


class CmdAsk(Command):
    """
    Ask an NPC about a topic.

    Usage:
      ask <npc> about <topic>

    Example:
      ask rodek about his work
    """

    key = "ask"
    locks = "cmd:all()"

    def parse(self):
        args = self.args.strip()
        if " about " in args:
            parts = args.split(" about ", 1)
            self.npc_name = parts[0].strip()
            self.topic_key = parts[1].strip()
        else:
            self.npc_name = args
            self.topic_key = None

    def func(self):
        if not self.topic_key:
            self.caller.msg("Usage: ask <npc> about <topic>")
            return

        npc = _find_npc_in_room(self.caller, self.npc_name)
        if not npc:
            self.caller.msg(f"You don't see anyone named '{self.npc_name}' here.")
            return

        flags = self.caller.db.scenario_flags or {}
        response, newly_unlocked, flags_to_set, outcome_flag = npc.handle_topic(
            self.topic_key, "ask", flags
        )

        self.caller.msg(response)

        # Update character flags
        if flags_to_set:
            if not self.caller.db.scenario_flags:
                self.caller.db.scenario_flags = {}
            self.caller.db.scenario_flags.update(flags_to_set)

        # Show newly unlocked topics
        for topic_key in newly_unlocked:
            self.caller.msg(f"\n[New topic available: {topic_key}]")

        # Check for scenario completion
        if outcome_flag:
            self.caller.msg("\n[SCENARIO_COMPLETE]")


class CmdTell(Command):
    """
    Tell an NPC about a topic.

    Usage:
      tell <npc> about <topic>

    Example:
      tell rodek about the missing goods
    """

    key = "tell"
    locks = "cmd:all()"

    def parse(self):
        args = self.args.strip()
        if " about " in args:
            parts = args.split(" about ", 1)
            self.npc_name = parts[0].strip()
            self.topic_key = parts[1].strip()
        else:
            self.npc_name = args
            self.topic_key = None

    def func(self):
        if not self.topic_key:
            self.caller.msg("Usage: tell <npc> about <topic>")
            return

        npc = _find_npc_in_room(self.caller, self.npc_name)
        if not npc:
            self.caller.msg(f"You don't see anyone named '{self.npc_name}' here.")
            return

        flags = self.caller.db.scenario_flags or {}
        response, newly_unlocked, flags_to_set, outcome_flag = npc.handle_topic(
            self.topic_key, "tell", flags
        )

        self.caller.msg(response)

        if flags_to_set:
            if not self.caller.db.scenario_flags:
                self.caller.db.scenario_flags = {}
            self.caller.db.scenario_flags.update(flags_to_set)

        for topic_key in newly_unlocked:
            self.caller.msg(f"\n[New topic available: {topic_key}]")

        if outcome_flag:
            self.caller.msg("\n[SCENARIO_COMPLETE]")


class CmdKnowledge(Command):
    """
    See what topics you can discuss with an NPC.

    Usage:
      knowledge <npc>

    Example:
      knowledge rodek
    """

    key = "knowledge"
    locks = "cmd:all()"

    def func(self):
        npc_name = self.args.strip()
        if not npc_name:
            self.caller.msg("Usage: knowledge <npc>")
            return

        npc = _find_npc_in_room(self.caller, npc_name)
        if not npc:
            self.caller.msg(f"You don't see anyone named '{npc_name}' here.")
            return

        flags = self.caller.db.scenario_flags or {}
        self.caller.msg(npc.get_knowledge_display(flags))


class CmdExamineScenario(Command):
    """
    Examine an NPC or object more closely.

    Usage:
      examine <target>

    Shows detailed description if the target has one.
    Falls back to default look if no special description.
    """

    key = "examine"
    aliases = ["exam"]
    locks = "cmd:all()"

    def func(self):
        target_name = self.args.strip()
        if not target_name:
            self.caller.msg("Usage: examine <target>")
            return

        if not self.caller.location:
            return

        # Search room contents and caller's inventory
        target_name_lower = target_name.lower()
        search_areas = list(self.caller.location.contents) + list(self.caller.contents)
        for obj in search_areas:
            if target_name_lower in obj.key.lower():
                examine_desc = obj.db.examine_desc
                if examine_desc:
                    self.caller.msg(examine_desc.strip())
                else:
                    self.caller.msg(obj.db.desc or obj.return_appearance(self.caller))
                return

        self.caller.msg(f"You don't see '{target_name}' here.")


class CmdAgentStart(Command):
    """
    Start an agent session for a scenario.

    Usage:
      agent start <agent_name> <scenario_id>

    Example:
      agent start em suspicious_blacksmith

    Requires Builder permissions. Calls the ConceptMRI backend
    to create an agent session and launch the agent loop.
    """

    key = "agent start"
    locks = "cmd:perm(Builder)"

    def func(self):
        args = self.args.strip().split()
        if len(args) < 2:
            self.caller.msg("Usage: agent start <agent_name> <scenario_id>")
            return

        agent_name = args[0]
        scenario_id = args[1]

        # Use Twisted's web client for HTTP call
        from twisted.internet import reactor, defer
        from twisted.web.client import Agent, readBody
        from twisted.web.http_headers import Headers

        agent = Agent(reactor)
        body = json.dumps({
            "session_name": f"{agent_name}_{scenario_id}",
            "scenario_id": scenario_id,
            "target_words": ["they", "them"],
            "bootstrap_session_id": "",
            "agent_name": agent_name,
            "auto_start": True,
            "evennia_username": os.environ.get("EVENNIA_AGENT_USER", "agent"),
            "evennia_password": os.environ.get("EVENNIA_AGENT_PASS", ""),
        }).encode("utf-8")

        class _StringProducer:
            def __init__(self, body):
                self.body = body
                self.length = len(body)

            def startProducing(self, consumer):
                consumer.write(self.body)
                return defer.succeed(None)

            def stopProducing(self):
                pass

            def pauseProducing(self):
                pass

            def resumeProducing(self):
                pass

        from zope.interface import implementer
        from twisted.web.iweb import IBodyProducer
        implementer(IBodyProducer)(_StringProducer)

        @defer.inlineCallbacks
        def _do_start():
            try:
                producer = _StringProducer(body)
                response = yield agent.request(
                    b"POST",
                    b"http://localhost:8000/api/agent/start",
                    Headers({"Content-Type": ["application/json"]}),
                    producer,
                )
                resp_body = yield readBody(response)
                result = json.loads(resp_body)
                self.caller.msg(f"Agent session started: {result.get('session_id', 'unknown')}")
            except Exception as e:
                self.caller.msg(f"Failed to start agent: {e}")

        _do_start()


class CmdAgentStop(Command):
    """
    Stop the running agent session.

    Usage:
      agent stop <session_id>

    Requires Builder permissions.
    """

    key = "agent stop"
    locks = "cmd:perm(Builder)"

    def func(self):
        session_id = self.args.strip()
        if not session_id:
            self.caller.msg("Usage: agent stop <session_id>")
            return

        from twisted.internet import reactor, defer
        from twisted.web.client import Agent, readBody
        from twisted.web.http_headers import Headers

        agent = Agent(reactor)
        body = json.dumps({"session_id": session_id}).encode("utf-8")

        class _StringProducer:
            def __init__(self, body):
                self.body = body
                self.length = len(body)

            def startProducing(self, consumer):
                consumer.write(self.body)
                return defer.succeed(None)

            def stopProducing(self):
                pass

            def pauseProducing(self):
                pass

            def resumeProducing(self):
                pass

        @defer.inlineCallbacks
        def _do_stop():
            try:
                producer = _StringProducer(body)
                response = yield agent.request(
                    b"POST",
                    b"http://localhost:8000/api/agent/stop",
                    Headers({"Content-Type": ["application/json"]}),
                    producer,
                )
                resp_body = yield readBody(response)
                result = json.loads(resp_body)
                self.caller.msg(f"Agent session stopped: {result.get('state', 'unknown')}, {result.get('total_turns', 0)} turns")
            except Exception as e:
                self.caller.msg(f"Failed to stop agent: {e}")

        _do_stop()
