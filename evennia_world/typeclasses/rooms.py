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

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj.account:
            moved_obj.msg(room_entered=[{
                "room_type": self.get_room_type(),
                "role": "visitor",
            }])

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if moved_obj.account:
            moved_obj.msg(room_left=[{
                "room_type": self.get_room_type(),
            }])


class ResearcherLab(Room):
    """
    Personal research lab. Full control over viz panels.
    Sends role="researcher" with no forced session.
    """

    def get_room_type(self):
        return "lab"

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        # Skip Room's at_object_receive — send our own OOB
        DefaultRoom.at_object_receive(self, moved_obj, source_location, **kwargs)
        if moved_obj.account:
            moved_obj.msg(room_entered=[{
                "room_type": "lab",
                "role": "researcher",
                "session_id": None,
            }])


class MicroWorldRoom(Room):
    """
    Curated micro-world with preset session/schema/viz config.
    Config stored in db.world_config (set by build script from YAML).
    """

    def get_room_type(self):
        return "micro_world"

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        DefaultRoom.at_object_receive(self, moved_obj, source_location, **kwargs)
        if moved_obj.account:
            config = self.db.world_config or {}
            moved_obj.msg(room_entered=[{
                "room_type": "micro_world",
                "role": config.get("role", "visitor"),
                "session_id": config.get("session_id"),
                "clustering_schema": config.get("clustering_schema"),
                "viz_preset": config.get("viz_preset"),
            }])
