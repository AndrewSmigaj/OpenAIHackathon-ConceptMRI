"""
Room typeclasses for LLMud Institute.

Room types:
- Room: base room (hub, social spaces)
- ResearcherLab: sends role="researcher" OOB on entry
- MicroWorldRoom: sends session/schema/preset config OOB on entry
"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Base room. Used for hubs and social spaces.
    Sends room_entered OOB with room_type on entry/exit.
    """

    def get_room_type(self):
        return self.db.room_type or "hub"

    def _get_role_for(self, character):
        """Determine role from account permissions. Builder+ = researcher."""
        account = character.account
        if not account:
            return "visitor"
        if account.check_permstring("Builder"):
            return "researcher"
        return "visitor"

    def _send_room_oob(self, character):
        """Send room_entered OOB to a character. Override in subclasses."""
        character.msg(room_entered=[{
            "room_type": self.get_room_type(),
            "role": self._get_role_for(character),
        }])

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj.account:
            self._send_room_oob(moved_obj)

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if moved_obj.account:
            moved_obj.msg(room_left=[{
                "room_type": self.get_room_type(),
            }])


class ResearcherLab(Room):
    """
    Personal research lab. Full control over viz panels.
    Sends role based on permissions, with no forced session.
    """

    def get_room_type(self):
        return "lab"

    def _send_room_oob(self, character):
        character.msg(room_entered=[{
            "room_type": "lab",
            "role": self._get_role_for(character),
            "session_id": None,
        }])


class MicroWorldRoom(Room):
    """
    Curated micro-world with preset session/schema/viz config.
    Config stored in db.world_config (set by build script from YAML).
    """

    def get_room_type(self):
        return "micro_world"

    def _send_room_oob(self, character):
        config = self.db.world_config or {}
        character.msg(room_entered=[{
            "room_type": "micro_world",
            "role": self._get_role_for(character),
            "session_id": config.get("session_id"),
            "clustering_schema": config.get("clustering_schema"),
            "viz_preset": config.get("viz_preset"),
        }])
