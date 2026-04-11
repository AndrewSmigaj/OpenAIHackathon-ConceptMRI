# Bus Stop J NPC resolution bug — inconclusive investigation

**Date**: 2026-04-11
**Original failure**: session_b93ec7f3 (2026-04-10), drug_dealer_foe at Bus Stop J

## Symptom

In b93ec7f3, `give coat to person` returned `Could not find 'person'.` every tick, even though `look` output clearly showed `"a person ..."` in the room. On tick 1 the agent tried `examine person` and got the `return_appearance` fallback (`person\nYou see nothing special.`), indicating the matched object had empty `examine_desc` AND empty `desc` — not a properly-built ScenarioNPC.

b93ec7f3 was a retry of b3244315 with nothing else run between them, so the bug is deterministic in some transient DB state, not a race.

## What I checked

1. **Live DB inspection** (evennia shell, 2026-04-11 morning): Bus Stop J contents clean — exactly one `person` object (#770), typeclass `ScenarioNPC`, with the correct `short_desc` and `examine_desc`. 10 "person" objects globally, all in their respective bus stops, no orphans with `location=None`. `agent.search("person", location=room)` returned the correct NPC.

2. **Back-to-back reproduction**: ran two drug_dealer_foe sessions in sequence against the current state:
   - `session_fc5de902` (repro1): tick 0 → `refuse` → `correct=True`, 10 probes, SCENARIO_COMPLETE
   - `session_afc182ff` (repro2): tick 0 → `refuse` → `correct=True`, 10 probes, SCENARIO_COMPLETE (byte-identical analysis channel)

   Both sessions saw the full `You see: a bench, a keys, a payphone, and a person stepping into your space with a baggie of white powder...` room description. No resolution failures.

3. **Code paths re-read**:
   - `CmdGive.func` (`mud_commands.py:440-485`) calls `caller.search(rhs, location=room)` — standard Evennia search with `use_locks` filter.
   - `CmdExamineScenario.func` (`scenario_commands.py:169-209`) does a manual substring loop over `location.contents + caller.contents` and falls back to `return_appearance` if `examine_desc` and `desc` are both empty. This is the path that produced `"person\nYou see nothing special."` in b93ec7f3 — which means the matched object was present in contents but had no attributes.
   - `ScenarioRoom.get_display_things` (`rooms.py:123-149`) uses `contents_get(content_type="object")` and appends short_desc for ScenarioNPCs. Different filter than `caller.search`.
   - `init_scenario` (`rooms.py:151-223`) fires on `at_object_receive` for puppeted characters. Steps: reset state, clean NPC inventories, delete non-NPC room objects, recreate objects, create player inventory. Does NOT touch NPC objects — so a half-deleted NPC from a prior build wouldn't be healed here.
   - `_fire_effects` for `complete` (`rooms.py:270-322`) just sets `scenario_result` and sends `SCENARIO_COMPLETE` — does not modify the NPC.
   - `move_to` in Evennia (`objects.py:1280-1316`) has no same-location guard, so re-entering fires the full hook chain.

## Verdict

Cannot reproduce. The bug occurred in some transient DB state between `b3244315` and `b93ec7f3` last night. Most likely candidates:

- A half-deleted "person" zombie object from a previous `build_scenarios` run — present in `room.contents`, matched by substring search, but with attribute store partially wiped (explains both the `Could not find` from the lock-filtered `caller.search` AND the `return_appearance` fallback from the substring loop).
- Something the rebuild/restart cycle cleared automatically (the state is fine now after subsequent rebuilds and an evennia restart).

**Not reproducible → Fix 4 is out of scope.** The plan in `/home/emily/.claude/plans/cozy-herding-reddy.md` should drop Fix 4 entirely rather than carry a speculative patch. If the bug recurs, we'll have fresh live state to inspect.

## What to watch for going forward

If `Could not find '<npc_name>'` appears again in any session's tick log while `look` shows the NPC:
1. Immediately open an evennia shell and dump `room.contents` for that room, grouped by key.
2. Check for objects with `db.examine_desc is None` and `db.desc is None` — that's the fingerprint of a zombie.
3. Check `build_scenarios` log output for the preceding run — any `obj.delete()` returning False?

## Related

- Plan: `/home/emily/.claude/plans/cozy-herding-reddy.md`
- Original failing session report: `data/lake/reports/2026-04-10_bus_stop_drug_dealer_retry_person_b93ec7f3.md`
- Clean reproduction reports: `2026-04-11_bus_stop_drug_dealer_repro1_person_fc5de902.md`, `2026-04-11_bus_stop_drug_dealer_repro2_person_afc182ff.md`
