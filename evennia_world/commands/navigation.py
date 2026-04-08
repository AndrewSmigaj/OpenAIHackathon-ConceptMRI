"""
Navigation commands for LLMud Institute.
"""

from evennia import search_object
from commands.command import Command


class CmdHub(Command):
    """
    Teleport back to the Observer Hub.

    Usage:
      hub

    Instantly returns you to the Observer Hub, the central nexus
    of the LLMud Institute.
    """

    key = "hub"
    locks = "cmd:all()"

    def func(self):
        hub = search_object("#2")
        if not hub:
            self.caller.msg("Could not find the Observer Hub.")
            return

        hub = hub[0]
        if self.caller.location == hub:
            self.caller.msg("You are already in the Observer Hub.")
            return

        self.caller.move_to(hub, quiet=False)
