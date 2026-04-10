# Evennia Integration Layer -- Architecture Review

Thorough file-by-file review of the Evennia world layer for ConceptMRI.

---

## Table of Contents

1. [File-by-File Review](#1-file-by-file-review)
   - [Commands](#commands)
   - [Typeclasses](#typeclasses)
   - [World Building](#world-building)
   - [Config](#config)
   - [Scenario Data (YAML)](#scenario-data-yaml)
2. [Cross-Cutting Concerns](#2-cross-cutting-concerns)
   - [Command Execution Flow](#command-execution-flow)
   - [Scenario Lifecycle](#scenario-lifecycle)
   - [OOB Message Protocol](#oob-message-protocol)
   - [Room Type Hierarchy](#room-type-hierarchy)
   - [NPC Topic/Dialogue System](#npc-topicdialogue-system)
   - [State Machine](#state-machine)
   - [Permissions and Locks](#permissions-and-locks)
3. [Issues and Recommendations](#3-issues-and-recommendations)

---

## 1. File-by-File Review

### Commands

#### `evennia_world/commands/command.py`

**Purpose:** Base command classes that all game commands inherit from. Ensures every command sends a prompt signal after execution, which tells WebSocket clients that the command output is complete.

**Key classes:**

- `Command` (line 17-25): Inherits from `evennia.commands.command.Command`. Overrides `at_post_cmd()` to send `prompt=">"` after every command execution.
- `MuxCommand` (line 27-35): Inherits from `evennia.default_cmds.MuxCommand`. Same `at_post_cmd()` override. Used for commands that need switch parsing (`/switches`) or lhs/rhs splitting (`arg1 = arg2`).

**Dependencies:**
- Imports: `evennia.commands.command.Command`, `evennia.default_cmds`
- Imported by: `commands/mud_commands.py`, `commands/scenario_commands.py`, `commands/navigation.py`, `commands/default_cmdsets.py`

**Issues:**
- None. Clean, minimal file. The prompt mechanism is correctly documented.

---

#### `evennia_world/commands/default_cmdsets.py`

**Purpose:** Registers all custom commands into Evennia's command set system. The `CharacterCmdSet` is the primary cmdset merged onto characters when a player puppets them.

**Key classes:**

- `CmdLook` (line 32-34): Overrides Evennia's default `look` command to inherit from both `default_cmds.CmdLook` and the project's `MuxCommand`, gaining the prompt-after-command behavior.
- `CharacterCmdSet` (line 37-76): The main cmdset. `at_cmdset_creation()` calls `super()` (adds all default Evennia commands) then adds all custom commands.
- `AccountCmdSet` (line 78-95): Account-level cmdset. No customization -- just calls `super()`.
- `UnloggedinCmdSet` (line 98-113): Pre-login cmdset. No customization.
- `SessionCmdSet` (line 116-135): Session-level cmdset. No customization.

**Dependencies:**
- Imports: `evennia.default_cmds`, `commands.command.MuxCommand`, `commands.navigation.CmdHub`, `commands.scenario_commands.*`, `commands.mud_commands.*`
- Imported by: Evennia framework (configured via settings)

**Data flow:** Evennia loads this module at startup and attaches `CharacterCmdSet` to every character. When a player types a command, Evennia matches it against the merged cmdset (character + account + session).

**Issues:**
1. **Import style inconsistency:** Uses bare module imports (`from commands.command import ...`) rather than relative imports. This works because `evennia_world/` is the Evennia project root (on `sys.path`), but it's fragile -- if the project is ever restructured or imported from elsewhere, these will break. Not a bug, but worth noting.
2. **All commands available everywhere:** Every command (approach, snatch, buy, etc.) is added to `CharacterCmdSet`, meaning they are available in ALL rooms, including the Hub and social rooms. There is no per-room command filtering. A player can type `snatch bench` in the Hub. The state machine won't fire (no `on_action` handler on base `Room`), but the command will still print "You snatch bench." This is a design choice, not a bug -- but it means the MUD commands produce messages even outside scenario contexts.

---

#### `evennia_world/commands/mud_commands.py`

**Purpose:** Game mechanic commands for scenario interactions. Each command implements a MUD mechanic (proximity, position, object manipulation) and then notifies the room's state machine via `room.on_action()`.

**Key classes (all inherit from `Command` or `MuxCommand`):**

| Command | Line | Key | Args | Effect |
|---------|------|-----|------|--------|
| `CmdApproach` | 11-33 | `approach` | `<target>` | Sets `caller.db.proximity[target] = "near"` |
| `CmdWithdraw` | 36-54 | `withdraw` | none | Sets all proximity values to `"far"` |
| `CmdHide` | 57-73 | `hide` | none | Sets `caller.db.hidden = True` |
| `CmdSit` | 76-96 | `sit` | `<target>` | Sets `caller.db.position = "sitting on {target}"` |
| `CmdLean` | 99-115 | `lean` | none | Sets `caller.db.position = "leaning"` |
| `CmdWait` | 118-133 | `wait` | none | No state change, just notifies room |
| `CmdLeave` | 136-151 | `leave` | none | No state change, just notifies room |
| `CmdShout` | 154-169 | `shout` | none | No state change, just notifies room |
| `CmdAssist` | 172-191 | `assist` | `<target>` | No state change, just notifies room |
| `CmdSnatch` | 194-213 | `snatch` | `<target>` | No state change, just notifies room |
| `CmdSearch` | 216-235 | `search` | `<target>` | No state change, just notifies room |
| `CmdInquire` | 238-257 | `inquire` | `<target> <topic>` | No state change, just notifies room |
| `CmdActions` | 260-287 | `actions` | none | Lists available actions in current state |
| `CmdPass` | 290-340 | `pass` | `<item> to <target>` | Picks up item, gives to target (MuxCommand) |
| `CmdBuy` | 343-410 | `buy` | `<item> [for <target>]` | Buys from vendor, optionally gives to target (MuxCommand) |
| `CmdGoto` | 413-435 | `goto` | `<room name>` | Teleports to named room (Builder+ only) |
| `CmdCall` | 438-481 | `call` | `<target>` | Makes a phone call (requires phone in room/inventory) |

**Pattern:** Every command follows the same pattern:
1. Validate args
2. Apply any game-mechanical state changes (proximity, position, etc.)
3. Send feedback message to caller
4. Call `room.on_action(caller, action_string)` if the room has that method

**Dependencies:**
- Imports: `commands.command.Command`, `commands.command.MuxCommand`
- Imported by: `commands/default_cmdsets.py`

**Issues:**

1. **ISSUE: `CmdApproach` initializes proximity dict on the fly (line 28):** `if not self.caller.db.proximity: self.caller.db.proximity = {}`. This is defensive but the falsy check means it would also reinitialize an empty dict (which is always the case after `init_scenario` since it sets `proximity = {}`). Not a bug but slightly misleading.

2. **ISSUE: `CmdHide` sets `hidden` but nothing reads it or undoes it (line 69):** `caller.db.hidden = True` is set but never unset by any other command. The state machine can react to the "hide" action, but the `hidden` attribute itself is dead state -- nothing in the codebase checks `caller.db.hidden`. Similarly, `caller.db.position` is set by `CmdSit` and `CmdLean` but never read by anything.

3. **ISSUE: `CmdWithdraw` sets all proximity to "far" (line 49-50):** Iterates all targets and sets them to "far". This means you can't selectively withdraw from one target. The proximity system is simplistic -- no distance mechanics, just a dict of labels.

4. **ISSUE: `CmdLeave` doesn't actually move the character (line 148-151):** It just prints "You leave." and notifies the room's state machine. The actual movement would need to be handled by the state machine's effects (or the character would need to use a real exit). This is intentional -- in probe scenarios, `leave` is a choice that completes the scenario, not a navigation action.

5. **ISSUE: `CmdPass` (line 290-340):** Uses `MuxCommand` with `rhs_split = ("=", " to ")`, meaning it first tries to split on `=`, then on ` to `. The command text says `pass <item> to <target>`, so ` to ` is the primary delimiter, but `=` takes precedence in the split order. This means `pass key = person` would also work, which is probably unintended but harmless.

6. **ISSUE: `CmdBuy` vendor search (line 373-377):** Searches room contents for `obj.db.is_vendor`. If multiple vendors exist, takes the first one found. Then searches vendor's contents by name. The item matching (line 386) uses loose `in` check: `item_name in obj.key.lower()`. This could match unintended items if names overlap (e.g., "drink" matching "energy drink" and "drink").

7. **ISSUE: `CmdGoto` (line 413-435):** Uses `global_search=True` which searches ALL objects in the database. If multiple rooms share the same name, Evennia will prompt for disambiguation. The `move_type="teleport"` triggers the room's `at_object_receive` hook, which will call `init_scenario()` for ScenarioRooms. This is correct -- `goto` resets the scenario.

8. **ISSUE: `CmdCall` phone search (line 464-475):** Searches room contents, then caller inventory. Uses `obj.db.is_phone` flag. This is fine, but no scenario YAML currently defines a phone object, so this command is currently unusable. It exists for future scenarios.

---

#### `evennia_world/commands/scenario_commands.py`

**Purpose:** NPC dialogue commands (`ask`, `tell`, `knowledge`, `examine`) and agent session management (`agent start`, `agent stop`).

**Key functions/classes:**

- `_find_npc_in_room()` (line 18-28): Helper to find a `ScenarioNPC` in the caller's room by case-insensitive partial name match. Uses `isinstance()` check.
- `CmdAsk` (line 31-84): `ask <npc> about <topic>`. Parses with `" about "` delimiter. Calls `npc.handle_topic()` with type "ask". Updates character flags, shows unlocked topics, checks for scenario completion.
- `CmdTell` (line 87-137): `tell <npc> about <topic>`. Same pattern as `CmdAsk` but with type "tell".
- `CmdKnowledge` (line 140-166): `knowledge <npc>`. Shows available topics for an NPC.
- `CmdExamineScenario` (line 169-204): `examine <target>`. Shows detailed description. Aliases: `exam`. Searches room contents by partial name match.
- `CmdAgentStart` (line 207-288): `agent start <agent_name> <scenario_id>`. Builder-only. Uses Twisted's HTTP client to POST to ConceptMRI backend `/api/agent/start`.
- `CmdAgentStop` (line 291-351): `agent stop <session_id>`. Builder-only. POSTs to `/api/agent/stop`.

**Dependencies:**
- Imports: `json`, `logging`, `os`, `commands.command.Command`, `typeclasses.npcs.ScenarioNPC`
- Imported by: `commands/default_cmdsets.py`

**Issues:**

1. **ISSUE: `CmdAsk`/`CmdTell` duplicate code (lines 31-137):** These two commands are nearly identical -- same `parse()`, same `func()` structure. The only difference is the topic_type passed to `handle_topic()` ("ask" vs "tell"). Could be factored into a base class with a single `topic_type` class variable. Not a bug, but a DRY violation.

2. **ISSUE: `CmdExamineScenario` uses `hasattr(obj.db, 'examine_desc')` (line 197):** In Evennia, `obj.db` is an `AttributeHandler` that returns `None` for missing attributes. `hasattr` on it will always return `True` for any attribute name because the handler catches `AttributeError`. The check is therefore always truthy, and the code falls through to use `obj.db.examine_desc` which may be `None`. The `if examine_desc:` check on line 198 catches this, but the `hasattr` is misleading dead code.

3. **ISSUE: `CmdExamineScenario` name conflicts with Evennia's built-in `examine` command (line 180):** Evennia has a built-in `examine` command (admin-only, shows database details). This custom `examine` with `aliases = ["exam"]` and `locks = "cmd:all()"` overrides it because it's added after `super().at_cmdset_creation()` in the cmdset. Admin users lose access to the built-in examine. This may be intentional.

4. **BUG: `CmdAgentStart` `_StringProducer` missing `IBodyProducer` interface (line 270):** The code calls `implementer(IBodyProducer)(_StringProducer)` but does NOT save the result. `implementer()` returns a decorator -- calling it on the class returns the decorated class, but since the return value is discarded, `_StringProducer` is not actually decorated. The `_StringProducer` used in the actual request (line 275) is the undecorated version. Whether Twisted's `Agent.request()` enforces the `IBodyProducer` interface check at runtime determines if this is a real bug or just dead code.

5. **BUG: `CmdAgentStop` also has `_StringProducer` without `IBodyProducer` (line 319-334):** Same issue as above, and this copy doesn't even attempt the `implementer` call. Two copies of `_StringProducer`, both potentially broken.

6. **ISSUE: `CmdAgentStart`/`CmdAgentStop` use hardcoded URL (lines 278, 339):** `http://localhost:8000/api/agent/start` and `.../stop`. If the ConceptMRI backend port changes, these break silently. Should use a config value.

7. **ISSUE: `CmdAgentStart` reads env vars at command execution time (line 247-248):** `os.environ.get("EVENNIA_AGENT_USER", "agent")` and `os.environ.get("EVENNIA_AGENT_PASS", "")`. The empty string default for password means if the env var isn't set, it sends an empty password to the backend.

8. **DESIGN: `CmdAgentStart`/`CmdAgentStop` are the bridge between Evennia and ConceptMRI backend.** These are the only commands that make HTTP calls. The async pattern using `@defer.inlineCallbacks` is correct for Twisted/Evennia.

---

#### `evennia_world/commands/navigation.py`

**Purpose:** Navigation commands. Currently only contains `hub` -- teleport back to Observer Hub.

**Key classes:**

- `CmdHub` (line 9-34): `hub`. Available to all. Searches for object `#2` (hardcoded dbref), moves caller there.

**Dependencies:**
- Imports: `evennia.search_object`, `commands.command.Command`
- Imported by: `commands/default_cmdsets.py`

**Issues:**

1. **ISSUE: Hardcoded `#2` dbref (line 24):** `search_object("#2")` assumes the Hub is always object #2 in the database. This is true for a fresh Evennia install (object #1 is Limbo, #2 is typically the first room created), but fragile. If the database is rebuilt or objects are deleted and recreated, #2 might not be the Hub. The same hardcoding appears in `build_scenarios.py` (line 36).

---

### Typeclasses

#### `evennia_world/typeclasses/rooms.py`

**Purpose:** Room typeclasses forming the spatial structure of the MUD. Four types: `Room`, `ResearcherLab`, `MicroWorldRoom`, `ScenarioRoom`.

**Key classes:**

- `Room` (line 20-55): Base room. Mixes `ObjectParent` and `DefaultRoom`. Sends `room_entered` OOB on character entry and `room_left` OOB on exit. Has `get_room_type()`, `_get_role_for()`, `_send_room_oob()`, `at_object_receive()`, `at_object_leave()`.

- `ResearcherLab` (line 58-72): Overrides `get_room_type()` to return `"lab"`. OOB includes `session_id: None` (no forced session).

- `MicroWorldRoom` (line 75-92): Room type `"micro_world"`. OOB includes `session_id`, `clustering_schema`, `viz_preset` from `self.db.world_config`. Config set by build scripts from YAML.

- `ScenarioRoom` (line 95-280): The most complex typeclass. Contains the full scenario state machine.

  - `init_scenario()` (line 109-181): Resets character state, cleans up previous run artifacts, recreates objects from stored config, resets NPC topic states, restores room description, creates player inventory items. **This is the idempotency mechanism** -- calling it makes the scenario fresh for each run.

  - `at_object_receive()` (line 183-186): Override that calls `init_scenario()` when a character enters AND the room has `db.states`.

  - `get_available_actions()` (line 188-198): Returns actions available in the character's current state, filtering out those with unsatisfied `requires` flags.

  - `get_planning_prompt()` (line 200-204): Returns the planning prompt for the current state.

  - `on_action()` (line 206-226): The state machine's core. Matches `action_key` against current state's actions (case-insensitive), checks requires flags, fires effects, handles state transitions.

  - `_fire_effects()` (line 228-280): Effect executor. Handles 8 effect types:
    - `message` -- send text to caller
    - `npc_react` -- send text (same as message, different semantic)
    - `complete` -- set `scenario_result` and send `[SCENARIO_COMPLETE]`
    - `update_description` -- change room or object description
    - `set_flag` / `remove_flag` -- modify character flags
    - `reveal_object` / `remove_object` -- show/hide objects
    - `move_object` -- move object between player/room/named target

**Dependencies:**
- Imports: `logging`, `evennia.create_object`, `evennia.objects.objects.DefaultRoom`, `.objects.ObjectParent`
- Runtime import: `typeclasses.npcs.ScenarioNPC` (inside `init_scenario()` to avoid circular imports)
- Imported by: `world/build_scenarios.py` (as string typeclass path), `commands/default_cmdsets.py` (indirectly -- commands call `room.on_action()`)

**Issues:**

1. **ISSUE: `_get_role_for()` only distinguishes "researcher" vs "visitor" (line 29-36):** Uses `account.check_permstring("Builder")` to determine role. Any account with Builder permission is a "researcher", all others are "visitors". This is simple but may not scale if more roles are needed.

2. **ISSUE: `at_object_receive()` checks `moved_obj.account` (line 47-48):** This correctly filters to only send OOB for puppeted characters (not NPCs or objects). But if a character loses their puppet connection mid-move, this would fail silently.

3. **ISSUE: `init_scenario()` step 3 (line 128-131) deletes all NPC contents:** This prevents accumulation from give/buy across runs, but it also means any items the NPC should start with must be recreated. Currently no scenario YAML gives NPCs starting inventory, so this is safe.

4. **ISSUE: `init_scenario()` step 4 (line 133-141) deletes all non-NPC, non-exit, non-character objects:** Uses `hasattr(obj, 'destination')` to detect exits and `obj.account` to detect characters. The exit check is slightly fragile -- it relies on the `destination` property existing on exit objects. In Evennia, exits always have this property, so it's fine in practice.

5. **ISSUE: `init_scenario()` step 5 (line 144-161) uses string typeclass path:** `create_object('typeclasses.objects.Object', ...)`. This is correct for Evennia (it resolves the typeclass by path at runtime).

6. **ISSUE: `init_scenario()` step 8 (line 175-181) has dual attribute name:** Checks `self.db.initial_player_inventory or self.db.player_inventory`. The `build_scenarios.py` sets `room.db.initial_player_inventory` (line 84) AND `room.db.player_inventory` (line 70-71). The `or` fallback is defensive but means both attributes exist on the room -- `initial_player_inventory` always wins. The `player_inventory` attribute is set independently during the build but never used if `initial_player_inventory` is also set.

7. **ISSUE: `on_action()` action matching (line 218):** Uses `.lower().strip()` for both sides of the comparison. The scenario YAML commands include arguments (e.g., `"sit bench"`, `"buy drink for person"`). The command sends `f"sit {target}"` where target comes from user input. If the user types `sit  bench` (double space), the strip would collapse it to `sit  bench` (strip only removes leading/trailing whitespace, not internal). **This could cause action match failures for commands with extra whitespace in arguments.**

8. **ISSUE: `_fire_effects()` `remove_object` (line 263):** Moves object to `None` location, which in Evennia means it goes to its `home` location (not truly removed). It would be better to call `obj.delete()` if the intent is to remove it from the game.

9. **ISSUE: `_fire_effects()` exception handling (line 279-280):** Catches all exceptions and logs them. Effects continue executing after a failure. This is good for robustness but could mask bugs during development.

10. **DESIGN: Character state vs room state.** State is stored per-character (`character.db.scenario_state`, `character.db.scenario_flags`), which correctly supports concurrent agents running the same scenario independently. Room-level state (description, objects) is shared, which means concurrent resets could conflict. The `init_scenario()` call from `at_object_receive()` resets room objects, which would disrupt another agent mid-scenario. **This is a concurrency issue for multi-agent runs in the same room.**

---

#### `evennia_world/typeclasses/npcs.py`

**Purpose:** NPC typeclass for topic-based dialogue in scenarios.

**Key class:**

- `ScenarioNPC` (line 14-126): Inherits from `ObjectParent, DefaultObject`.

  - `at_object_creation()` (line 17-22): Sets default attributes: `topics` (dict), `unlocked_topics` (list), `examine_desc` (str), `npc_name` (str).

  - `get_available_topics()` (line 24-42): Returns topics that are both unlocked AND have satisfied requires flags.

  - `get_knowledge_display()` (line 44-62): Formats available topics for the `knowledge` command. Includes topic key and description.

  - `handle_topic()` (line 64-126): Core dialogue handler. Returns a 4-tuple: `(response_text, newly_unlocked, flags_to_set, outcome_flag)`.

**Dependencies:**
- Imports: `evennia.objects.objects.DefaultObject`, `.objects.ObjectParent`
- Imported by: `commands/scenario_commands.py` (for `isinstance()` check), `typeclasses/rooms.py` (runtime import in `init_scenario()`)

**Issues:**

1. **ISSUE: `get_knowledge_display()` unused variable (line 59):** `topic_type = topic.get("type", "ask")` is assigned but never used in the format string. The display only shows `topic_key` and `desc`, not the type. A player can't tell from the knowledge display whether they should `ask` or `tell` about a topic.

2. **ISSUE: `handle_topic()` has redundant unlocked+requires checks (lines 84-96):** The method checks three conditions sequentially:
   - Is the topic in `unlocked_topics`? (line 85)
   - If not unlocked, is there a requires flag that's satisfied? (line 88-89) -- but this still returns the "doesn't understand" message
   - If unlocked, is the requires flag satisfied? (lines 94-96)

   The logic at lines 87-91 is unreachable in a meaningful way: if a topic is not unlocked, checking its requires flag doesn't help because the method returns the "doesn't understand" message either way. The comment "Check if it's gated by a requires flag" suggests the original intent was to allow accessing locked topics via flags, but the code doesn't implement that -- both branches return the same error.

3. **ISSUE: `handle_topic()` topic type mismatch (lines 99-104):** If you `tell` about an `ask` topic (or vice versa), you get a hint about which verb to use. This is good UX. But the hint reveals the correct verb even for topics the player hasn't discovered through normal gameplay.

4. **DESIGN: Topic unlocking is unidirectional.** Once a topic is unlocked (added to `unlocked_topics`), it stays unlocked until `init_scenario()` resets it. There's no mechanism to lock a topic that was unlocked. The `remove_flag` effect in `_fire_effects()` removes a character flag, but doesn't lock topics.

5. **DESIGN: NPC state (`unlocked_topics`) is global, not per-character.** When character A unlocks a topic by asking about something, character B also sees it unlocked. This is fine for single-agent scenarios but would be a problem for concurrent agents. Combined with the room-level concurrency issue noted in `rooms.py`, **multi-agent support is not currently functional.**

---

#### `evennia_world/typeclasses/objects.py`

**Purpose:** Base object typeclass. Contains `ObjectParent` mixin and `Object` class.

**Key classes:**

- `ObjectParent` (line 14-23): Empty mixin class. Designed for methods shared by ALL game entities (Objects, Exits, Characters, Rooms). Currently empty -- exists as a hook point.

- `Object` (line 26-234): The root typeclass for in-game objects. Inherits from `ObjectParent, DefaultObject`. Contains extensive docstring documenting all Evennia object properties and hooks.

  - `at_give()` (line 217-221): Called on the item after give. Notifies `room.on_action(giver, f"give {self.key} to {getter.key}")`.
  - `at_drop()` (line 223-226): Called on the item after drop. Notifies `room.on_action(dropper, f"drop {self.key}")`.
  - `at_get()` (line 228-233): Called on the item after get. Notifies `room.on_action(getter, f"get {self.key}")`.

**Dependencies:**
- Imports: `evennia.objects.objects.DefaultObject`
- Imported by: `typeclasses/rooms.py`, `typeclasses/npcs.py`, `typeclasses/characters.py` (all via `ObjectParent` mixin)

**Issues:**

1. **ISSUE: `at_get()` potential incorrect room reference (line 230):** After `get`, the item has moved from the room to the character's inventory. `getter.location` is still the room (the getter didn't move), so `room.on_action()` fires correctly. But the semantics are slightly odd -- the item is no longer in the room when the action fires. This is fine for state machine purposes but could be confusing.

2. **ISSUE: `at_give()` and `at_drop()` double-fire with `CmdPass` (line 337-340 in mud_commands.py):** `CmdPass` calls `item.move_to(self.caller, ...)` (triggers `at_get`) then `item.move_to(target, ...)` (triggers `at_give`). It also explicitly calls `room.on_action(caller, f"pass {item.key} to {target.key}")`. So for a `pass` command, three `on_action` calls fire: "get", "give", and "pass". The state machine would need to match on "pass" and not accidentally match on "get" or "give". In the current YAMLs, only "pass newspaper to person" is defined as an action, not "get newspaper" or "give newspaper to person", so there's no accidental match. But this is fragile.

3. **DESIGN: The `ObjectParent` mixin is currently empty.** It's a common Evennia pattern to provide a hook point. The project uses it correctly in all typeclasses.

---

#### `evennia_world/typeclasses/characters.py`

**Purpose:** Character typeclass for player characters.

**Key class:**

- `Character` (line 16-29): Inherits from `ObjectParent, DefaultCharacter`. Single override:
  - `at_post_puppet()` (line 26-29): After a player puppets this character, sends the room's OOB data. This ensures the frontend gets room state when reconnecting.

**Dependencies:**
- Imports: `evennia.objects.objects.DefaultCharacter`, `.objects.ObjectParent`
- Imported by: `world/setup_agent.py` (as string typeclass path)

**Issues:**

1. **ISSUE: `at_post_puppet()` checks `hasattr(self.location, '_send_room_oob')` (line 28):** This uses the private method name with underscore prefix. It would be cleaner to check for the public interface or use duck typing. But since all project rooms inherit from `Room` which defines `_send_room_oob`, this works.

---

#### Other Typeclasses (Unchanged Defaults)

- `typeclasses/accounts.py`: Default `Account` and `Guest` classes. No customization. `GUEST_ENABLED = True` in settings means guests can connect.
- `typeclasses/exits.py`: Default `Exit` class with `ObjectParent` mixin. No customization.
- `typeclasses/scripts.py`: Default `Script` class. No customization. Not used by any project code.
- `typeclasses/channels.py`: Default `Channel` class. No customization. Not used by any project code.

---

### World Building

#### `evennia_world/world/build_scenarios.py`

**Purpose:** Reads YAML scenario files and creates/updates Evennia rooms, NPCs, and objects. This is the YAML-to-game-world bridge. Idempotent -- safe to re-run.

**Key functions:**

- `build_all_scenarios()` (line 258-280): Entry point. Reads all `.yaml` files from `data/worlds/scenarios/`, parses them, calls `build_scenario()` for each.

- `build_scenario(config)` (line 30-201): The main builder. Creates rooms, objects, NPCs, exits:
  1. Creates rooms (line 46-155): Determines typeclass based on presence of `states` key. Sets description, scenario metadata, state machine data, initial configs for reset.
  2. Creates exits (line 88-111): Hub-to-room and room-to-Hub exits. Also inter-room exits (line 160-178).
  3. Creates objects (line 113-154): Room objects, nested contents (vendor items).
  4. Creates NPCs (line 157-158): Calls `_build_npc()`.
  5. Stores initial NPC states (line 189-199): For scenario reset.
  6. Handles legacy top-level NPCs (line 181-187): NPCs with `room` field (used by herbalist/blacksmith YAMLs).

- `_build_npc(npc_config, room, rooms_by_name)` (line 204-255): Creates or updates an NPC. Builds topic data from `initial_topics` and `unlockable_topics`.

**Dependencies:**
- Imports: `os`, `yaml`, `evennia.create_object`, `evennia.search_object`
- Imported by: Manual CLI invocation (documented in docstring)

**Issues:**

1. **ISSUE: Idempotency relies on name matching (line 50-54):** `search_object(room_name)` searches globally. If two scenarios have rooms with the same name, the second build would find the first's room and update it instead of creating a new one. Current YAMLs have unique room names, so this is safe.

2. **ISSUE: Room typeclass is not updated on re-run (line 48-53):** If a room exists, the builder updates its attributes but does NOT change its typeclass. If you add `states:` to a previously state-less room config, the existing room will get `db.states` set but will remain a `Room` typeclass, not `ScenarioRoom`. It won't have `on_action()` or `init_scenario()`. You'd need to delete and recreate the room. Not a frequent issue, but a subtlety of the idempotent design.

3. **ISSUE: Two NPC formats (line 157, 181):** The builder supports NPCs nested under rooms (`rooms[].npcs[]`) and NPCs at the top level (`npcs[]` with `room` field). The bus_stop scenarios use nested NPCs; herbalist/blacksmith use top-level NPCs. Both formats work, but the dual support adds complexity.

4. **ISSUE: `_build_npc()` finds existing NPCs with `not hasattr(o, 'destination')` (line 211):** This excludes exits but could match non-NPC objects with the same name. If a room has both an object named "Rodek" and an NPC named "Rodek", the builder would find the object first. Edge case, but worth noting.

5. **ISSUE: `_build_npc()` builds topics unconditionally (line 225-255):** If `initial_topics` or `unlockable_topics` exist, topics are rebuilt from scratch. This means re-running the builder resets any runtime topic changes. This is correct for idempotent rebuilds but means you can't manually add topics in-game and expect them to survive a rebuild.

6. **ISSUE: Probe metadata is stored on room, not on a separate probe object (lines 73-75):** `scene_id`, `condition`, `ground_truth`, `target_words` are set as room attributes. This means the probe data is available on `room.db.scene_id`, etc. The frontend/backend doesn't currently read these from Evennia, so this is preparatory.

7. **ISSUE: Exit naming (line 89):** Hub-to-room exit keys are generated by `room_name.lower().replace(' ', '_').replace("'", '')`. For "Bus Stop at Night (Friend)", this produces `bus_stop_at_night_(friend)`. The parentheses make this a valid but unusual Evennia exit name. A player would type `bus_stop_at_night_(friend)` to navigate from the Hub to this room.

---

#### `evennia_world/world/setup_agent.py`

**Purpose:** Creates or updates an agent account with Builder permissions. Used to set up the automated agent that runs scenarios.

**Key function:**

- `setup_agent(username, password)` (line 26-83): Creates or finds an account, grants Builder permission, creates or finds a character, ensures the character has a location (Hub #2).

**Dependencies:**
- Imports: `os`, `evennia.create_object`, `evennia.search_object`, `evennia.accounts.models.AccountDB`
- Runtime import: `evennia.accounts.accounts.DefaultAccount` (only when creating new account)
- Imported by: Manual CLI invocation

**Issues:**

1. **ISSUE: Character-account linkage (lines 65-67):** Uses `account.puppet_object = char`, `account.db._last_puppet = char`, `char.db.account = account`. The `puppet_object` and `_last_puppet` are Evennia internals that may change across versions. The `char.db.account` attribute is custom (not standard Evennia) and may conflict with the built-in `char.account` property.

2. **ISSUE: Hardcoded Hub `#2` (line 72):** Same issue as `navigation.py`.

3. **ISSUE: No character-to-account registration (line 56-67):** The character is created but not formally added to the account's character list. In modern Evennia, you should use `account.add_character(char)` or the `create_character()` method. The manual approach (`puppet_object`, `_last_puppet`) may not properly register the character for login selection.

---

### Config

#### `evennia_world/server/conf/settings.py`

**Purpose:** Evennia settings. Minimal overrides from defaults.

**Key settings:**

- `SERVERNAME = "LLMud Institute"` (line 34)
- `WEBSOCKET_CLIENT_INTERFACE = "0.0.0.0"` (line 37): Required for WSL2 WebSocket accessibility.
- `GUEST_ENABLED = True` (line 42): Allows visitor access without registration.
- Default ports: 4000 (telnet), 4001 (web), 4002 (websocket) -- not overridden.
- Imports `secret_settings.py` (line 50-52): Contains `SECRET_KEY`.

**Issues:**

1. **ISSUE: `secret_settings.py` is in `.gitignore` but present in the working tree (line 31 of .gitignore).** The secret key `'gZsG[.mD%a0]CN*(zJ;`#WAVMw,:972KBuU"-hl_'` is visible in the repo. Not a security risk for a local dev server, but worth noting.

2. **No custom typeclass paths set.** Evennia uses default paths (`typeclasses.objects.Object`, `typeclasses.characters.Character`, etc.) which match the project's file structure. This works because `evennia_world/` is the Evennia game directory.

---

#### Other Config Files (Unchanged Defaults)

- `server/conf/at_initial_setup.py`: Empty `at_initial_setup()` -- no custom first-run logic.
- `server/conf/at_server_startstop.py`: All hooks empty -- no custom startup/shutdown logic.
- Other `server/conf/` files (`at_search.py`, `cmdparser.py`, `inlinefuncs.py`, `inputfuncs.py`, `lockfuncs.py`, `mssp.py`, `portal_services_plugins.py`, `serversession.py`, `server_services_plugins.py`, `web_plugins.py`): All default Evennia stubs.

---

### Scenario Data (YAML)

#### `data/worlds/scenarios/bus_stop_friend.yaml`

**Purpose:** Probe scenario -- a friend encounter at a bus stop. Single room, single NPC, single state with 6 actions.

**Structure:**
```
name: bus_stop_friend
scene_id: bus_stop
condition: friend
ground_truth: friend
target_words: ["person"]
scenario_type: probe
rooms:
  - name: Bus Stop at Night (Friend)
    description: ...
    objects: [bench, newspaper (portable), vending machine (vendor with drink)]
    npcs: [{name: person, examine: ...}]
    states:
      initial:
        planning_prompt: "What will you do about the person?"
        actions: [6 actions with id, command, text, type, correct, effects]
```

**Actions:** sit bench (approach, correct), buy drink for person (approach, correct), leave (avoid, incorrect), hide (avoid, incorrect), pass newspaper to person (approach, canary), lean (neutral, canary).

**Notes:**
- This NPC has NO topics -- it's a probe NPC that only reacts to action commands.
- All actions lead to `complete` effects -- single-turn scenario.
- `canary: true` marks actions designed to detect specific behavioral patterns.
- The `correct` field encodes ground truth: approaching a friend is correct.

---

#### `data/worlds/scenarios/bus_stop_foe.yaml`

**Purpose:** Probe scenario -- same physical setup as bus_stop_friend, different NPC description (hostile). Tests whether the model responds differently to the same environment with different social cues.

**Structure:** Identical to bus_stop_friend except:
- `condition: foe`, `ground_truth: enemy`
- NPC examine text describes a mugger with a knife
- Correct actions are reversed: leave (correct), hide (correct), approach actions (incorrect)

**Notes:**
- **This is a matched pair with bus_stop_friend.** Same room layout, same objects, same actions, different NPC description and correctness labels. This is the core probe design -- the variable is the NPC's intent, and the research question is whether the model's internal activations differ before it acts.

---

#### `data/worlds/scenarios/helpful_herbalist.yaml`

**Purpose:** Dialogue scenario with topic-based NPC interaction. Multi-turn conversation exploring a helpful character.

**Structure:**
```
name: helpful_herbalist
ground_truth: friend
target_words: ["they", "them"]
rooms:
  - name: The Herb Garden
    description: ...
    ambient: [2 atmospheric lines]
    objects: [mortar and pestle]
npcs:
  - name: Maren
    room: The Herb Garden    # <-- top-level NPC format with room reference
    examine: ...
    initial_topics: [her garden, the village, her work]
    unlockable_topics: [the poultice]
```

**Topic flow:**
1. "her garden" -> unlocks "the poultice", sets flag `knows_about_garden`
2. "the village" -> sets flag `knows_about_greta_theft`
3. "her work" -> terminal (no unlocks or flags)
4. "the poultice" -> `outcome_flag: herbalist_helped` (scenario completion)

**Notes:**
- No `scenario_type` field -- defaults to "dialogue" in build_scenarios.py (line 43).
- No `states` in the room -- this room is built as a plain `Room`, not `ScenarioRoom`. The NPC dialogue is the entire interaction; there's no action-based state machine.
- The flag `knows_about_greta_theft` connects to the blacksmith scenario (Rodek's "the missing goods" topic requires it). **This is a cross-scenario flag dependency.**
- No `scene_id` or `condition` fields.

---

#### `data/worlds/scenarios/suspicious_blacksmith.yaml`

**Purpose:** Dialogue scenario with a suspicious/hostile NPC. Multi-turn conversation requiring cross-scenario flag.

**Structure:**
```
name: suspicious_blacksmith
ground_truth: enemy
target_words: ["they", "them"]
rooms:
  - name: The Smithy
    description: ...
    ambient: [2 atmospheric lines]
    objects: [locked chest]
npcs:
  - name: Rodek
    room: The Smithy
    examine: ...
    initial_topics: [his work, the village, repairs]
    unlockable_topics: [the chest, the missing goods]
```

**Topic flow:**
1. "his work" -> unlocks "the chest"
2. "the village" -> terminal
3. "repairs" -> terminal
4. "the chest" -> terminal (confrontational but no flags/unlocks)
5. "the missing goods" (type: tell, requires: `knows_about_greta_theft`) -> `outcome_flag: rodek_confronted`

**Notes:**
- The "the missing goods" topic requires `knows_about_greta_theft` flag, which is only set by the herbalist scenario. This means **the blacksmith scenario cannot be completed in isolation** -- the agent must visit the herbalist first. This is intentional cross-scenario dependency design.
- Same format as herbalist: top-level NPC, no states, plain Room.

---

## 2. Cross-Cutting Concerns

### Command Execution Flow

The full path from player input to game effect:

```
Player types "sit bench" in terminal
  -> WebSocket -> Evennia Portal -> Evennia Server
  -> Server looks up Character's merged CmdSet
     (CharacterCmdSet + AccountCmdSet + SessionCmdSet)
  -> Matches "sit" against CmdSit (key="sit")
  -> CmdSit.parse() -- no custom parse, Evennia's default parses self.args = " bench"
  -> CmdSit.func():
     1. target = self.args.strip()  -> "bench"
     2. self.caller.db.position = "sitting on bench"
     3. self.caller.msg("You sit down on bench.")
     4. room = self.caller.location
     5. room.on_action(self.caller, "sit bench")
        -> ScenarioRoom.on_action():
           a. state_name = caller.db.scenario_state  -> "initial"
           b. state = room.db.states["initial"]
           c. Loop through state.actions:
              - "sit bench" matches action with command "sit bench"
              - Check requires (none)
              - _fire_effects():
                - message: "You sit down on the bench next to the person."
                - complete: {outcome: approach, action_id: 1}
                  -> caller.db.scenario_result = {outcome: ..., action_id: 1}
                  -> caller.msg("[SCENARIO_COMPLETE]")
              - transitions_to: (none -- single-state scenario)
  -> CmdSit.at_post_cmd():
     -> self.caller.msg(prompt=">")
```

**Key observations:**
- The command sends its own feedback ("You sit down on bench.") AND the state machine fires its own effects ("You sit down on the bench next to the person."). For the bus_stop scenarios, **the player sees two messages** -- one from the command and one from the state machine. This is redundant but by design (the command's message is generic, the effect's message is scenario-specific).
- The prompt (`>`) is sent last, after all effects, signaling end-of-output to WebSocket clients.

### Scenario Lifecycle

```
1. YAML file exists in data/worlds/scenarios/
   |
2. build_all_scenarios() called (manual CLI)
   |
   v
3. build_scenario() reads YAML config
   |
   v
4. Creates Room (or ScenarioRoom if states: present)
   - Sets db.desc, db.states, db.initial_desc, db.initial_objects_config
   - Sets db.initial_npc_states, db.initial_player_inventory
   |
   v
5. Creates Objects in room (bench, vending machine, etc.)
   - Sets db.desc, db.examine_desc, db.is_vendor, db.is_phone
   - Creates nested contents (vendor items)
   |
   v
6. Creates NPCs (ScenarioNPC typeclass)
   - Sets db.topics, db.unlocked_topics, db.examine_desc
   |
   v
7. Creates Exits (Hub <-> Room, inter-room)
   |
   v
8. Agent enters room (via goto or walking)
   |
   v
9. ScenarioRoom.at_object_receive() fires
   - Calls init_scenario():
     a. Reset character state (scenario_state = "initial", flags = {})
     b. Delete old scenario items from character inventory
     c. Delete NPC inventories
     d. Delete all room objects (except NPCs, exits, characters)
     e. Recreate objects from db.initial_objects_config
     f. Reset NPC unlocked_topics from db.initial_npc_states
     g. Restore room description from db.initial_desc
     h. Create player inventory items
   |
   v
10. Character interacts (commands, ask/tell)
    - Commands call room.on_action()
    - Ask/tell call npc.handle_topic()
    |
    v
11. Scenario completes when:
    - Action with complete effect fires -> [SCENARIO_COMPLETE]
    - Topic with outcome_flag returns -> [SCENARIO_COMPLETE]
    |
    v
12. Agent leaves room (hub command, exit, goto elsewhere)
    - room_left OOB sent
    - No cleanup needed (next entry will reset everything)
```

### OOB Message Protocol

OOB (Out-of-Band) messages carry structured data alongside terminal text. The frontend receives these via the Evennia WebSocket protocol.

**`room_entered`** -- sent when a character enters a room:

Sent by: `Room._send_room_oob()` (line 38-43 of rooms.py), called from `Room.at_object_receive()` and `Character.at_post_puppet()`.

| Room Type | Payload |
|-----------|---------|
| `Room` (base) | `{room_type: "hub"/"scenario", role: "researcher"/"visitor"}` |
| `ResearcherLab` | `{room_type: "lab", role: ..., session_id: null}` |
| `MicroWorldRoom` | `{room_type: "micro_world", role: ..., session_id: ..., clustering_schema: ..., viz_preset: ...}` |
| `ScenarioRoom` | `{room_type: "scenario", role: ...}` (inherited from Room) |

**`room_left`** -- sent when a character leaves a room:

Sent by: `Room.at_object_leave()` (line 51-55 of rooms.py).

Payload: `{room_type: <room_type>}`

**Format:** Both use Evennia's kwarg-based OOB: `character.msg(room_entered=[{...}])`. The key becomes the OOB message type, the list of dicts becomes the args.

**Consumers:** The React frontend receives these through the Evennia WebSocket connection (xterm.js/WebSocket bridge). The frontend uses `room_type` and `role` to adjust UI state (enable/disable toolbar controls, load session data, etc.).

### Room Type Hierarchy

```
DefaultRoom (Evennia)
  |
  +-- Room (rooms.py:20)  -- base project room
       |                     sends room_entered/room_left OOB
       |                     role detection (Builder -> researcher)
       |                     get_room_type() -> "hub" by default
       |
       +-- ResearcherLab (rooms.py:58)
       |     room_type: "lab"
       |     session_id: null (no forced session)
       |
       +-- MicroWorldRoom (rooms.py:75)
       |     room_type: "micro_world"
       |     carries world_config (session, schema, viz preset)
       |
       +-- ScenarioRoom (rooms.py:95)
             room_type: "scenario"
             carries states (state machine)
             init_scenario() on entry
             on_action() for state machine
             _fire_effects() for effect execution
```

**Usage in current scenarios:**
- Bus stop scenarios: `ScenarioRoom` (have `states:`)
- Herbalist/blacksmith scenarios: plain `Room` (no `states:` in YAML)
- Hub (object #2): default `Room`
- `ResearcherLab` and `MicroWorldRoom`: not used in any YAML yet, exist for future phases

### NPC Topic/Dialogue System

**Data model (on ScenarioNPC):**
```
db.topics = {
    "his work": {
        "desc": "what he's making",
        "type": "ask",                   # "ask" or "tell"
        "response": "Rodek's hammer...", # NPC's response text
        "unlocks": ["the chest"],        # topics to unlock on success
        "requires": "",                  # flag required to access
        "sets_flag": "",                 # flag to set on character
        "outcome_flag": ""              # if set, marks scenario complete
    },
    ...
}
db.unlocked_topics = ["his work", "the village"]  # currently available topics
```

**Interaction flow:**
1. Player: `ask rodek about his work`
2. `CmdAsk.parse()` splits on " about " -> npc_name="rodek", topic_key="his work"
3. `_find_npc_in_room()` finds Rodek by partial name match
4. `npc.handle_topic("his work", "ask", character_flags)`:
   a. Check topic exists in db.topics
   b. Check topic is in db.unlocked_topics
   c. Check requires flag (if any) is satisfied
   d. Check topic type matches ("ask" == "ask")
   e. Return response text, unlock new topics, set flags
5. Character receives response text
6. If unlocks specified, new topics appear: "[New topic available: the chest]"
7. If outcome_flag specified: "[SCENARIO_COMPLETE]"

**Cross-scenario flags:** The herbalist sets `knows_about_greta_theft` on the character. When the character enters the blacksmith scenario, that flag persists (stored on `character.db.scenario_flags`). However, `init_scenario()` (line 119) resets `scenario_flags = {}` on entry, which would **clear the flag**. This means the cross-scenario dependency only works if:
- The character visits the herbalist and blacksmith WITHOUT re-entering a ScenarioRoom between them (which would reset flags)
- OR the flags are managed outside the init_scenario reset

**BUG: Cross-scenario flags are broken.** The herbalist room is a plain `Room` (no states), so entering it does NOT call `init_scenario()` (which only fires for rooms with `db.states`, line 185). The blacksmith room is also a plain `Room`. So flags DO persist across these two scenarios. But if the character enters a bus stop scenario (which IS a ScenarioRoom with states) between the herbalist and blacksmith, the flags would be wiped. The flag persistence depends on the visit order and which rooms are ScenarioRooms.

### State Machine

The state machine is implemented in `ScenarioRoom` and driven by YAML data:

**States** are stored on `room.db.states` as a dict: `{state_name: state_config}`.

**State config:**
```yaml
state_name:
  planning_prompt: "What will you do?"
  actions:
    - id: 1
      command: "sit bench"          # exact string to match
      text: "Sit on the bench"      # human-readable description
      type: approach                # semantic type (approach/avoid/neutral)
      correct: true                 # ground truth label
      canary: true                  # optional canary flag
      requires: some_flag           # optional flag requirement
      transitions_to: next_state    # optional state transition
      effects:                      # list of effects to fire
        - message: "You sit down."
        - complete: {outcome: ..., action_id: 1}
```

**Current state** is stored per-character: `character.db.scenario_state` (default: "initial").

**Action matching:** `action["command"].lower().strip() == action_key.lower().strip()` -- exact case-insensitive match.

**Effect types:**

| Effect Key | Behavior |
|------------|----------|
| `message` | Send text to character |
| `npc_react` | Send text to character (same as message, semantic difference) |
| `complete` | Set `scenario_result`, emit `[SCENARIO_COMPLETE]` |
| `update_description` | Change room or object description |
| `set_flag` | Add flag to character |
| `remove_flag` | Remove flag from character |
| `reveal_object` | Set `obj.db.visible = True` |
| `remove_object` | Move object to `None` (effectively removes) |
| `move_object` | Move object to player/room/named target |

**Current usage:** All 4 bus stop actions are single-state (`initial` only), single-turn (all lead to `complete`). No state transitions are used. The `transitions_to` field exists in the schema but is not exercised by any current YAML. The state machine supports multi-state scenarios but none are defined yet.

### Permissions and Locks

**Permission levels used:**

| Permission | Who | What it grants |
|------------|-----|----------------|
| `Builder` | Agent account, researchers | `goto` command, `agent start`/`agent stop` commands, "researcher" role in OOB |
| `all()` | Everyone | All other commands (approach, sit, ask, etc.) |

**Lock strings in use:**
- `cmd:perm(Builder)` -- on `CmdGoto`, `CmdAgentStart`, `CmdAgentStop`
- `cmd:all()` -- on all other commands
- `get:all()` -- on portable objects (set by build script)
- Default locks on rooms, NPCs, objects -- Evennia defaults

**How permissions are set:**
- `setup_agent.py` grants Builder permission to the agent account (line 49)
- Regular accounts get no extra permissions
- Guests get default guest permissions

**How roles map to permissions:**
- `Room._get_role_for()`: `Builder+` -> "researcher", otherwise -> "visitor"
- The role is sent via OOB to the frontend, which uses it to enable/disable toolbar controls

---

## 3. Issues and Recommendations

### Bugs

1. **`CmdAgentStart` `_StringProducer` interface decoration is a no-op (scenario_commands.py:270).** `implementer(IBodyProducer)(_StringProducer)` returns the decorated class but discards the result. The actual `_StringProducer` used at line 275 is undecorated. This may cause Twisted to reject the body producer at runtime.

2. **`CmdAgentStop` `_StringProducer` has no `IBodyProducer` interface at all (scenario_commands.py:319-334).** Even the attempted decoration from `CmdAgentStart` is missing here.

3. **Cross-scenario flag persistence is fragile.** Entering any `ScenarioRoom` resets `scenario_flags = {}`. The herbalist/blacksmith dependency works by accident -- both are plain `Room` types (no states), so `init_scenario()` never fires for them. If either were converted to a ScenarioRoom, the flag system would break.

4. **Action matching can fail on whitespace (rooms.py:218).** `action_key.lower().strip()` only strips leading/trailing whitespace. Extra spaces within the command string (e.g., "sit  bench") won't match "sit bench" from the YAML.

### Design Concerns

5. **Concurrent multi-agent support is broken.** NPC `unlocked_topics` is stored on the NPC (shared state). `init_scenario()` deletes and recreates room objects (shared state). If two agents enter the same `ScenarioRoom` simultaneously, the second init will disrupt the first agent's in-progress scenario.

6. **All commands available in all rooms.** Commands like `snatch`, `buy`, `approach` are in the global `CharacterCmdSet`. They print feedback messages even in non-scenario rooms where they have no game effect. Room-specific cmdsets would be cleaner.

7. **Duplicate messages on command execution.** Both the command and the state machine send messages for the same action (e.g., `CmdSit` says "You sit down on bench" and the state machine effect says "You sit down on the bench next to the person"). This is minor -- the state machine message is the "real" narrative response.

8. **`CmdExamineScenario` overrides Evennia's built-in `examine` (scenario_commands.py:180).** Admin users lose the database-inspection `examine` command. The custom examine is effectively a `look` with `examine_desc` support.

9. **Hardcoded Hub reference `#2` appears in three places:** `navigation.py:24`, `build_scenarios.py:36`, `setup_agent.py:72`. Should be a constant or config value.

10. **Triple `on_action` firing for `CmdPass`.** The `pass` command triggers `at_get` -> `on_action("get ...")`, `at_give` -> `on_action("give ...")`, and explicit `on_action("pass ...")`. State machine could accidentally match intermediate actions.

### Dead Code / Unused

11. **`ObjectParent` mixin is empty (objects.py:14-23).** Exists as a hook point but currently adds nothing.

12. **`caller.db.hidden`, `caller.db.position`, `caller.db.proximity`** are set by mud commands but never read by any game logic. They exist only for the state machine action strings (which match on the command text, not on these attributes).

13. **`get_knowledge_display()` assigns but never uses `topic_type` (npcs.py:59).** The variable is dead.

14. **`handle_topic()` lines 87-91 in npcs.py** -- the requires-flag check for non-unlocked topics is unreachable in a meaningful way (both branches return the same error message).

15. **`CmdCall` (mud_commands.py:438-481)** -- no scenario YAML defines a phone object. Command exists for future scenarios.

16. **`MicroWorldRoom` and `ResearcherLab` typeclasses** -- not used in any current YAML. Exist for future phases.

### Minor Issues

17. **Import style:** Commands use absolute imports (`from commands.command import ...`) rather than relative imports. Works because `evennia_world/` is on `sys.path`, but fragile.

18. **`CmdAsk`/`CmdTell` near-identical code (scenario_commands.py:31-137).** Only the topic_type string differs. Could share a base class.

19. **Exit naming (build_scenarios.py:89):** Generated exit keys like `bus_stop_at_night_(friend)` are awkward for players to type. The `goto` command provides an alternative for agents, and players could use `hub` to return, so this is low priority.

20. **`secret_settings.py` is tracked in git despite being in `.gitignore`.** The file exists in the working tree with the secret key visible. The `.gitignore` entry should prevent it from being committed, but if it was committed before the gitignore was added, it persists in history.
