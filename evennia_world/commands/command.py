"""
Commands

Commands describe the input the account can do to the game.

All game commands should inherit from Command (for simple commands)
or MuxCommand (for commands needing switch/lhs/rhs parsing).

Both send a prompt after every command via at_post_cmd(), which signals
end-of-output to WebSocket clients (see Evennia Howto-Command-Prompt).
"""

from evennia.commands.command import Command as BaseCommand
from evennia import default_cmds


class Command(BaseCommand):
    """
    Base command for LLMud Institute.
    """

    def at_post_cmd(self):
        """Send prompt after every command — signals end-of-output to clients."""
        self.caller.msg(prompt=">")


class MuxCommand(default_cmds.MuxCommand):
    """
    MuxCommand with prompt support. Use for commands that need
    switch parsing (/switches) or lhs/rhs splitting (arg1 = arg2).
    """

    def at_post_cmd(self):
        """Send prompt after every command — signals end-of-output to clients."""
        self.caller.msg(prompt=">")
