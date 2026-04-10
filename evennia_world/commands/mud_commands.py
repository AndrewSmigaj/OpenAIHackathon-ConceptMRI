"""
MUD commands for scenario interactions.

Each command implements a MUD mechanic (proximity, position, etc.)
then calls room.on_action() to notify the scenario state machine.
"""

from commands.command import Command, MuxCommand


class CmdApproach(Command):
    """
    Approach someone or something.

    Usage:
      approach <target>
    """

    key = "approach"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Approach who?")
            return
        if not self.caller.db.proximity:
            self.caller.db.proximity = {}
        self.caller.db.proximity[target] = "near"
        self.caller.msg(f"You approach {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"approach {target}")


class CmdWithdraw(Command):
    """
    Back away from someone or something.

    Usage:
      withdraw
    """

    key = "withdraw"
    locks = "cmd:all()"

    def func(self):
        if self.caller.db.proximity:
            for target in self.caller.db.proximity:
                self.caller.db.proximity[target] = "far"
        self.caller.msg("You withdraw.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "withdraw")


class CmdHide(Command):
    """
    Hide from view.

    Usage:
      hide
    """

    key = "hide"
    locks = "cmd:all()"

    def func(self):
        self.caller.db.hidden = True
        self.caller.msg("You hide.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "hide")


class CmdSit(Command):
    """
    Sit down on something.

    Usage:
      sit <target>
    """

    key = "sit"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Sit where?")
            return
        self.caller.db.position = f"sitting on {target}"
        self.caller.msg(f"You sit down on {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"sit {target}")


class CmdLean(Command):
    """
    Lean against something.

    Usage:
      lean
    """

    key = "lean"
    locks = "cmd:all()"

    def func(self):
        self.caller.db.position = "leaning"
        self.caller.msg("You lean back.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "lean")


class CmdWait(Command):
    """
    Wait and observe.

    Usage:
      wait
    """

    key = "wait"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You wait.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "wait")


class CmdFlee(Command):
    """
    Flee the area.

    Usage:
      flee
    """

    key = "flee"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You flee.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "flee")


class CmdShout(Command):
    """
    Shout or call out.

    Usage:
      shout
    """

    key = "shout"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You shout.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "shout")


class CmdAssist(Command):
    """
    Offer help to someone.

    Usage:
      assist <target>
    """

    key = "assist"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Assist who?")
            return
        self.caller.msg(f"You offer to assist {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"assist {target}")


class CmdSnatch(Command):
    """
    Take something forcefully.

    Usage:
      snatch <target>
    """

    key = "snatch"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Snatch what?")
            return
        self.caller.msg(f"You snatch {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"snatch {target}")


class CmdShove(Command):
    """
    Shove someone away from you.

    Usage:
      shove <target>
    """

    key = "shove"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Shove who?")
            return
        self.caller.msg(f"You shove {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"shove {target}")


class CmdSearch(Command):
    """
    Search or rummage through something.

    Usage:
      search <target>
    """

    key = "search"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Search what?")
            return
        self.caller.msg(f"You search {target}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"search {target}")


class CmdInquire(Command):
    """
    Ask about something.

    Usage:
      inquire <target> <topic>
    """

    key = "inquire"
    locks = "cmd:all()"

    def func(self):
        args = self.args.strip()
        if not args:
            self.caller.msg("Inquire about what?")
            return
        self.caller.msg(f"You inquire about {args}.")
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"inquire {args}")


class CmdActions(Command):
    """
    List available actions in the current scenario.

    Usage:
      actions
    """

    key = "actions"
    locks = "cmd:all()"

    def func(self):
        room = self.caller.location
        if not hasattr(room, "get_available_actions"):
            self.caller.msg("No scenario actions available here.")
            return
        actions = room.get_available_actions(self.caller)
        if not actions:
            self.caller.msg("No actions available.")
            return
        lines = []
        for action in actions:
            lines.append(f"{action['command']} — {action['text']}")
        prompt = room.get_planning_prompt(self.caller)
        if prompt:
            lines.append("")
            lines.append(prompt)
        self.caller.msg("\n".join(lines))


class CmdPass(MuxCommand):
    """
    Pick up an item from the room and hand it to someone.

    Usage:
      pass <item> to <target>

    Example:
      pass newspaper to person

    Picks up a portable item from the room and gives it
    directly to another character or NPC.
    """

    key = "pass"
    locks = "cmd:all()"
    rhs_split = ("=", " to ")

    def func(self):
        if not self.lhs or not self.rhs:
            self.caller.msg("Usage: pass <item> to <target>")
            return

        room = self.caller.location
        if not room:
            return

        # Find item in room
        item = self.caller.search(self.lhs, location=room)
        if not item:
            return

        # Check portability
        if not item.access(self.caller, "get"):
            self.caller.msg(f"You can't pick up {item.key}.")
            return

        # Find recipient in room
        target = self.caller.search(self.rhs, location=room)
        if not target:
            return

        # Pick up and hand over
        item.move_to(self.caller, quiet=True, move_type="get")
        item.move_to(target, quiet=True, move_type="give")
        self.caller.msg(f"You pick up {item.key} and hand it to {target.key}.")

        # Explicit on_action — the at_give hook fires "give X to Y"
        # which won't match "pass X to Y" in scenario YAML
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"pass {item.key} to {target.key}")


class CmdGive(MuxCommand):
    """
    Hand something in your inventory to someone.

    Usage:
      give <item> to <target>

    Example:
      give phone to person

    Gives an item you are carrying to another character or NPC.
    """

    key = "give"
    locks = "cmd:all()"
    rhs_split = ("=", " to ")

    def func(self):
        if not self.lhs or not self.rhs:
            self.caller.msg("Usage: give <item> to <target>")
            return

        room = self.caller.location
        if not room:
            return

        # Find item in caller's inventory
        item = self.caller.search(self.lhs, location=self.caller)
        if not item:
            return

        # Find recipient in room
        target = self.caller.search(self.rhs, location=room)
        if not target:
            return

        item.move_to(target, quiet=True, move_type="give")
        self.caller.msg(f"You hand {item.key} to {target.key}.")

        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"give {item.key} to {target.key}")


class CmdBuy(MuxCommand):
    """
    Buy something from a vendor.

    Usage:
      buy <item>
      buy <item> for <target>

    Example:
      buy drink
      buy drink for person

    Finds a vendor in the room, purchases the item, and
    optionally gives it to someone.
    """

    key = "buy"
    locks = "cmd:all()"
    rhs_split = (" for ", "=")

    def func(self):
        if not self.lhs:
            self.caller.msg("Usage: buy <item> [for <target>]")
            return

        room = self.caller.location
        if not room:
            return

        # Find vendor in room
        vendor = None
        for obj in room.contents:
            if obj.db.is_vendor:
                vendor = obj
                break
        if not vendor:
            self.caller.msg("There's nothing to buy from here.")
            return

        # Find item in vendor's contents
        item_name = self.lhs.strip().lower()
        item = None
        for obj in vendor.contents:
            if obj.key.lower() == item_name or item_name in obj.key.lower():
                item = obj
                break
        if not item:
            self.caller.msg(f"They don't have that for sale.")
            return

        # Move item to caller
        item.move_to(self.caller, quiet=True, move_type="get")

        # If recipient specified, hand it over
        if self.rhs:
            target = self.caller.search(self.rhs.strip(), location=room)
            if not target:
                return
            item.move_to(target, quiet=True, move_type="give")
            self.caller.msg(
                f"You buy {item.key} from {vendor.key} and offer it to {target.key}."
            )
            if hasattr(room, "on_action"):
                room.on_action(self.caller, f"buy {item.key} for {target.key}")
        else:
            self.caller.msg(f"You buy {item.key} from {vendor.key}.")
            if hasattr(room, "on_action"):
                room.on_action(self.caller, f"buy {item.key}")


class CmdGoto(Command):
    """
    Teleport to a named room. Builder+ only.

    Usage:
        goto <room name>

    Searches for a room by name and moves the caller there directly.
    Used by agent loops for scenario entry.
    """

    key = "goto"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: goto <room name>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        self.caller.move_to(target, move_type="teleport")


class CmdCall(Command):
    """
    Make a phone call.

    Usage:
      call <target>

    Example:
      call 911

    Requires a phone object in the room or your inventory.
    """

    key = "call"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Call who?")
            return

        room = self.caller.location
        if not room:
            return

        # Find phone in room or inventory
        phone = None
        for obj in room.contents:
            if obj.db.is_phone:
                phone = obj
                break
        if not phone:
            for obj in self.caller.contents:
                if obj.db.is_phone:
                    phone = obj
                    break
        if not phone:
            self.caller.msg("You don't have anything to make a call with.")
            return

        self.caller.msg(f"You pick up the {phone.key} and dial {target}.")
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"call {target}")
