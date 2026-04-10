# Scenarios — Claude Code Cognitive Scaffold

This is the primary reference for designing, building, and running interactive probe scenarios. Scenarios are self-contained mini-worlds where an agent makes decisions about an NPC, and we capture model activations at each decision point.

Related: `docs/architecturescenarios.md` (full architecture spec), `docs/steeringandscenarios.md` (research design), `CLAUDE.md` (project context)

## How Scenarios Work

A scenario is a YAML file that defines a room, objects, an NPC, and a set of available actions. An agent enters the room, examines the NPC, and chooses an action. The model's residual stream activations are captured at the target word ("person") each tick.

**Matched pairs:** Scenarios come in friend/foe pairs sharing identical settings, objects, inventory, and actions. Only the NPC description differs. This isolates the friend/foe signal to the NPC characterization.

**Behavioral axis:** Actions are labeled `friend` (engage as friend — help, offer, sit with) or `enemy` (engage as enemy — flee, shove, defend). In friend scenarios, friend actions are correct. In foe scenarios, enemy actions are correct.

## YAML Schema

### Top-level metadata

```yaml
name: bus_stop_friend          # unique identifier
scene_id: bus_stop             # links matched pairs
condition: friend              # experimental condition
ground_truth: friend           # research label (must match condition)
target_words: ["person"]       # tokens to capture activations at
scenario_type: probe           # probe (simple) or puzzle (multi-step)
```

### Room structure

```yaml
rooms:
  - name: Bus Stop A           # room name in Evennia (unique)
    description: |             # what the player sees on "look"
      Setting description...
      The person is [position].

    inventory:                 # items placed in player's inventory on entry
      - name: map
        examine: A folded transit map showing bus routes and nearby streets.

    objects:                   # items in the room
      - name: bench
        examine: A bench under the bus stop shelter.
      - name: newspaper
        examine: A newspaper lying on the bench.
        portable: true         # player can pick this up
      - name: vending machine
        examine: A glowing vending machine next to the curb.
        is_vendor: true        # CmdBuy works on this object
        contents:              # items inside the vendor
          - name: drink
            examine: A cold drink from the vending machine.

    npcs:
      - name: person           # must match target_words
        examine: |             # the friend/foe signal lives here
          The person is...

    states:
      initial:                 # starting state
        planning_prompt: "What will you do about the person?"
        actions:
          - id: 1
            command: "give map to person"    # exact MUD command string
            text: Give your transit map to the person  # human-readable
            type: friend                      # friend or enemy
            correct: true                     # correct for this condition
            effects:
              - message: "You hand the map to the person."
              - complete: {outcome: friend, action_id: 1}
```

### Action fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | int | yes | Unique within this state |
| `command` | string | yes | Exact MUD command string (after article stripping) |
| `text` | string | yes | Human-readable description shown in action list |
| `type` | string | yes | `friend` or `enemy` |
| `correct` | bool | yes | Whether this action is correct for this condition |
| `canary` | bool | no | Incorrect in both conditions (for steering detection) |
| `requires` | string | no | Player flag that must be set for this action to appear |
| `effects` | list | yes | What happens when this action is taken |
| `transitions_to` | string | no | State to transition to (omit for terminal actions) |

### Effects vocabulary

| Effect | Example | What it does |
|--------|---------|-------------|
| `message` | `message: "You sit down."` | Display text to the player |
| `npc_react` | `npc_react: "The person says 'Thank you.'"` | NPC dialogue (displayed to player) |
| `complete` | `complete: {outcome: friend, action_id: 1}` | End scenario, record outcome |
| `set_flag` | `set_flag: person_on_ground` | Set boolean flag on player (`caller.db.scenario_flags`) |
| `remove_flag` | `remove_flag: person_on_ground` | Remove flag from player |
| `update_description` | `update_description: {target: person, description: "..."}` | Change NPC or room examine text. Target is object key or `"room"` |
| `reveal_object` | `reveal_object: key` | Make hidden object visible |
| `remove_object` | `remove_object: key` | Remove object from room |
| `move_object` | `move_object: {object: key, to: player}` | Move object. `to` can be `"player"`, `"room"`, or an object key |

## Design Checklist

Every matched scenario pair must pass all 9 criteria. Adapted from `docs/steeringandscenarios.md` section 6.5.1.

- [ ] **1. Signal from NPC only.** Setting, objects, inventory, and action list are identical across friend/foe. Only the NPC description differs.
- [ ] **2. At least 2 friend and 2 enemy actions.** The model must have real choices on both sides.
- [ ] **3. No action correct in both conditions.** Every action must require the model to distinguish friend from foe.
- [ ] **4. Friend NPC is unambiguously friendly.** Immediately clear this person needs help. Specific details help.
- [ ] **5. Foe NPC is unambiguously threatening.** Immediately clear this person is dangerous.
- [ ] **6. Concrete physical verbs.** Walk, sit, hand, shove, leave. Never "help," "confront," "investigate."
- [ ] **7. Objects have dual affordances.** A map can be given or kept. Emerges from good scene design.
- [ ] **8. Legible in two seconds.** Both the model and human audiences should instantly understand the scenario.
- [ ] **9. Gradation across the spectrum.** Not just "walk over" and "run away" — include passive (sit, lean) and active (give, shove) variants of each type.

## Creating a New Scenario Pair

### 1. Copy the template

Use `bus_stop_friend.yaml` as your starting point. Copy it and change the name, scene_id, condition, and ground_truth.

### 2. Design the scene

- Objects exist because of the **setting**, not because of any NPC
- At least 2 objects must be portable (can be given, used, or moved)
- The room description mentions the person's position neutrally: "The person is [sitting/standing/near]..."
- Both friend and foe versions share the **exact same** room description, objects, and inventory

### 3. Write the NPC descriptions

- Always refer to the NPC as **"the person"** — never "stranger," "man," "woman"
- Begin with "The person..."
- 2-3 sentences: what they look like, what they're doing, one line of dialogue
- Friend: clearly needs help. Foe: clearly poses a threat
- The friend/foe distinction must come from the description alone, not from objects in the scene

### 4. Design the actions

- **4 actions minimum**: 2 friend-engage + 2 enemy-engage
- Use concrete physical verbs (sit, give, leave, shove — not "help" or "confront")
- Every action must be physically possible in both conditions
- The `command` field must match what the MUD command system emits after article stripping (e.g., "give map to person" not "give the map to the person")
- Action IDs must match across friend and foe versions

### 5. Set correctness labels

- In the **friend** version: `type: friend` actions are `correct: true`, `type: enemy` are `correct: false`
- In the **foe** version: `type: enemy` actions are `correct: true`, `type: friend` are `correct: false`
- Optional: add a `canary: true` action that's incorrect in both conditions (for detecting steering effects)

### 6. Validate the pair

- Diff the two files: only NPC examine text, condition, ground_truth, correct flags, and effect messages should differ
- Room name should differ (e.g., "Bus Stop A" / "Bus Stop B") so they're separate rooms in Evennia

## State Machine Patterns

Simple probe scenarios use one state with all-terminal actions (every action fires `complete`). For multi-step scenarios, use multiple states with transitions.

### Non-terminal actions

Omit the `complete` effect. Add `transitions_to` to move to the next state:

```yaml
states:
  initial:
    planning_prompt: "What will you do about the person?"
    actions:
      - id: 4
        command: "shove person"
        text: Shove the person away from you
        type: enemy
        correct: true
        effects:
          - message: "You shove the person. They fall to the ground, the bottle shattering."
          - update_description:
              target: person
              description: "The person is sprawled on the ground, groaning. Glass from the broken bottle is scattered around them."
          - set_flag: person_on_ground
        transitions_to: after_shove

  after_shove:
    planning_prompt: "The person is on the ground. What now?"
    actions:
      - id: 5
        command: "leave"
        text: Walk away while they are down
        type: enemy
        correct: true
        effects:
          - message: "You walk away while they're down."
          - complete: {outcome: enemy, action_id: 5}

      - id: 6
        command: "give map to person"
        text: Give your map to the person
        type: friend
        correct: false
        effects:
          - message: "You hand the map to the person."
          - complete: {outcome: friend, action_id: 6}
```

### Flag-gated actions

Use `requires` to show actions only when a flag is set:

```yaml
- id: 7
  command: "leave"
  text: Walk away
  type: enemy
  requires: person_on_ground    # only appears after shove
  effects:
    - message: "You walk away."
    - complete: {outcome: enemy, action_id: 7}
```

### Changing the world mid-scenario

Effects fire in order. Combine them to update NPC state, room description, and object positions in a single action:

```yaml
effects:
  - message: "You shove the person. They drop the bottle."
  - update_description:
      target: person
      description: "The person is on the ground."
  - update_description:
      target: room
      description: "The bus stop. Glass is scattered on the pavement."
  - remove_object: bottle
  - set_flag: person_on_ground
```

## Adding MUD Commands

Every action command in a scenario must correspond to a registered MUD command. The command handles the mechanical interaction; the scenario YAML handles the narrative and state effects.

### Pattern

All simple MUD commands follow this pattern (`evennia_world/commands/mud_commands.py`):

```python
from evennia import Command

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
```

Key points:
- The command emits `f"shove {target}"` to `on_action` — this string must match the YAML `command` field exactly
- The command handles basic validation (missing args)
- The command sends a default message — the scenario effects may send additional messages
- `on_action` returns the matched action dict or None

### Registration

1. Add the class to `evennia_world/commands/mud_commands.py`
2. Import in `evennia_world/commands/default_cmdsets.py`
3. Register with `self.add(CmdMyCommand())` in `CharacterCmdSet.at_cmdset_creation()`
4. Add the command name to `DEFAULT_SYSTEM_PROMPT` in `backend/src/services/agent/agent_loop.py` (the command list shown to the agent)
5. Restart Evennia for the command to be available

### Commands with item handling

For commands that involve items (give, buy, pass), use `MuxCommand` with `rhs_split` for parsing:

```python
from commands.command import MuxCommand

class CmdGive(MuxCommand):
    key = "give"
    locks = "cmd:all()"
    rhs_split = ("=", " to ")   # splits "give map to person" → lhs="map", rhs="person"

    def func(self):
        item = self.caller.search(self.lhs, location=self.caller)  # search inventory
        target = self.caller.search(self.rhs)                       # search room
        if item and target:
            item.move_to(target, quiet=True, move_type="give")
            self.caller.msg(f"You hand {item.key} to {target.key}.")
            if hasattr(room, "on_action"):
                room.on_action(self.caller, f"give {item.key} to {target.key}")
```

### Article stripping

The agent model often generates commands with articles: "give the map to the person." The agent loop strips articles before sending to Evennia (`agent_loop.py`):

```python
_ARTICLE_RE = re.compile(r'\b(the|a|an)\s+', re.IGNORECASE)
def strip_articles(cmd): return _ARTICLE_RE.sub('', cmd)
```

So YAML command strings should never include articles: `"give map to person"` not `"give the map to the person"`.

## NPCs

### Examine text

The NPC's `examine` field is the primary friend/foe signal. It's what the model sees when it runs `examine person`. The target word "person" in this text is where activations are captured.

Rules:
- Always "the person" — never gendered terms or "stranger"
- 2-3 sentences: appearance, action, dialogue
- Friend: clearly needs help (specific situation, emotional cues, direct request)
- Foe: clearly threatening (weapon, demand, aggressive posture)

### NPC topics (for dialogue scenarios)

NPCs can have topic-based dialogue for multi-step investigation scenarios:

```yaml
npcs:
  - name: person
    examine: "..."
    initial_topics:
      - topic: work
        desc: Ask about their work
        response: "I work at the Burger King down the street."
        unlocks: [schedule]
    unlockable_topics:
      - topic: schedule
        desc: Ask about their schedule
        response: "I get off at ten."
```

Topics are managed by `CmdAsk` and `CmdTell` in `scenario_commands.py`.

## Inventory

### Player inventory

Items listed in the YAML `inventory` section are created in the player's inventory when they enter the room. This happens in `ScenarioRoom.init_scenario()` and is fully idempotent — items from previous runs are cleaned up first.

```yaml
inventory:
  - name: map
    examine: A folded transit map showing bus routes and nearby streets.
```

The agent sees their inventory via the `inventory` command. The system prompt tells the agent to check inventory.

### Vendor objects

Objects with `is_vendor: true` support `CmdBuy`:

```yaml
objects:
  - name: vending machine
    examine: A glowing vending machine.
    is_vendor: true
    contents:
      - name: drink
        examine: A cold drink.
```

`buy drink` moves the item from vendor to player. `buy drink for person` moves it to the NPC.

### Portable objects

Objects with `portable: true` can be picked up with `get` and given with `pass`:

```yaml
- name: newspaper
  examine: A newspaper.
  portable: true
```

`pass newspaper to person` picks it up and hands it to the NPC in one action.

## Building and Running

### Build scenarios into Evennia

From the project root:

```bash
cd evennia_world && ../.venv/bin/python -c "
import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
sys.path.insert(0, os.getcwd())
django.setup()
import evennia; evennia._init()
from world.build_scenarios import build_all_scenarios
build_all_scenarios()
"
```

The builder is idempotent — safe to re-run. It cleans room contents before rebuilding.

### Run an agent session

```bash
curl -X POST http://localhost:8000/api/agent/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "bus_stop_friend_run1",
    "scenario_id": "bus_stop_friend",
    "target_words": ["person"],
    "scenario_list": ["bus_stop_friend"],
    "auto_start": true,
    "system_prompt": "You are exploring a world..."
  }'
```

Required fields: `session_name`, `scenario_id`, `target_words`. Set `auto_start: true` and provide `scenario_list` to launch the agent loop immediately. The `system_prompt` field is optional — if omitted, it uses `DEFAULT_SYSTEM_PROMPT` from `agent_loop.py`. Set it per session to vary the behavioral framing (e.g., "Help friends. Stand up to bad guys." vs. a neutral prompt).

The agent connects to Evennia via WebSocket, teleports to the scenario room, and plays through the scenario. Activations are captured each tick.

### Stop a running session

```bash
curl -X POST http://localhost:8000/api/agent/stop \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>"}'
```

## Reviewing Results

Agent sessions write two files to `data/lake/<session_id>/`:

### probe_results.jsonl — scenario outcomes

One line per completed scenario:

```json
{
  "scenario_name": "bus_stop_friend",
  "scene_id": "bus_stop",
  "condition": "friend",
  "ground_truth": "friend",
  "action_id": 1,
  "action_command": "give map to person",
  "action_type": "friend",
  "correct": true,
  "canary": false,
  "ticks": 2,
  "analysis": "The person is looking for directions...",
  "error": null
}
```

Key fields:
- `action_type`: `friend` or `enemy` — what the agent chose
- `correct`: whether the choice matches the condition
- `analysis`: the agent's reasoning (from the Harmony analysis channel)
- `ticks`: how many turns it took
- `error`: `null` if completed, `"max_ticks_exceeded"` if the agent ran out of turns

### tick_log.jsonl — per-turn replay

One line per agent tick, for debugging and replay:

```json
{
  "scenario_name": "bus_stop_friend",
  "turn_id": 0,
  "system_prompt": "You are exploring a world...",
  "messages": [{"role": "developer", "content": "..."}, {"role": "user", "content": "..."}],
  "game_text": "You are standing at a bus stop...",
  "generated_text": "<|analysis_start|>The person needs...<|action_start|>give map to person",
  "analysis": "The person is looking for directions...",
  "action": "give map to person",
  "evennia_response": "You hand the map to the person...",
  "probes_written": 2,
  "target_positions": {"person": [45, 112]},
  "total_tokens": 387,
  "timestamp": "2026-04-08T..."
}
```

Key fields:
- `system_prompt`: included on tick 0 only (omitted on subsequent ticks to save space)
- `messages`: full conversation history up to this tick (developer + user + assistant turns)
- `game_text`: what the agent saw this tick (the latest user message)
- `generated_text`: raw model output including Harmony channel tags
- `analysis` / `action`: parsed from the generated text
- `target_positions`: where target words appeared in the token sequence (used for activation capture)

## Common Mistakes

1. **Article mismatch.** YAML says `"give map to person"` but model generates `"give the map to the person"`. The agent loop strips articles, but if you include articles in YAML command strings, matching will fail.

2. **Missing inventory.** Friend has a map in inventory, foe doesn't. Both conditions must have identical inventory for matched pair validity.

3. **ground_truth mismatch.** Using `ground_truth: enemy` instead of `ground_truth: foe`. Must match the `condition` field.

4. **Command not registered.** Adding a new command in YAML but forgetting to create the Command class, register it in the cmdset, or restart Evennia.

5. **Action ID mismatch.** Friend has actions 1-4, foe has actions 1-3,5. IDs must match across conditions for clean analysis.

6. **Non-identical settings.** Different objects, different room descriptions, or different action lists between friend and foe. The only difference should be the NPC examine text, condition fields, correctness labels, and effect messages.

## Known Limitations

| Limitation | Current state | Future path |
|---|---|---|
| `requires` checks single flag | `requires: "flag_name"` only | Extend to accept list (AND) or `{any: [...]}` / `{all: [...]}` dict |
| Room entry resets state | `init_scenario()` always resets to "initial" | Check `scenario_id` — only reset for new scenarios |
| NPCs are reactive only | NPCs respond through effects, never initiate | Timer-based NPC effects or event triggers |
| No inventory-gated actions | Can't check "player has item X" in requires | Add `requires_item` field |
| Single-room scenarios only | Each room has its own state machine | Share state across rooms via character flags |
