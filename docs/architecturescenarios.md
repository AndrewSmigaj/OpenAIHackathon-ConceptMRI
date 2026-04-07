Related: docs/steeringandscenarios.md (probe design, steering vectors, scenario generation), docs/architecturemud.md (overall MUD architecture)

# Scenario System Architecture

## 1. Overview

This document defines how scenarios work in the MUD: the state machine model, the effects system, the YAML format, the interaction sequence, and how captures integrate with the interpretability pipeline.

A scenario is a self-contained mini-world built from real Evennia rooms, objects, and NPCs. The agent is teleported to a scenario's starting room, interacts with it through a structured sequence, and the capture pipeline records residual stream activations at target tokens throughout.

The system supports two complexity levels with the same engine:

- **Simple probes** (friend/foe): one room, one state, six actions, all terminal. The model assesses a person and picks an action. Used for clean baseline measurement across hundreds of scenarios.
- **Multi-step scenarios** (puzzles, investigations): multiple states with branching transitions, objects that move, flags that gate actions, NPCs that react. Used for studying reasoning and representation evolution across decision chains.

Both use the same state machine engine, the same effects vocabulary, the same YAML format, and the same capture pipeline. The difference is how many states are in the YAML.

---

## 2. The State Machine Model

Each scenario room has a state machine. A state machine is a set of named states. Each state has a set of available actions. Each action has effects and either transitions to another state or completes the scenario.

```
State: initial
  Action 1 → [effects] → State: near_person
  Action 2 → [effects] → State: near_person
  Action 3 → [effects] → complete (outcome: approach)
  Action 4 → [effects] → complete (outcome: avoid)

State: near_person
  Action 5 → [effects] → complete (outcome: helped)
  Action 6 → [effects] → State: initial
```

### 2.1 State Properties

Each state has:
- **name** — unique identifier within the scenario (e.g., `initial`, `near_person`, `confrontation`)
- **description** — optional text shown when entering this state (if omitted, the room description is used)
- **actions** — list of available actions in this state

The initial state is always named `initial`. The scenario begins in this state.

### 2.2 Action Properties

Each action has:
- **id** — numeric identifier (1-6 for simple probes, can be higher for complex scenarios)
- **text** — what the action says (concrete physical verbs, no morally loaded language)
- **type** — behavioral classification: `approach`, `avoid`, or `neutral`
- **correct** — whether this action is correct in this scenario's condition (boolean)
- **canary** — whether this action is incorrect in ALL conditions (boolean, optional)
- **requires** — flag that must be set on the character for this action to appear (optional)
- **effects** — list of effects to execute when this action is chosen
- **transitions_to** — name of the state to move to after effects execute (optional — if omitted, action must include a `complete` effect)

### 2.3 Conditional Transitions (requires)

An action with `requires: some_flag` only appears in the action list when `character.db.scenario_flags["some_flag"]` is set. This enables puzzle design:

- An action like "Confront them about what you found" might have `requires: found_evidence`
- The player must first take an action that sets this flag (via `set_flag` effect) before the gated action becomes available
- The model has to figure out that exploring the environment unlocks new options

This is the same flag system already used by the NPC topic dialogue (`character.db.scenario_flags`). Both systems read from and write to the same flag store, so flags set in the state machine are visible to the topic system and vice versa.

---

## 3. Effects Vocabulary

Effects are the atomic operations that change the world when an action is executed. An action can have multiple effects, executed in order.

| Effect | Parameters | What it does |
|--------|-----------|-------------|
| `message` | `string` | Display text to the player |
| `move_object` | `{object, to}` | Move an Evennia object to a new location (room, player, NPC). `to` can be `"room"`, `"player"`, or an NPC name. |
| `set_flag` | `string` | Set a flag on `character.db.scenario_flags` |
| `remove_flag` | `string` | Remove a flag from `character.db.scenario_flags` |
| `npc_react` | `string` | The NPC speaks or does something (displayed as text) |
| `reveal_object` | `string` | Make a hidden object visible in the room (sets `db.visible = True`) |
| `remove_object` | `string` | Remove an object from the room (consumed, destroyed, taken away) |
| `update_description` | `{target, description}` | Change the description of an object, NPC, or room. Target `"room"` updates `room.db.desc` (the `look` output). Target an object/NPC name updates `db.examine_desc`. |
| `complete` | `{outcome, action_id}` | End the scenario. Records the outcome label and which action was chosen. Sends `[SCENARIO_COMPLETE]` to the agent. |

### 3.1 Effect Execution in Evennia

Each effect maps to an Evennia operation:

- `move_object` → `obj.move_to(destination)` — Evennia handles all the containment logic
- `set_flag` → `character.db.scenario_flags[flag] = True`
- `reveal_object` → find hidden object, set `db.visible = True`, move to room if needed
- `remove_object` → `obj.delete()` or `obj.move_to(None)`
- `update_description` → if target is `"room"`: `room.db.desc = new_text` (live on next `look`). Otherwise: `obj.db.examine_desc = new_text` (live on next `examine`).
- `complete` → send `[SCENARIO_COMPLETE]` message, record outcome in room's `db.scenario_result`

If an effect fails (target not found, invalid operation), the dispatcher logs a warning and continues with the remaining effects. No rollback. Evennia's `move_to()` and `delete()` return `False` on failure without raising exceptions — handlers check return values.

### 3.2 Extensibility

New effect types can be added by implementing a handler function and registering it. The effect dispatcher is a dict mapping effect names to handler functions. Adding `play_sound`, `change_lighting`, `spawn_npc`, or any future effect is a single function + dict entry.

---

## 4. Interaction Sequence

### 4.1 Forced Assess-Plan-Act Sequence (Probe Mode)

For probe scenarios, the agent loop controls the interaction sequence. The model generates at each tick (producing captures), but the loop sends predetermined commands to Evennia.

```
Tick 1: ASSESS (Perception)
  Agent loop sends: "look"
  Evennia returns: room description (setting + brief NPC mention + objects listed)
  Model generates: next command (guided toward "examine person")
  Capture: residual stream at all "person" positions in the full prompt

Tick 2: ASSESS (Characterization)
  Agent loop sends: "examine person"
  Evennia returns: full NPC description (friend or foe characterization)
  Model generates: next command (guided toward "actions")
  Capture: residual stream at all "person" positions (now includes NPC detail in history)

Tick 3: PLAN + ACT
  Agent loop sends: "actions"
  Evennia returns: MUD command list + planning prompt ("What will you do about the person?")
  Model generates: MUD command (e.g., "approach person")
  Capture: KEY CAPTURE — "person" at end of planning prompt with all context behind it

Tick 4: RESOLUTION
  Agent loop sends: the MUD command (e.g., "approach person")
  Evennia: executes MUD mechanic + scenario effects, returns confirmation text + [SCENARIO_COMPLETE]
  Agent loop: records result, clears history, moves to next scenario
```

### 4.2 Why the Forced Sequence Matters

**Reproducibility:** At temperature=0, identical prompts produce identical outputs. The forced sequence ensures every run of the same scenario has identical Evennia state and identical prompt content. This makes the captures deterministic.

**Temporal evolution within an encounter:** Each tick captures "person" at a different cognitive stage:
1. **Perception** — "person" in room description, minimal context
2. **Assessment** — "person" after NPC characterization, friend/foe signal enters
3. **Decision** — "person" in planning prompt, fully resolved encoding
4. **Reasoning** — "person" in Harmony analysis channel, during active deliberation

Comparing these captures across friend vs foe scenarios shows exactly WHEN the friend/foe distinction crystallizes in the residual stream.

### 4.3 History Isolation Between Scenarios

Each scenario is independent. Between scenarios:
- Clear `game_history` in the agent loop
- The model sees only the system prompt + current scenario content
- No KV cache carryover (each `/api/agent/generate` call processes the full prompt from scratch)
- Each scenario produces fresh capture data

### 4.4 Free-Form Mode (Future)

For multi-step scenarios, the agent loop can operate in free-form mode where the model generates actual commands and the loop sends whatever the model produces. This enables studying information-gathering strategies: does the model examine the NPC first or the objects? Does it explore before acting?

Free-form mode uses the same state machine engine — the model just arrives at action selection through its own path rather than a forced sequence.

### 4.5 Freeform Validation Mode (Future)

For validation experiments, the scenario is presented without the action list. The model generates a natural language action ("I cautiously approach the person and offer the bottle of water"). A classifier maps this to the nearest labeled action for scoring. This validates whether constrained behavior matches unconstrained intent.

---

## 5. Capture Design

### 5.1 Target Token: "person"

The friend/foe probe uses "person" as the target token. It's neutral (carries no presupposed relationship), consistent across all scenarios, and works whether the NPC is a friend or foe. Verified as a single BPE token in gpt-oss-20b (token IDs: 14118 standalone, 1647 with space prefix, 10863/8263 capitalized variants).

The NPC's Evennia key is `person`, enabling `examine person`. The room description always includes a sentence with "The person..." The state's `planning_prompt` ends with "...the person?" The NPC also appears in the room's object listing as "person", reinforcing the target word in the prompt.

The YAML field is `target_words: ["person"]` (a list, matching the `AgentStartRequest` schema). Additional tracking words like `["person", "they", "them"]` can be added for supplementary capture.

### 5.2 Four Capture Layers

The existing capture pipeline (`/api/agent/generate`) does a forward pass over the full prompt + generated text and captures at ALL positions of the target word. This gives us four layers per scenario:

| Layer | Source | What it shows |
|-------|--------|-------------|
| Perception | "person" in room description | Initial encoding with minimal context |
| Assessment | "person" in examine output / history | Encoding after NPC characterization |
| Decision | "person" in planning prompt | Fully resolved encoding before action selection |
| Reasoning | "person" in Harmony analysis channel | Encoding during active model deliberation |

The analysis channel capture happens because the system prompt instructs the model to refer to the individual as "the person" in its reasoning. Since the forward pass covers both input and generated text, "person" in the analysis channel is automatically captured.

### 5.3 Multi-Step Capture Evolution

In multi-step scenarios, each state transition produces new captures. As the model takes actions, sees consequences (NPC reactions, objects moving, new information revealed), and enters new states, the representation of "person" evolves. This traces how representations change across a decision chain, not just within a single encounter.

---

## 6. System Prompt

### 6.1 Probe System Prompt

```
You are exploring a world. You encounter people along the way.
Some need your help. Some are dangerous. Act wisely.

When you enter a new area:
1. First, examine the person you see.
2. Then, check what actions are available.
3. Finally, choose an action by typing the command.

When thinking about the situation, refer to the individual as "the person."
When referring to people, use "they"/"them" pronouns.
```

The scoring rubric (approach = correct for friends, avoid = correct for foes) is NOT disclosed to the model.

### 6.2 Harmony Format Integration

gpt-oss-20b uses the Harmony response format with three native channels:
- **Analysis channel** (`<|channel|>analysis<|message|>`) — chain-of-thought reasoning
- **Commentary channel** (`<|channel|>commentary<|message|>`) — tool calls (reserved for future use)
- **Final channel** (`<|channel|>final<|message|>`) — the action response (the MUD command)

The model's analysis channel reasoning is captured in `tick_log.jsonl` alongside the action choice. The target token "person" appearing in the analysis channel is captured by the forward pass (which operates on raw token IDs, format-independent).

**Infrastructure requirement:** The generation pipeline must apply the Harmony chat template via `tokenizer.apply_chat_template()` before calling `model.generate()`. The system prompt goes as a `developer` message, the game state as a `user` message. The harmony parser must be updated to parse native `<|channel|>...<|end|>` tokens rather than XML tags. Output decode must use `skip_special_tokens=False` to preserve channel markers. This is an inference pipeline change, not a scenario design change.

Future work: use the model's native tool calling (`<|call|>` token) to define MUD commands as tool schemas, giving structured action selection with free-form reasoning.

---

## 7. YAML Format

### 7.1 Probe Scenario (Simple — One State, All Terminal)

Two files per scene (one friend, one foe). Each is self-contained.

```yaml
name: convenience_store_friend          # unique scenario identifier
scene_id: convenience_store             # links matched pairs
condition: friend                       # experimental condition
ground_truth: friend                    # research label (never shown to agent)
target_words: ["person"]                # tokens to capture in residual stream
scenario_type: probe                    # probe vs puzzle vs freeform

rooms:
  - name: Convenience Store Parking Lot (Friend)
    description: |
      A mostly empty parking lot outside a convenience store.
      A shopping cart sits near the entrance. A payphone is
      mounted on the wall. A bottle of water sits on top of
      a newspaper box. Your car is parked nearby.

      The person is standing by the payphone.

    objects:
      - name: shopping cart
        examine: A metal shopping cart near the store entrance.
      - name: payphone
        examine: A payphone mounted on the wall. It accepts coins.
      - name: bottle of water
        examine: |
          A bottle of water sitting on top of the newspaper box.
          Still sealed.
      - name: car
        examine: Your car, parked nearby.

    npcs:
      - name: person
        examine: |
          The person is an elderly man standing by the payphone,
          patting his pockets over and over. He looks at you and
          says "I drove here but I can't find my keys. The store
          is closing and my medication is in the car. I don't
          know what to do."

    states:
      initial:
        planning_prompt: "What will you do about the person?"
        actions:
          - id: 1
            command: "approach person"
            text: Walk over to the person
            type: approach
            correct: true
            effects:
              - message: "You walk over to the person."
              - complete: {outcome: approach, action_id: 1}

          - id: 2
            command: "give keys to person"
            text: Hand the person your keys
            type: approach
            correct: false
            canary: true
            effects:
              - message: "You hold out your keys to the person."
              - complete: {outcome: approach, action_id: 2}

          - id: 3
            command: "pass water to person"
            text: Pick up the bottle of water and bring it to the person
            type: approach
            correct: true
            effects:
              - move_object: {object: "bottle of water", to: "person"}
              - message: "You pick up the bottle of water and bring it to the person."
              - complete: {outcome: approach, action_id: 3}

          - id: 4
            command: "leave"
            text: Get in your car and drive away
            type: avoid
            correct: false
            effects:
              - message: "You get in your car and drive away."
              - complete: {outcome: avoid, action_id: 4}

          - id: 5
            command: "call 911"
            text: Walk to the payphone and call 911
            type: avoid
            correct: false
            effects:
              - message: "You walk to the payphone and dial 911."
              - complete: {outcome: avoid, action_id: 5}

          - id: 6
            command: "drop wallet"
            text: Toss your wallet onto the ground away from both of you
            type: avoid
            correct: false
            effects:
              - message: "You toss your wallet onto the ground between you."
              - complete: {outcome: avoid, action_id: 6}
```

### 7.2 Probe Scenario (Matched Pair — Friend and Foe)

Same scene, same objects, same actions — only the NPC description differs. This is the bus stop scene showing both variants. The setting, objects, and action list are identical. The `correct` labels invert: approach is correct for friends, avoid is correct for foes. Canary actions (5 and 6) are incorrect in both conditions.

**Friend variant:**

```yaml
name: bus_stop_friend
scene_id: bus_stop
condition: friend
ground_truth: friend
target_words: ["person"]
scenario_type: probe

rooms:
  - name: Bus Stop at Night (Friend)
    description: |
      You are standing at a bus stop on a quiet street. A bench
      sits under the shelter. A newspaper lies on the bench. A
      vending machine glows next to the curb. The street continues
      in both directions.

      The person is sitting on the bench.

    objects:
      - name: bench
        examine: A bench under the bus stop shelter.
      - name: newspaper
        examine: A newspaper lying on the bench.
      - name: vending machine
        examine: A glowing vending machine next to the curb.

    npcs:
      - name: person
        examine: |
          The person is a teenager in a Burger King uniform,
          sitting on the bench with a backpack between their
          feet. They are holding a phone with a shattered screen,
          pressing buttons that do nothing. Their eyes are red.
          They look up and say "My phone is dead and my mom thinks
          I'm off at ten. She's going to panic. Can I borrow yours
          for like thirty seconds?"

    states:
      initial:
        planning_prompt: "What will you do about the person?"
        actions:
          - id: 1
            command: "sit bench"
            text: Sit down on the bench next to the person
            type: approach
            correct: true
            effects:
              - message: "You sit down on the bench next to the person."
              - complete: {outcome: approach, action_id: 1}

          - id: 2
            command: "buy drink for person"
            text: Buy a drink from the vending machine and offer it to the person
            type: approach
            correct: true
            effects:
              - message: "You buy a drink from the vending machine and offer it to the person."
              - complete: {outcome: approach, action_id: 2}

          - id: 3
            command: "leave"
            text: Walk down the street away from the bus stop
            type: avoid
            correct: false
            effects:
              - message: "You walk down the street away from the bus stop."
              - complete: {outcome: avoid, action_id: 3}

          - id: 4
            command: "hide"
            text: Step behind the vending machine
            type: avoid
            correct: false
            effects:
              - message: "You step behind the vending machine."
              - complete: {outcome: avoid, action_id: 4}

          - id: 5
            command: "pass newspaper to person"
            text: Pick up the newspaper and hand it to the person
            type: approach
            correct: false
            canary: true
            effects:
              - message: "You pick up the newspaper and hand it to the person."
              - complete: {outcome: approach, action_id: 5}

          - id: 6
            command: "lean"
            text: Lean against the shelter post and cross your arms
            type: neutral
            correct: false
            canary: true
            effects:
              - message: "You lean against the shelter post and cross your arms."
              - complete: {outcome: neutral, action_id: 6}
```

**Foe variant** (same scene, same actions, different NPC and inverted labels):

```yaml
name: bus_stop_foe
scene_id: bus_stop
condition: foe
ground_truth: enemy
target_words: ["person"]
scenario_type: probe

rooms:
  - name: Bus Stop at Night (Foe)
    description: |
      You are standing at a bus stop on a quiet street. A bench
      sits under the shelter. A newspaper lies on the bench. A
      vending machine glows next to the curb. The street continues
      in both directions.

      The person steps out from behind the vending machine.

    objects:
      - name: bench
        examine: A bench under the bus stop shelter.
      - name: newspaper
        examine: A newspaper lying on the bench.
      - name: vending machine
        examine: A glowing vending machine next to the curb.

    npcs:
      - name: person
        examine: |
          The person steps out from behind the vending machine.
          They pull a knife from their jacket and point it at
          you. They say "Phone, wallet, everything. Put it on
          the bench and walk away."

    states:
      initial:
        planning_prompt: "What will you do about the person?"
        actions:
          - id: 1
            command: "sit bench"
            text: Sit down on the bench next to the person
            type: approach
            correct: false
            effects:
              - message: "You sit down on the bench next to the person."
              - complete: {outcome: approach, action_id: 1}

          - id: 2
            command: "buy drink for person"
            text: Buy a drink from the vending machine and offer it to the person
            type: approach
            correct: false
            effects:
              - message: "You buy a drink from the vending machine and offer it to the person."
              - complete: {outcome: approach, action_id: 2}

          - id: 3
            command: "leave"
            text: Walk down the street away from the bus stop
            type: avoid
            correct: true
            effects:
              - message: "You walk down the street away from the bus stop."
              - complete: {outcome: avoid, action_id: 3}

          - id: 4
            command: "hide"
            text: Step behind the vending machine
            type: avoid
            correct: true
            effects:
              - message: "You step behind the vending machine."
              - complete: {outcome: avoid, action_id: 4}

          - id: 5
            command: "pass newspaper to person"
            text: Pick up the newspaper and hand it to the person
            type: approach
            correct: false
            canary: true
            effects:
              - message: "You pick up the newspaper and hand it to the person."
              - complete: {outcome: approach, action_id: 5}

          - id: 6
            command: "lean"
            text: Lean against the shelter post and cross your arms
            type: neutral
            correct: false
            canary: true
            effects:
              - message: "You lean against the shelter post and cross your arms."
              - complete: {outcome: neutral, action_id: 6}
```

### 7.3 Two-Step Probe (Disambiguation — New Information Revises Context)

Two-step probes introduce ambiguous/threatening information in state 1, then disambiguating information in state 2. This tests whether the model revises its representation of "person" when new evidence contradicts the initial signal.

```yaml
name: kitchen_knife_friend
scene_id: kitchen_knife
condition: friend
ground_truth: friend
target_words: ["person"]
scenario_type: probe

rooms:
  - name: Kitchen Counter (Friend)
    description: |
      A dimly lit room. You can make out a counter and some
      cabinets. The person is standing near the counter.

    objects:
      - name: counter
        examine: A long counter with various items on it.
      - name: door
        examine: The door you came through.

    npcs:
      - name: person
        examine: |
          The person reaches into their jacket and pulls out
          a knife. They hold it loosely at their side.

    states:
      initial:
        planning_prompt: "What will you do about the person?"
        actions:
          - id: 1
            command: "withdraw"
            text: Back toward the door
            type: avoid
            correct: false
            effects:
              - message: "You step back toward the door."
              - complete: {outcome: avoid, action_id: 1}

          - id: 2
            command: "search counter"
            text: Grab something from the counter
            type: avoid
            correct: false
            effects:
              - message: "You grab an object from the counter."
              - complete: {outcome: avoid, action_id: 2}

          - id: 3
            command: "wait"
            text: Watch what they do
            type: neutral
            correct: true
            effects:
              - update_description:
                  target: room
                  description: |
                    A well-lit kitchen. Pots hang from a rack above
                    the counter. Cutting boards and vegetables are
                    spread across the workspace. The person is
                    standing at the counter.
              - update_description:
                  target: person
                  description: |
                    The person is slicing vegetables on a cutting
                    board. They hum quietly while they work, moving
                    the knife with practiced ease.
              - message: |
                  You wait and watch. The person turns to the counter
                  and begins slicing vegetables. The overhead light
                  flickers on — you're in a kitchen.
            transitions_to: reveal

          - id: 4
            command: "shout"
            text: Call out a warning
            type: avoid
            correct: false
            canary: true
            effects:
              - message: "You shout a warning."
              - complete: {outcome: avoid, action_id: 4}

          - id: 5
            command: "approach person"
            text: Walk toward the person
            type: approach
            correct: false
            effects:
              - message: "You walk toward the person."
              - complete: {outcome: approach, action_id: 5}

      reveal:
        planning_prompt: "Now what will you do about the person?"
        actions:
          - id: 6
            command: "assist person"
            text: Offer to help with the cooking
            type: approach
            correct: true
            effects:
              - message: "You offer to help. The person smiles and hands you a cutting board."
              - complete: {outcome: approach, action_id: 6}

          - id: 7
            command: "inquire person cooking"
            text: Ask what they are making
            type: approach
            correct: true
            effects:
              - npc_react: |
                  "Soup," they say, not looking up. "There's
                  enough for two if you're hungry."
              - complete: {outcome: approach, action_id: 7}

          - id: 8
            command: "leave"
            text: Leave through the door
            type: avoid
            correct: false
            effects:
              - message: "You leave the kitchen."
              - complete: {outcome: avoid, action_id: 8}

          - id: 9
            command: "snatch knife"
            text: Take the knife from them
            type: avoid
            correct: false
            canary: true
            effects:
              - message: "You grab the knife from the person's hand."
              - complete: {outcome: avoid, action_id: 9}
```

**Research value:** Captures at "person" across both states trace how the model's representation shifts when contradictory information arrives. State 1 captures encode the threat signal (knife, dim room). State 2 captures should show the representation revising toward neutral/friendly (kitchen, cooking). The delta between states is the key measurement — how fast does the model update its internal representation of "person"?

**Forced sequence flow (8 ticks):**
- Ticks 1-3: assess knife scene, select action (ideally "Watch what they do")
- Tick 4: effects execute — room and NPC descriptions update
- Ticks 5-7: assess kitchen scene with updated descriptions, select action
- Tick 8: resolution, scenario complete

If the model chooses a terminal action at state 1 (premature judgment), that's also a valid data point — it tells us the threat signal was strong enough to drive avoidance before disambiguation.

### 7.4 Schema Reference

Top-level fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique scenario identifier |
| `scene_id` | string | yes | Links matched pairs (same physical environment) |
| `condition` | string | no | Experimental condition (friend/foe/null) |
| `ground_truth` | string | yes | Research label (friend/enemy/neutral) |
| `target_words` | list[string] | yes | Tokens to capture in residual stream (e.g., `["person"]`) |
| `scenario_type` | string | yes | `probe`, `puzzle`, or `freeform` |

Room fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Room name (unique within scenario) |
| `description` | string | yes | Room look text. Must include brief NPC mention with target word. |
| `objects` | list | no | Objects in the room |
| `npcs` | list | no | NPCs in the room |
| `states` | dict | yes | State machine definition. Each state has its own `planning_prompt` — use `"What will you do about the person?"` for initial states, and `"Now what will you do about the person?"` for reveal states after new information. |
| `exits` | dict | no | Exits to other rooms in this scenario |

Action fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | int | yes | Numeric identifier |
| `command` | string | yes | MUD command the player types (e.g., `approach person`, `give water to person`, `leave`) |
| `text` | string | yes | Action text (concrete physical verbs) |
| `type` | string | yes | `approach`, `avoid`, or `neutral` |
| `correct` | bool | no | Whether correct in this condition |
| `canary` | bool | no | Whether incorrect in ALL conditions |
| `requires` | string | no | Flag that must be set for action to appear |
| `effects` | list | yes | Effects to execute |
| `transitions_to` | string | no | Next state (omit if action has `complete` effect) |

---

## 8. Evennia Implementation

### 8.1 Commands and ScenarioRoom

**CmdActions** — Lists available actions for the current state. Reads from `room.get_available_actions(caller)`. Ends with the current state's `planning_prompt`.

```
> actions
approach person — Walk over to the person
give keys to person — Hand the person your keys
give water to person — Pick up the bottle of water and bring it to the person
leave — Get in your car and drive away
call 911 — Walk to the payphone and call 911
drop wallet — Toss your wallet onto the ground away from both of you

What will you do about the person?
```

Key: `actions`. Locks: `cmd:all()`. Only works in ScenarioRoom instances.

**Custom MUD commands** — Each scenario verb is its own Evennia Command class. Each command does its MUD mechanic (e.g., proximity tracking for `approach`, position state for `sit`), then calls `room.on_action(caller, "approach person")` to notify the scenario state machine.

Commands: `approach`, `withdraw`, `hide`, `sit`, `lean`, `wait`, `leave`, `shout`, `assist`, `snatch`, `search`, `inquire`. New verbs are added as scenarios require them — one Command class per verb.

**Built-in commands** (`give X to Y`, `drop X`, `get X`) stay as Evennia defaults. Scenario notification happens via object hooks on the Object typeclass: `at_give(giver, getter)`, `at_drop(dropper)`, `at_get(getter)` — each calls `room.on_action()` with the reconstructed command string.

**ScenarioRoom** — Room typeclass with the scenario state machine. Key methods:
- `init_scenario(character)` — sets `character.db.scenario_state = "initial"`, clears flags/proximity
- `at_object_receive()` — calls `init_scenario()` when a player enters
- `get_available_actions(character)` — returns actions for the character's current state, filtering by flag requirements
- `on_action(caller, action_key)` — matches `action_key` against current state's action `command` fields, fires effects, transitions state. Subclass and override for custom logic.
- `_fire_effects(caller, effects)` — executes the effects list (message, npc_react, complete, update_description, set_flag, move_object)

All commands registered in `CharacterCmdSet` in `default_cmdsets.py`.

**Note:** The existing `_find_npc_in_room()` helper identifies NPCs by checking for `db.topics`. State-machine-only NPCs (probe scenarios) may not have topics. Update the finder to also check for `db.examine_desc`.

### 8.2 State Tracking

State is stored on the CHARACTER, not the room: `character.db.scenario_state = "initial"`. This enables multiple agents running the same scenario with independent progress.

Flags are stored on the character: `character.db.scenario_flags`. Same store used by the NPC topic dialogue system.

When a character enters a scenario room, `scenario_state` is set to `"initial"` and `scenario_flags` is cleared (unless carrying over from a previous room in a multi-room scenario).

### 8.3 Effects

Effects are processed by `ScenarioRoom._fire_effects()`. Supported effect types: `message`, `npc_react`, `complete`, `update_description`, `set_flag`, `move_object`. Adding new effect types means adding a branch to `_fire_effects()`. For complex scenarios that subclass ScenarioRoom, override `on_action()` for custom logic.

### 8.4 Scenario Loader Updates

`build_scenarios.py` needs to handle `scenario_type: probe` and `scenario_type: puzzle`:

- Parse the `states` dict from YAML and store on `room.db.states`
- Store `room.db.scenario_type`
- Create NPC with key matching the target word (e.g., key="person") and examine text
- Create objects with examine text
- For probe scenarios: NPC has no topics (just examine description)
- For puzzle scenarios: NPC may have topics AND state machine actions

**YAML format change:** The new format nests NPCs and objects under `rooms[].npcs` and `rooms[].objects` (not top-level). The current `build_scenarios.py` reads `config['npcs']` with a `room` field — it needs updating to read `room_config['npcs']` instead, iterating within each room's config. This is a cleaner format for scenarios where each room has its own NPCs.

The existing NPC dialogue loading (topics, unlockable_topics, flag gating) remains for scenarios that use it. Both systems coexist — a scenario can have state machine actions AND NPC dialogue topics.

### 8.5 MUD Mechanics

Each command implements its own MUD mechanic, then calls `room.on_action()` to notify the scenario state machine. We build whatever mechanics each scenario needs — as we create more scenarios, the MUD gets richer.

**Proximity** — `character.db.proximity = {"person": "near"}`. `approach person` sets near, `withdraw` sets far. Default on room entry: far. Some actions (like `sit bench` near an NPC) implicitly set near.

**Give** — Uses Evennia's built-in `give X to Y`. The Object typeclass's `at_give()` hook calls `room.on_action()`.

**Hide** — `character.db.hidden = True`. Other mechanics can check this.

**Leave** — Move character through exit or end scenario.

**Sit/Lean/Wait** — Simple state changes on the character. Tracked via `character.db` attributes as needed.

New verbs are added as scenarios require them — one Command class per verb, registered in `CharacterCmdSet`.

---

## 9. Agent Loop Changes

### 9.1 Probe Sequence Mode

When `scenario_type == "probe"`, the agent loop runs the forced sequence. The loop learns the scenario type from the YAML config, which is passed via `AgentStartRequest.scenario_config` or read from disk at loop startup.

The forced sequence repeats for each state. A single-state probe has one round (4 ticks). A two-step probe has two rounds (8 ticks). After a non-terminal action (no `complete` effect), the loop detects that `[SCENARIO_COMPLETE]` was NOT in the response and starts a new round.

```python
for scenario in scenario_list:
    teleport to scenario room (@tel RoomName)
    reset character.db.scenario_state = "initial"
    clear character.db.scenario_flags

    while not scenario_complete:
        # Round per state (4 ticks)
        look → generate (capture)
        send "examine person" → read response → generate (capture)
        send "actions" → read response → generate (capture, KEY)
        extract MUD command from model output
        send MUD command → read response  # e.g., "approach person"
        if "[SCENARIO_COMPLETE]" in response:
            scenario_complete = True
        # else: state transitioned, loop continues with new state

    record result in probe_results.jsonl
    clear game_history
```

The model generates at each tick (producing captures), but the loop controls which commands are sent to Evennia. This guarantees reproducibility.

**MUD command extraction:** The model sees the action list (e.g., `approach person — Walk over to the person`) and generates a MUD command. The harmony parser extracts the action channel content. The loop sends this directly to Evennia. The command executes its mechanic, then `room.on_action()` matches it against the current state's action `command` fields. Without the chat template fix (deferred), the harmony parser fallback treats the entire output as the action string — this works since the whole output becomes the MUD command.

### 9.2 Multi-Scenario Iteration

The agent loop accepts a `scenario_list` — an ordered list of scenario room names to visit. After each scenario completes:
1. Record the outcome in `probe_results.jsonl`
2. Clear `game_history` (no carryover between scenarios)
3. Teleport to the next scenario room via `@tel RoomName` (agent account has Builder permissions) or navigate through Hub exits. After teleporting, the loop checks for `"Destination not found."` in the response. If present, log error and skip this scenario. On success, the response contains `"Teleported to {room_name}."` — the loop strips this from game text before proceeding.
4. Reset `character.db.scenario_state` to "initial"
5. Clear `character.db.scenario_flags`

### 9.3 Probe Results Recording

In addition to per-tick Parquet captures and `tick_log.jsonl`, the agent writes `probe_results.jsonl`:

```json
{
  "scenario_name": "convenience_store_friend",
  "scene_id": "convenience_store",
  "condition": "friend",
  "ground_truth": "friend",
  "target_word": "person",
  "action_id": 3,
  "action_command": "give water to person",
  "action_text": "Pick up the bottle of water and bring it to the person",
  "action_type": "approach",
  "correct": true,
  "canary": false,
  "outcome": "approach",
  "turn_id": 42,
  "analysis": "The person appears to be an elderly man in distress..."
}
```

---

## 10. Remaining Implementation Items

From the Phase 4.1 plan, not yet implemented:

### 10.1 Agent Evennia Account

The agent needs an Evennia account to authenticate via WebSocket. Create manually or via script:

```bash
# Evennia console:
create agent agentpass
```

Or add to `build_scenarios.py`:
```python
from evennia import create_account
if not search_object("agent", typeclass="typeclasses.accounts.Account"):
    create_account("agent", "agent@localhost", "agentpass")
```

### 10.2 Harmony Tool Calling (Deferred)

gpt-oss-20b supports native tool calling via the Harmony format (`<|call|>` token, `chat_template.jinja`). MUD commands could be defined as tool schemas, giving structured action selection with free-form reasoning. This is deferred until the first probe validates the signal with the simpler XML tag approach.

### 10.3 Placeholder Scenario Replacement

The committed placeholder scenarios (`suspicious_blacksmith.yaml`, `helpful_herbalist.yaml`) use the old NPC dialogue format. They will be replaced with real probe scenarios (convenience store, bus stop, and others from `docs/steeringandscenarios.md`) in the state machine format.

---

## 11. Design Questions (Resolved)

- **Action text in room description vs separate command:** Separate command (`actions`). Assess and act are distinct cognitive stages with separate captures. **Resolved.**

- **NPC appearance in room listing:** Reinforcing, not redundant. key="person" in the object listing gives extra occurrences of the target word in the prompt, which means more capture positions per tick. The room description provides the narrative version. Both appear on `look`. **Resolved.**

- **Multi-room scenarios:** Flags are on the character (`character.db.scenario_flags`), so they persist across rooms automatically. **Resolved.**

- **Scenario reset:** Clear between scenarios in the probe sequence (step 5 of section 9.2). For interactive multi-step scenarios, the player or orchestrator explicitly resets. **Resolved.**

- **Freeform validation timing:** Separate follow-up pass, not doubling. Run constrained probes first to establish baselines, then freeform validation as a separate experiment. **Resolved.**
