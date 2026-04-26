"""
MUD commands for scenario interactions.

Each command implements a MUD mechanic (proximity, position, etc.)
then calls room.on_action() to notify the scenario state machine.
"""

from commands.command import Command, MuxCommand
from evennia.commands.cmdhandler import CMD_NOMATCH


class CmdScenarioFallback(Command):
    """Route any unrecognized command to room.on_action so YAML-defined
    scenario actions (e.g. "ready spray", "dial aps") work without a
    dedicated Cmd class per verb."""

    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Huh?")
            return
        room = self.caller.location
        if room and hasattr(room, "on_action"):
            result = room.on_action(self.caller, raw)
            if result is not None:
                return
        self.caller.msg(f"Command '{raw}' is not available. Type 'actions' for help.")


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
        self.caller.location.msg_contents(
            f"{self.caller.key} backs away.",
            exclude=self.caller,
        )
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
        self.caller.location.msg_contents(
            f"{self.caller.key} sits down on {target}.",
            exclude=self.caller,
        )
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
      shout <word>

    Example:
      shout thief
      shout scam
    """

    key = "shout"
    locks = "cmd:all()"

    def func(self):
        args = self.args.strip()
        if args:
            self.caller.msg(f'You shout "{args}!"')
            self.caller.location.msg_contents(
                f'{self.caller.key} shouts "{args}!"',
                exclude=self.caller,
            )
            action_str = f"shout {args}"
        else:
            self.caller.msg("You shout.")
            self.caller.location.msg_contents(
                f"{self.caller.key} shouts.",
                exclude=self.caller,
            )
            action_str = "shout"
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, action_str)


class CmdRefuse(Command):
    """
    Firmly say no to what someone is offering.

    Usage:
      refuse
    """

    key = "refuse"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You firmly say no.")
        self.caller.location.msg_contents(
            f"{self.caller.key} firmly says no.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "refuse")


class CmdLeave(Command):
    """
    Turn and walk away from the current situation.

    Usage:
      leave
    """

    key = "leave"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You turn and walk away.")
        self.caller.location.msg_contents(
            f"{self.caller.key} turns and walks away.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "leave")


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
        self.caller.location.msg_contents(
            f"{self.caller.key} shoves {target}.",
            exclude=self.caller,
        )
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
        room.msg_contents(
            f"{self.caller.key} hands {item.key} to {target.key}.",
            exclude=self.caller,
        )

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


class CmdGreet(Command):
    """
    Greet someone in a friendly way.

    Usage:
      greet <target>
    """

    key = "greet"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Greet who?")
            return
        self.caller.msg(f"You greet {target} warmly.")
        self.caller.location.msg_contents(
            f"{self.caller.key} greets {target} warmly.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"greet {target}")


class CmdFollow(Command):
    """
    Follow someone.

    Usage:
      follow <target>
    """

    key = "follow"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Follow who?")
            return
        self.caller.msg(f"You follow {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} follows {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"follow {target}")


class CmdChat(Command):
    """
    Start a casual conversation with someone.

    Usage:
      chat <target>
    """

    key = "chat"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Chat with who?")
            return
        self.caller.msg(f"You strike up a conversation with {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} starts chatting with {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"chat {target}")


class CmdBeckon(Command):
    """
    Gesture for someone to come to you.

    Usage:
      beckon <target>
    """

    key = "beckon"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Beckon who?")
            return
        self.caller.msg(f"You gesture for {target} to come closer.")
        self.caller.location.msg_contents(
            f"{self.caller.key} gestures for {target} to come closer.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"beckon {target}")


class CmdComfort(Command):
    """
    Try to comfort someone.

    Usage:
      comfort <target>
    """

    key = "comfort"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Comfort who?")
            return
        self.caller.msg(f"You try to comfort {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} tries to comfort {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"comfort {target}")


class CmdEscort(Command):
    """
    Walk alongside someone protectively.

    Usage:
      escort <target>
    """

    key = "escort"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Escort who?")
            return
        self.caller.msg(f"You walk alongside {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} walks alongside {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"escort {target}")


class CmdWave(Command):
    """
    Wave at someone or for attention.

    Usage:
      wave
    """

    key = "wave"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You wave.")
        self.caller.location.msg_contents(
            f"{self.caller.key} waves.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "wave")


class CmdTapShoulder(Command):
    """
    Tap someone on the shoulder.

    Usage:
      tap <target>
    """

    key = "tap"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Tap who?")
            return
        self.caller.msg(f"You tap {target} on the shoulder.")
        self.caller.location.msg_contents(
            f"{self.caller.key} taps {target} on the shoulder.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"tap {target}")


class CmdOffer(MuxCommand):
    """
    Hold out an item for someone.

    Usage:
      offer <item> to <target>

    Example:
      offer water to person
    """

    key = "offer"
    locks = "cmd:all()"
    rhs_split = ("=", " to ")

    def func(self):
        if not self.lhs or not self.rhs:
            self.caller.msg("Usage: offer <item> to <target>")
            return

        room = self.caller.location
        if not room:
            return

        item_name = self.lhs.strip()
        target_name = self.rhs.strip()

        self.caller.msg(f"You offer {item_name} to {target_name}.")
        room.msg_contents(
            f"{self.caller.key} offers {item_name} to {target_name}.",
            exclude=self.caller,
        )

        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"offer {item_name} to {target_name}")


class CmdSteady(Command):
    """
    Physically steady someone who is unsteady.

    Usage:
      steady <target>
    """

    key = "steady"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Steady who?")
            return
        self.caller.msg(f"You reach out and steady {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} reaches out and steadies {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"steady {target}")


class CmdDodge(Command):
    """
    Sidestep or duck around someone.

    Usage:
      dodge
    """

    key = "dodge"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You sidestep quickly.")
        self.caller.location.msg_contents(
            f"{self.caller.key} sidesteps quickly.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "dodge")


class CmdSprint(Command):
    """
    Run away at full speed.

    Usage:
      sprint
    """

    key = "sprint"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You break into a sprint.")
        self.caller.location.msg_contents(
            f"{self.caller.key} breaks into a sprint.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "sprint")


class CmdPhotograph(Command):
    """
    Take a photo of something or someone.

    Usage:
      photograph <target>
    """

    key = "photograph"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Photograph what?")
            return
        self.caller.msg(f"You take a photo of {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} takes a photo of {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"photograph {target}")


class CmdWarn(Command):
    """
    Verbally warn someone off.

    Usage:
      warn <target>
    """

    key = "warn"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Warn who?")
            return
        self.caller.msg(f"You warn {target} to back off.")
        self.caller.location.msg_contents(
            f"{self.caller.key} warns {target} to back off.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"warn {target}")


class CmdSignal(Command):
    """
    Signal for attention or help.

    Usage:
      signal
    """

    key = "signal"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You signal for help.")
        self.caller.location.msg_contents(
            f"{self.caller.key} signals for help.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "signal")


class CmdBlock(Command):
    """
    Physically block someone's path.

    Usage:
      block <target>
    """

    key = "block"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Block who?")
            return
        self.caller.msg(f"You step in front of {target}, blocking their path.")
        self.caller.location.msg_contents(
            f"{self.caller.key} steps in front of {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"block {target}")


class CmdStare(Command):
    """
    Stare someone down.

    Usage:
      stare <target>
    """

    key = "stare"
    locks = "cmd:all()"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("Stare at who?")
            return
        self.caller.msg(f"You stare hard at {target}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} stares hard at {target}.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"stare {target}")


class CmdCrouch(Command):
    """
    Duck down out of sight.

    Usage:
      crouch
    """

    key = "crouch"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You crouch down out of sight.")
        self.caller.location.msg_contents(
            f"{self.caller.key} crouches down.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "crouch")


class CmdWhistle(Command):
    """
    Whistle loudly for attention.

    Usage:
      whistle
    """

    key = "whistle"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You whistle loudly.")
        self.caller.location.msg_contents(
            f"{self.caller.key} whistles loudly.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "whistle")


class CmdIgnore(Command):
    """
    Deliberately look away and disengage.

    Usage:
      ignore
    """

    key = "ignore"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("You deliberately look away.")
        self.caller.location.msg_contents(
            f"{self.caller.key} deliberately looks away.",
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, "ignore")


class CmdGoto(Command):
    """
    Teleport to a named room. Builder+ only.

    Usage:
        goto <room name> [scenario=<scenario_name>]

    Searches for a room by name and moves the caller there directly.
    Used by agent loops for scenario entry. The optional scenario=
    argument sets the room's active scenario so init_scenario()
    restores the correct NPC configs and action definitions.
    """

    key = "goto"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: goto <room name> [scenario=<name>]")
            return
        args = self.args.strip()
        scenario = None
        if " scenario=" in args:
            parts = args.rsplit(" scenario=", 1)
            args = parts[0]
            scenario = parts[1]
        target = self.caller.search(args, global_search=True)
        if not target:
            return
        if scenario and hasattr(target, 'db'):
            target.db.active_scenario = scenario
        if self.caller.location == target:
            return  # Already in the room — skip the spurious "leaving X for X" broadcast
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


# ====================================================================
# Table-driven commands — compact verb definitions for scenario actions
# ====================================================================

def _build_target_cmd(key, help_text, actor_tpl, room_tpl):
    """Build a Command subclass that takes a single target argument."""
    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg(f"{key.title()} who?")
            return
        self.caller.msg(actor_tpl.format(target=target))
        self.caller.location.msg_contents(
            room_tpl.format(caller=self.caller.key, target=target),
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"{key} {target}")
    cls_name = "Cmd" + "".join(w.title() for w in key.split())
    return cls_name, type(cls_name, (Command,), {
        "__doc__": f"{help_text}\n\nUsage:\n  {key} <target>",
        "key": key, "locks": "cmd:all()", "func": func,
    })


def _build_noarg_cmd(key, help_text, actor_msg, room_tpl):
    """Build a Command subclass that takes no arguments."""
    def func(self):
        self.caller.msg(actor_msg)
        self.caller.location.msg_contents(
            room_tpl.format(caller=self.caller.key),
            exclude=self.caller,
        )
        room = self.caller.location
        if hasattr(room, "on_action"):
            room.on_action(self.caller, key)
    cls_name = "Cmd" + "".join(w.title() for w in key.split())
    return cls_name, type(cls_name, (Command,), {
        "__doc__": f"{help_text}\n\nUsage:\n  {key}",
        "key": key, "locks": "cmd:all()", "func": func,
    })


def _build_mux_cmd(key, prep, help_text, actor_tpl, room_tpl):
    """Build a MuxCommand subclass: verb <item> <prep> <target>."""
    def func(self):
        if not self.lhs or not self.rhs:
            self.caller.msg(f"Usage: {key} <item> {prep} <target>")
            return
        item = self.lhs.strip()
        target = self.rhs.strip()
        self.caller.msg(actor_tpl.format(item=item, target=target))
        room = self.caller.location
        room.msg_contents(
            room_tpl.format(caller=self.caller.key, item=item, target=target),
            exclude=self.caller,
        )
        if hasattr(room, "on_action"):
            room.on_action(self.caller, f"{key} {item} {prep} {target}")
    cls_name = "Cmd" + "".join(w.title() for w in key.split())
    return cls_name, type(cls_name, (MuxCommand,), {
        "__doc__": f"{help_text}\n\nUsage:\n  {key} <item> {prep} <target>",
        "key": key, "locks": "cmd:all()",
        "rhs_split": ("=", f" {prep} "),
        "func": func,
    })


# --- Target commands (verb <target>) ---
for _def in [
    ("kneel", "Kneel beside someone.", "You kneel beside {target}.", "{caller} kneels beside {target}."),
    ("whisper", "Whisper to someone.", "You whisper to {target}.", "{caller} whispers to {target}."),
    ("point", "Point at someone or something.", "You point at {target}.", "{caller} points at {target}."),
    ("grab", "Grab someone or something.", "You grab {target}.", "{caller} grabs {target}."),
    ("nudge", "Nudge someone gently.", "You nudge {target} gently.", "{caller} nudges {target}."),
    ("shield", "Step in front to shield someone.", "You step in front of {target}, shielding them.", "{caller} shields {target}."),
    ("shake", "Shake someone.", "You shake {target}.", "{caller} shakes {target}."),
    ("push", "Push someone or something.", "You push {target}.", "{caller} pushes {target}."),
    ("pull", "Pull someone toward you.", "You pull {target} toward you.", "{caller} pulls {target}."),
    ("lift", "Lift someone up.", "You lift {target} up.", "{caller} lifts {target} up."),
    ("catch", "Catch someone before they fall.", "You catch {target}.", "{caller} catches {target}."),
    ("fan", "Fan someone to cool them.", "You fan {target}.", "{caller} fans {target}."),
    ("bandage", "Bandage someone.", "You bandage {target}.", "{caller} bandages {target}."),
    ("poke", "Poke someone.", "You poke {target}.", "{caller} pokes {target}."),
    ("elbow", "Elbow someone.", "You elbow {target}.", "{caller} elbows {target}."),
    ("trip", "Trip someone.", "You trip {target}.", "{caller} trips {target}."),
    ("pin", "Pin someone down.", "You pin {target} down.", "{caller} pins {target} down."),
    ("calm", "Try to calm someone down.", "You try to calm {target} down.", "{caller} tries to calm {target} down."),
    ("pat", "Pat someone reassuringly.", "You pat {target} on the back.", "{caller} pats {target} on the back."),
    ("motion", "Motion to someone.", "You motion to {target}.", "{caller} motions to {target}."),
    ("brace", "Brace someone to keep them upright.", "You brace {target}.", "{caller} braces {target}."),
    ("prop", "Prop someone up.", "You prop {target} up.", "{caller} props {target} up."),
    ("lunge", "Lunge at someone.", "You lunge at {target}.", "{caller} lunges at {target}."),
    ("swat", "Swat at someone.", "You swat at {target}.", "{caller} swats at {target}."),
    ("yank", "Yank someone or something.", "You yank {target}.", "{caller} yanks {target}."),
    ("hoist", "Hoist someone up.", "You hoist {target} up.", "{caller} hoists {target} up."),
    ("cradle", "Cradle someone gently.", "You cradle {target}.", "{caller} cradles {target}."),
    ("glare", "Glare at someone.", "You glare at {target}.", "{caller} glares at {target}."),
    ("restrain", "Restrain someone.", "You restrain {target}.", "{caller} restrain {target}."),
    ("drag", "Drag someone.", "You drag {target}.", "{caller} drags {target}."),
    ("rock", "Rock someone gently.", "You rock {target} gently.", "{caller} rocks {target} gently."),
    ("squeeze", "Squeeze someone's hand.", "You squeeze {target}'s hand.", "{caller} squeezes {target}'s hand."),
    ("shade", "Shade someone from the sun.", "You shade {target} from the sun.", "{caller} shades {target}."),
    ("splash", "Splash water on someone.", "You splash water on {target}.", "{caller} splashes water on {target}."),
    ("taunt", "Taunt someone.", "You taunt {target}.", "{caller} taunts {target}."),
    ("mock", "Mock someone.", "You mock {target}.", "{caller} mocks {target}."),
    ("corner", "Corner someone.", "You corner {target}.", "{caller} corners {target}."),
    ("crowd", "Crowd someone.", "You crowd {target}.", "{caller} crowds {target}."),
    ("clutch", "Clutch someone.", "You clutch {target}.", "{caller} clutches {target}."),
    ("usher", "Usher someone along.", "You usher {target} along.", "{caller} ushers {target} along."),
    ("bump", "Bump into someone.", "You bump {target}.", "{caller} bumps {target}."),
    ("rub", "Rub someone's back.", "You rub {target}'s back.", "{caller} rubs {target}'s back."),
    ("scold", "Scold someone.", "You scold {target}.", "{caller} scolds {target}."),
]:
    _n, _c = _build_target_cmd(*_def)
    globals()[_n] = _c

# --- No-arg commands ---
for _def in [
    ("stamp", "Stamp your feet.", "You stamp your feet.", "{caller} stamps their feet."),
    ("clap", "Clap your hands.", "You clap your hands.", "{caller} claps their hands."),
    ("pace", "Pace back and forth.", "You pace back and forth.", "{caller} paces back and forth."),
    ("duck", "Duck down.", "You duck down.", "{caller} ducks down."),
    ("backpedal", "Back away quickly.", "You backpedal quickly.", "{caller} backpedals quickly."),
    ("jog", "Jog away.", "You jog away.", "{caller} jogs away."),
    ("linger", "Linger nearby.", "You linger nearby.", "{caller} lingers nearby."),
    ("freeze", "Freeze in place.", "You freeze in place.", "{caller} freezes in place."),
    ("flinch", "Flinch.", "You flinch.", "{caller} flinches."),
    ("bolt", "Bolt away.", "You bolt.", "{caller} bolts."),
    ("pivot", "Pivot on your heel.", "You pivot on your heel.", "{caller} pivots on their heel."),
    ("cower", "Cower.", "You cower.", "{caller} cowers."),
]:
    _n, _c = _build_noarg_cmd(*_def)
    globals()[_n] = _c

# --- Mux commands (verb <item> <prep> <target>) ---
for _def in [
    ("toss", "to", "Toss something to someone.", "You toss {item} to {target}.", "{caller} tosses {item} to {target}."),
    ("slide", "to", "Slide something to someone.", "You slide {item} to {target}.", "{caller} slides {item} to {target}."),
    ("drape", "over", "Drape something over someone.", "You drape {item} over {target}.", "{caller} drapes {item} over {target}."),
    ("press", "on", "Press something on someone.", "You press {item} on {target}.", "{caller} presses {item} on {target}."),
    ("pour", "on", "Pour something on someone.", "You pour {item} on {target}.", "{caller} pours {item} on {target}."),
    ("wrap", "around", "Wrap something around someone.", "You wrap {item} around {target}.", "{caller} wraps {item} around {target}."),
    ("tuck", "around", "Tuck something around someone.", "You tuck {item} around {target}.", "{caller} tucks {item} around {target}."),
]:
    _n, _c = _build_mux_cmd(*_def)
    globals()[_n] = _c
