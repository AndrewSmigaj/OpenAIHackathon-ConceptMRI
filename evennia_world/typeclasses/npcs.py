"""
Scenario NPC typeclass.

NPCs with topic-based dialogue and flag-gated unlocking for
agent research scenarios. Topics are set by the scenario YAML
loader; flags are stored per-character for concurrent agent support.
"""

from evennia.objects.objects import DefaultObject

from .objects import ObjectParent


class ScenarioNPC(ObjectParent, DefaultObject):
    """NPC with topic-based ask/tell dialogue and flag-gated topic unlocking."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.topics = {}           # {topic_key: {desc, type, response, unlocks, requires, sets_flag, outcome_flag}}
        self.db.unlocked_topics = []  # topic keys currently available (starts with initial_topics)
        self.db.examine_desc = ""     # narrative description for examine command
        self.db.npc_name = self.key   # display name

    def get_available_topics(self, flags):
        """Return topics that are unlocked AND whose requires flags are satisfied.

        Args:
            flags: dict of flag_name -> bool from character.db.scenario_flags

        Returns:
            list of (topic_key, topic_dict) tuples
        """
        available = []
        for topic_key in self.db.unlocked_topics:
            topic = self.db.topics.get(topic_key)
            if not topic:
                continue
            required_flag = topic.get("requires")
            if required_flag and not flags.get(required_flag):
                continue
            available.append((topic_key, topic))
        return available

    def get_knowledge_display(self, flags):
        """Format available topics for the knowledge command.

        Returns a string like:
            Rodek
              You could ask or tell about:
                his work         -- what he's making
                the village      -- what's been happening around here
        """
        available = self.get_available_topics(flags)
        if not available:
            return f"{self.db.npc_name}\n  No topics available."

        lines = [f"{self.db.npc_name}", "  You could ask or tell about:"]
        for topic_key, topic in available:
            desc = topic.get("desc", "")
            topic_type = topic.get("type", "ask")
            lines.append(f"    {topic_key:<20s} -- {desc}")
        return "\n".join(lines)

    def handle_topic(self, topic_key, topic_type, flags):
        """Handle an ask/tell interaction.

        Args:
            topic_key: the topic string (e.g. "his work")
            topic_type: "ask" or "tell"
            flags: dict from character.db.scenario_flags

        Returns:
            (response_text, newly_unlocked, flags_to_set, outcome_flag_or_None)
            - response_text: str — NPC's response
            - newly_unlocked: list[str] — topic keys now available
            - flags_to_set: dict[str, bool] — flags to add to character
            - outcome_flag: str or None — terminal scenario flag
        """
        # Check if topic exists
        topic = self.db.topics.get(topic_key)
        if not topic:
            return (f'{self.db.npc_name} doesn\'t seem to understand what you mean.', [], {}, None)

        # Check if topic is unlocked
        if topic_key not in self.db.unlocked_topics:
            # Check if it's gated by a requires flag
            required_flag = topic.get("requires")
            if required_flag and not flags.get(required_flag):
                return (f'{self.db.npc_name} doesn\'t seem to understand what you mean.', [], {}, None)
            # Not unlocked and no flag path — unavailable
            return (f'{self.db.npc_name} doesn\'t seem to understand what you mean.', [], {}, None)

        # Check requires flag (for topics that are unlocked but still need a flag)
        required_flag = topic.get("requires")
        if required_flag and not flags.get(required_flag):
            return (f'{self.db.npc_name} doesn\'t seem to understand what you mean.', [], {}, None)

        # Check topic type matches
        expected_type = topic.get("type", "ask")
        if topic_type != expected_type:
            if expected_type == "tell":
                return (f"You'd need to tell {self.db.npc_name} about that, not ask.", [], {}, None)
            else:
                return (f"You'd need to ask {self.db.npc_name} about that, not tell.", [], {}, None)

        # Success — deliver response
        response_text = topic.get("response", "").strip()

        # Handle unlocks (direct same-NPC topic unlocking)
        newly_unlocked = []
        unlocks = topic.get("unlocks", [])
        for unlock_key in unlocks:
            if unlock_key not in self.db.unlocked_topics and unlock_key in self.db.topics:
                self.db.unlocked_topics.append(unlock_key)
                newly_unlocked.append(unlock_key)

        # Handle flags
        flags_to_set = {}
        sets_flag = topic.get("sets_flag")
        if sets_flag:
            flags_to_set[sets_flag] = True

        # Handle outcome flag
        outcome_flag = topic.get("outcome_flag")

        return (response_text, newly_unlocked, flags_to_set, outcome_flag)
