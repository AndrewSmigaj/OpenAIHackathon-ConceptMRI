"""
Room typeclasses for LLMud Institute.

Room types:
- Room: base room (hub, social spaces)
- ResearcherLab: sends role="researcher" OOB on entry
- MicroWorldRoom: sends session/schema/preset config OOB on entry
"""

import logging

from evennia import create_object
from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent

logger = logging.getLogger("evennia")


def _purge_recursive(obj):
    """Delete obj and all nested contents.

    Evennia's DefaultObject.delete() calls clear_contents() which MOVES
    children to their home location (DEFAULT_HOME=#2 if unset) before
    deleting the container. Without a recursive pre-pass this leaks
    nested items into the Hub on every scenario rebuild.
    """
    for child in list(obj.contents):
        _purge_recursive(child)
    obj.delete()


class Room(ObjectParent, DefaultRoom):
    """
    Base room. Used for hubs and social spaces.
    Sends room_entered OOB with room_type on entry/exit.
    """

    def format_appearance(self, appearance, looker, **kwargs):
        """Prepend a blank line so the room name is visually separated
        from whatever output came immediately before the look."""
        return "\n" + super().format_appearance(appearance, looker, **kwargs)

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


class ScenarioRoom(Room):
    """
    Room with a scenario state machine. State is stored on the character
    (not the room) so multiple agents can run independently.

    Data-driven probes: YAML states stored on room.db.states, interpreted
    by on_action() and _fire_effects().

    Complex scenarios: subclass and override on_action() with custom logic.
    """

    def get_room_type(self):
        return "scenario"

    def get_display_characters(self, looker, **kwargs):
        """Hide player characters from look output.

        NPCs are DefaultObject subclasses, so they appear under 'things',
        not 'characters'. This prevents the agent from seeing other players
        (e.g. Emily) and getting distracted from scenario NPCs.
        """
        return ""

    def get_display_exits(self, looker, **kwargs):
        """Hide exits to non-scenario rooms (e.g. the hub) from the agent.

        Agents teleported in for a probe run should not be able to wander
        out to unrelated scenarios. Researchers (Developer permission)
        still see all exits for manual testing. The agent account has
        Builder (needed for `goto`) but not Developer, so it gets the
        restricted view.

        Forward-compatible with multi-room scenarios: exits whose
        destination is another ScenarioRoom are whitelisted.
        """
        from evennia.utils.utils import iter_to_str

        account = getattr(looker, "account", None)
        if account and account.check_permstring("Developer"):
            return super().get_display_exits(looker, **kwargs)

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        scenario_exits = [e for e in exits if isinstance(e.destination, ScenarioRoom)]
        if not scenario_exits:
            return ""
        exit_names = iter_to_str(e.get_display_name(looker, **kwargs) for e in scenario_exits)
        return f"|wExits:|n {exit_names}"

    def get_display_things(self, looker, **kwargs):
        """Show objects and NPCs, appending short_desc for NPCs.

        Produces: "You see: a bench, a newspaper, a person sitting on the bench, and a vending machine"
        instead of listing the NPC separately in the room description.
        """
        from typeclasses.npcs import ScenarioNPC
        from collections import defaultdict
        from evennia.utils.utils import iter_to_str

        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)
        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            name = singular if nthings == 1 else plural
            if isinstance(thing, ScenarioNPC) and thing.db.short_desc:
                name = f"{name} {thing.db.short_desc}"
            thing_names.append(name)

        thing_names = iter_to_str(thing_names)
        return f"|wYou see:|n {thing_names}" if thing_names else ""

    def init_scenario(self, character):
        """Initialize scenario state when a character enters.

        Resets both character state and room state so scenarios are
        fully idempotent across runs.
        """
        from typeclasses.npcs import ScenarioNPC

        # 1. Reset character state
        character.db.scenario_state = "initial"
        character.db.scenario_flags = {}
        character.db.proximity = {}

        # 2. Clean up character inventory from previous runs
        for obj in list(character.contents):
            if obj.db.scenario_item:
                obj.delete()

        # 3. Clean NPC inventories (prevents accumulation from give/buy across runs)
        for obj in self.contents:
            if isinstance(obj, ScenarioNPC):
                for held in list(obj.contents):
                    held.delete()

        # 4. Delete all non-NPC, non-exit objects in room (will recreate from config)
        for obj in list(self.contents):
            if isinstance(obj, ScenarioNPC):
                continue
            if obj.destination:  # it's an exit
                continue
            if obj.account:  # it's a character
                continue
            _purge_recursive(obj)

        # 5. Recreate objects from stored config
        for obj_config in (self.db.initial_objects_config or []):
            obj = create_object('typeclasses.objects.Object',
                                key=obj_config['name'], location=self)
            obj.db.desc = obj_config.get('examine', obj_config['name'])
            obj.db.examine_desc = obj_config.get('examine', '')
            if obj_config.get('is_vendor'):
                obj.db.is_vendor = True
            if obj_config.get('is_phone'):
                obj.db.is_phone = True
            if obj_config.get('portable'):
                obj.locks.add("get:all()")
            # Nested contents (e.g. items inside a vendor)
            for child_config in obj_config.get('contents', []):
                child = create_object('typeclasses.objects.Object',
                                      key=child_config['name'], location=obj)
                child.db.desc = child_config.get('examine', child_config['name'])
                child.db.examine_desc = child_config.get('examine', '')
                child.locks.add("get:all()")

        # 6. Reset NPC topic states
        for npc_name, initial_topics in (self.db.initial_npc_states or {}).items():
            for obj in self.contents:
                if isinstance(obj, ScenarioNPC) and obj.key == npc_name:
                    obj.db.unlocked_topics = list(initial_topics)
                    break

        # 7. Restore per-scenario NPC configs (examine_desc, short_desc, etc.)
        active = self.db.active_scenario
        if active and self.db.scenario_npc_configs:
            npc_configs = self.db.scenario_npc_configs.get(active, [])
            for npc_cfg in npc_configs:
                for obj in self.contents:
                    if isinstance(obj, ScenarioNPC) and obj.key == npc_cfg['name']:
                        obj.db.examine_desc = npc_cfg.get('examine_desc', '')
                        obj.db.short_desc = npc_cfg.get('short_desc', '')
                        obj.db.desc = npc_cfg.get('desc', obj.key)
                        break

        # 8. Restore per-scenario states (action definitions)
        if active and self.db.scenario_states:
            scenario_states = self.db.scenario_states.get(active)
            if scenario_states:
                self.db.states = scenario_states

        # 9. Set scenario_id so other code reads the correct value
        if active:
            self.db.scenario_id = active

        # 10. Restore room description
        if self.db.initial_desc:
            self.db.desc = self.db.initial_desc

        # 11. Create personal items for this scenario
        for item_config in (self.db.initial_player_inventory or self.db.player_inventory or []):
            item = create_object('typeclasses.objects.Object',
                                 key=item_config['name'], location=character)
            item.db.desc = item_config.get('examine', item_config['name'])
            item.db.examine_desc = item_config.get('examine', '')
            item.db.scenario_item = True
            item.locks.add("get:all()")

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj.account and self.db.states:
            self.init_scenario(moved_obj)

    def get_available_actions(self, character):
        """Return actions available in the character's current state."""
        state_name = character.db.scenario_state or "initial"
        state = (self.db.states or {}).get(state_name, {})
        flags = character.db.scenario_flags or {}
        actions = []
        for action in state.get("actions", []):
            if action.get("requires") and not flags.get(action["requires"]):
                continue
            actions.append(action)
        return actions

    def get_planning_prompt(self, character):
        """Return the planning prompt for the character's current state."""
        state_name = character.db.scenario_state or "initial"
        state = (self.db.states or {}).get(state_name, {})
        return state.get("planning_prompt", "")

    def on_action(self, caller, action_key, **kwargs):
        """Process a scenario-relevant action.

        Data-driven: matches action_key against current state's actions.
        Override in subclasses for custom logic.

        Returns the matched action dict, or None if no match.
        """
        state_name = caller.db.scenario_state or "initial"
        state = (self.db.states or {}).get(state_name, {})
        flags = caller.db.scenario_flags or {}
        for action in state.get("actions", []):
            if action["command"].lower().strip() != action_key.lower().strip():
                continue
            if action.get("requires") and not flags.get(action["requires"]):
                continue
            self._fire_effects(caller, action.get("effects", []))
            if action.get("transitions_to"):
                caller.db.scenario_state = action["transitions_to"]
            return action
        return None

    def _fire_effects(self, caller, effects):
        """Execute a list of effects from an action."""
        for effect in effects:
            try:
                if "message" in effect:
                    caller.msg(effect["message"])
                elif "npc_react" in effect:
                    caller.msg(effect["npc_react"])
                elif "complete" in effect:
                    caller.db.scenario_result = effect["complete"]
                    caller.msg("[SCENARIO_COMPLETE]")
                elif "update_description" in effect:
                    ud = effect["update_description"]
                    if ud["target"] == "room":
                        self.db.desc = ud["description"]
                    else:
                        for obj in self.contents:
                            if obj.key.lower() == ud["target"].lower():
                                obj.db.examine_desc = ud["description"]
                                break
                elif "set_flag" in effect:
                    if not caller.db.scenario_flags:
                        caller.db.scenario_flags = {}
                    caller.db.scenario_flags[effect["set_flag"]] = True
                elif "remove_flag" in effect:
                    if caller.db.scenario_flags:
                        caller.db.scenario_flags.pop(effect["remove_flag"], None)
                elif "reveal_object" in effect:
                    for obj in self.contents:
                        if obj.key.lower() == effect["reveal_object"].lower():
                            obj.db.visible = True
                            break
                elif "remove_object" in effect:
                    for obj in self.contents:
                        if obj.key.lower() == effect["remove_object"].lower():
                            obj.move_to(None, quiet=True)
                            break
                elif "move_object" in effect:
                    mo = effect["move_object"]
                    for obj in self.contents:
                        if obj.key.lower() == mo["object"].lower():
                            dest_key = mo["to"]
                            if dest_key == "player":
                                target = caller
                            elif dest_key == "room":
                                target = self
                            else:
                                target = caller.search(dest_key)
                            if target:
                                obj.move_to(target, quiet=True)
                            break
            except Exception as e:
                logger.log_err(f"ScenarioRoom effect error: {e}")
