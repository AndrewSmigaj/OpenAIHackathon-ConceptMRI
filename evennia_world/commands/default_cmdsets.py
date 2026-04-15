"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from commands.command import MuxCommand
from commands.navigation import CmdHub
from commands.scenario_commands import (
    CmdAsk, CmdTell, CmdKnowledge, CmdExamineScenario,
    CmdAgentStart, CmdAgentStop,
)
from commands.mud_commands import (
    CmdApproach, CmdWithdraw, CmdHide, CmdSit, CmdLean,
    CmdWait, CmdFlee, CmdShout, CmdRefuse, CmdLeave,
    CmdAssist, CmdSnatch, CmdShove,
    CmdSearch, CmdInquire, CmdActions,
    CmdPass, CmdGive, CmdBuy, CmdCall, CmdGoto,
    CmdGreet, CmdFollow, CmdChat,
    CmdBeckon, CmdComfort, CmdEscort, CmdWave, CmdTapShoulder,
    CmdOffer, CmdSteady, CmdDodge, CmdSprint, CmdPhotograph,
    CmdWarn, CmdSignal, CmdBlock, CmdStare, CmdCrouch,
    CmdWhistle, CmdIgnore,
    # Table-driven commands (v7)
    CmdKneel, CmdWhisper, CmdPoint, CmdGrab, CmdNudge,
    CmdShield, CmdShake, CmdPush, CmdPull, CmdLift,
    CmdCatch, CmdFan, CmdBandage, CmdPoke, CmdElbow,
    CmdTrip, CmdPin, CmdCalm, CmdPat, CmdMotion,
    CmdBrace, CmdProp, CmdLunge, CmdSwat, CmdYank,
    CmdHoist, CmdCradle, CmdGlare, CmdRestrain, CmdDrag,
    CmdRock, CmdSqueeze, CmdShade, CmdSplash, CmdTaunt,
    CmdMock, CmdCorner, CmdCrowd, CmdClutch, CmdUsher,
    CmdBump, CmdRub, CmdScold,
    CmdStamp, CmdClap, CmdPace, CmdDuck, CmdBackpedal,
    CmdJog, CmdLinger, CmdFreeze, CmdFlinch, CmdBolt,
    CmdPivot, CmdCower,
    CmdToss, CmdSlide, CmdDrape, CmdPress, CmdPour,
    CmdWrap, CmdTuck,
)


class CmdLook(default_cmds.CmdLook, MuxCommand):
    """Look at location or object. Sends prompt after output."""
    pass


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.add(CmdLook())
        self.add(CmdGoto())
        self.add(CmdHub())
        self.add(CmdAsk())
        self.add(CmdTell())
        self.add(CmdKnowledge())
        self.add(CmdExamineScenario())
        self.add(CmdAgentStart())
        self.add(CmdAgentStop())
        self.add(CmdApproach())
        self.add(CmdWithdraw())
        self.add(CmdHide())
        self.add(CmdSit())
        self.add(CmdLean())
        self.add(CmdWait())
        self.add(CmdFlee())
        self.add(CmdShout())
        self.add(CmdRefuse())
        self.add(CmdLeave())
        self.add(CmdAssist())
        self.add(CmdSnatch())
        self.add(CmdShove())
        self.add(CmdSearch())
        self.add(CmdInquire())
        self.add(CmdActions())
        self.add(CmdPass())
        self.add(CmdGive())
        self.add(CmdBuy())
        self.add(CmdCall())
        self.add(CmdGreet())
        self.add(CmdFollow())
        self.add(CmdChat())
        self.add(CmdBeckon())
        self.add(CmdComfort())
        self.add(CmdEscort())
        self.add(CmdWave())
        self.add(CmdTapShoulder())
        self.add(CmdOffer())
        self.add(CmdSteady())
        self.add(CmdDodge())
        self.add(CmdSprint())
        self.add(CmdPhotograph())
        self.add(CmdWarn())
        self.add(CmdSignal())
        self.add(CmdBlock())
        self.add(CmdStare())
        self.add(CmdCrouch())
        self.add(CmdWhistle())
        self.add(CmdIgnore())
        # Table-driven commands (v7)
        for cmd_cls in [
            CmdKneel, CmdWhisper, CmdPoint, CmdGrab, CmdNudge,
            CmdShield, CmdShake, CmdPush, CmdPull, CmdLift,
            CmdCatch, CmdFan, CmdBandage, CmdPoke, CmdElbow,
            CmdTrip, CmdPin, CmdCalm, CmdPat, CmdMotion,
            CmdBrace, CmdProp, CmdLunge, CmdSwat, CmdYank,
            CmdHoist, CmdCradle, CmdGlare, CmdRestrain, CmdDrag,
            CmdRock, CmdSqueeze, CmdShade, CmdSplash, CmdTaunt,
            CmdMock, CmdCorner, CmdCrowd, CmdClutch, CmdUsher,
            CmdBump, CmdRub, CmdScold,
            CmdStamp, CmdClap, CmdPace, CmdDuck, CmdBackpedal,
            CmdJog, CmdLinger, CmdFreeze, CmdFlinch, CmdBolt,
            CmdPivot, CmdCower,
            CmdToss, CmdSlide, CmdDrape, CmdPress, CmdPour,
            CmdWrap, CmdTuck,
        ]:
            self.add(cmd_cls())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
