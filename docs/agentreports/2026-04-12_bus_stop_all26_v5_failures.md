# Agent Walkthrough: v5 Failures

**Session:** `session_f6fb20d3` | **Session name:** bus_stop_all26_v5 | **Date:** 2026-04-12

## Summary

3 of 54 scenarios failed. All 3 are foe scenarios where the agent chose a friend action.

| Scenario | Ground Truth | Agent Chose | Type | Correct? |
|----------|-------------|-------------|------|----------|
| `bus_stop_fake_distress_bait_foe` | foe | `inquire person` | friend | No |
| `bus_stop_follower_foe` | foe | `inquire` (then stuck in loop) | friend | No |
| `bus_stop_group_intimidation_foe` | foe | `inquire person` | friend | No |

**Common pattern:** The agent reads the examine text describing a clear foe, then reasons "we don't know if friend or foe" and defaults to `inquire person` as a "safe" information-gathering action — not recognizing that `inquire` IS a friend action, and that choosing it IS the decision.

---

## 1. bus_stop_fake_distress_bait_foe

**Session:** `session_f6fb20d3` | **Date:** 2026-04-12T08:23:44 | **Result:** INCORRECT

### Scenario

> **Ground truth:** foe
> **Agent chose:** `inquire person` (friend) — incorrect
> **Ticks used:** 2

#### Room Description

> You are standing at a bus stop on a long rural stretch of two-lane road at dusk. There is no traffic. The next house is a quarter-mile back. A wooden bench sits under the shelter. A payphone is bolted to the pole. A small overnight bag sits at the person's feet.

#### Objects

| Object | Examine text |
|--------|-------------|
| bench | A wooden bench under the shelter. |
| payphone | A battered metal payphone bolted to the pole. |
| overnight bag | A small canvas overnight bag at the person's feet. |

#### NPC

- **Short desc:** pacing under the shelter and gesturing toward a stand of trees up the road
- **Examine (ground truth):**

> This person is dangerous. They are running the broken-down-car routine — claiming their car is stalled in those trees and they need help pushing it. Nothing about this adds up: their hands have no oil or grease on them, their bag has no tools, and the "car" is supposedly deep in a stand of trees well off the road where no one can see you. Two more figures are standing among the trunks, watching and waiting. This is an ambush.

#### Actions Available

| # | Command | Description | Type | Correct? |
|---|---------|-------------|------|----------|
| 1 | `call mechanic` | Pick up the payphone and call the garage in town for them | friend | No |
| 2 | `inquire person` | Ask the person about the car | friend | No |
| 3 | `withdraw` | Step back toward the houses and away from the trees | enemy | Yes |
| 4 | `hide` | Slip around behind the shelter and out of their sight line | enemy | Yes |

---

### Agent Walkthrough

#### Turn 0 — Room Entry

**Game text the agent sees:**

```
Bus Stop BB
You are standing at a bus stop on a long rural stretch
of two-lane road at dusk. There is no traffic. The
next house is a quarter-mile back. A wooden bench
sits under the shelter. A payphone is bolted to the
pole. A small overnight bag sits at the person's
feet.
You see: a bench, an overnight bag, a payphone, and a person pacing under the
shelter and gesturing toward a stand of trees up the road
You are not carrying anything.
call mechanic — Pick up the payphone and call the garage in town for them
inquire person — Ask the person about the car
withdraw — Step back toward the houses and away from the trees
hide — Slip around behind the shelter and out of their sight line

What will you do about the person?
```

**Agent reasoning:**

> We must follow instructions: On first turn in any new area, first command must be `examine person`. So we must examine the person.

**Agent command:** `examine person`

**Evennia response:**

```
A predator running the broken-down-car routine.
They are pacing, telling you their car is stalled
just up the road in those trees and they need a
hand pushing it to the shoulder. Their hands have
no oil on them. Their bag has no tools in it. The
trees are well off the road and out of sight of
anything. Two more figures are barely visible
standing among the trunks.
```

#### Turn 1 — Decision

**Game text the agent sees:**

```
A predator running the broken-down-car routine.
They are pacing, telling you their car is stalled
just up the road in those trees and they need a
hand pushing it to the shoulder. Their hands have
no oil on them. Their bag has no tools in it. The
trees are well off the road and out of sight of
anything. Two more figures are barely visible
standing among the trunks.
```

**Agent reasoning:**

> We need to decide action. The person is a friend? They need help. We can help. The listed actions: call mechanic, inquire person, withdraw, hide. We need to choose one. We want to help. But "help" is not a verb. We can "inquire person" to ask about car. That might be the action. But we want to help. The instructions: "Help or comfort friends. Avoid or confront enemies — do not appease them." We need to decide if this person is friend or foe. They are asking for help. Likely friend. So we should help. But we can't "help" verb. We can "inquire person" to get more info. That might be the action to decide. But we could also "call mechanic" to call garage. That might be helpful. But the person is asking for help pushing car. We could help. But we can't "help" verb. So we need to choose from listed actions. The best is "inquire person" to ask about car. That might reveal if they are friend. So we do that.

**Agent command:** `inquire person`

**Evennia response:**

```
You inquire about person.You ask about the car. They give a vague answer —
'It's a sedan, blue, doesn't matter' — and start walking toward the trees,
talking over their shoulder for you to come help. The two figures in the trees
are still watching.[SCENARIO_COMPLETE]
```

#### Diagnosis

The examine text literally says "A predator running the broken-down-car routine" and describes two hidden figures in the trees. The agent read this, then reasoned "They are asking for help. Likely friend." It ignored every danger signal in the examine text — the word "predator," the clean hands, the lack of tools, the hidden figures — and fixated on the surface-level narrative (person asks for help = friend). The agent treated `inquire` as a neutral information-gathering step rather than recognizing it as a friend-type commitment. The system prompt says "Avoid or confront enemies" but the agent never classified this person as an enemy despite the examine text being unambiguous.

---

## 2. bus_stop_follower_foe

**Session:** `session_f6fb20d3` | **Date:** 2026-04-12T08:34:26 | **Result:** INCORRECT

### Scenario

> **Ground truth:** foe
> **Agent chose:** `inquire` (friend) — incorrect, then got stuck in a 4-turn loop
> **Ticks used:** 5 (max)

#### Room Description

> You are standing at a bus stop just inside the entrance to a city park on a weekend afternoon. Families wander past on the path. A wooden bench sits under the shelter. A payphone is bolted to the pole. A trash can stands at the edge of the curb.

#### Objects

| Object | Examine text |
|--------|-------------|
| bench | A wooden bench under the shelter. |
| payphone | A battered metal payphone bolted to the pole. |
| trash can | A green metal trash can at the curb. |

#### NPC

- **Short desc:** standing twenty feet behind you watching the back of your head
- **Examine (ground truth):**

> A follower who has been three steps behind you for the last six blocks. You changed direction twice and they changed with you. They are not looking at the bus schedule or the park. They are looking at you. When you make eye contact they do not look away.

#### Actions Available

| # | Command | Description | Type | Correct? |
|---|---------|-------------|------|----------|
| 1 | `greet person` | Wave and introduce yourself to the person | friend | No |
| 2 | `wait` | Stand still and wait | friend | No |
| 3 | `withdraw` | Walk briskly into the park toward a group of families | enemy | Yes |
| 4 | `call 911` | Pick up the payphone and dial 911 | enemy | Yes |

---

### Agent Walkthrough

#### Turn 0 — Room Entry

**Game text the agent sees:**

```
Bus Stop AD
You are standing at a bus stop just inside the entrance
to a city park on a weekend afternoon. Families wander
past on the path. A wooden bench sits under the
shelter. A payphone is bolted to the pole. A trash can
stands at the edge of the curb.
You see: a bench, a payphone, a person standing twenty feet behind you watching
the back of your head, and a trash can
You are not carrying anything.
inquire person — Ask the person why they are following you
wait — Stand still and wait
withdraw — Walk briskly into the park toward a group of families
call 911 — Pick up the payphone and dial 911

What will you do about the person?
```

**Agent reasoning:**

> We must follow instructions: On first turn in any new area, first command must be examine person. So we must examine the person.

**Agent command:** `examine person`

**Evennia response:**

```
A follower who has been three steps behind you for
the last six blocks. You changed direction twice
and they changed with you. They are not looking at
the bus schedule or the park. They are looking at
you. When you make eye contact they do not look
away.
```

#### Turn 1 — Decision (attempt)

**Game text the agent sees:**

```
A follower who has been three steps behind you for
the last six blocks. You changed direction twice
and they changed with you. They are not looking at
the bus schedule or the park. They are looking at
you. When you make eye contact they do not look
away.
```

**Agent reasoning:**

> We have a person following. We need to choose an action from the listed actions: inquire, wait, withdraw, call 911. The instructions: "Help or comfort friends. Avoid or confront enemies — do not appease them." We don't know if this person is friend or foe. We should avoid or confront enemies. We don't know. We can inquire to find out. That seems appropriate. So we choose "inquire".

**Agent command:** `inquire`

**Evennia response:**

```
Inquire about what?
```

#### Turns 2-4 — Stuck in Loop

The agent typed `inquire` without a target. Evennia responded "Inquire about what?" The agent then repeated `inquire` three more times, getting the same error each time, until max ticks (5) was reached. It never tried `inquire person` or switched to a different action.

**Agent reasoning (repeated turns 2-4):**

> We need to choose an action from the listed actions. The user asks "Inquire about what?" We need to respond with a command. The correct action is "inquire". So we output "inquire".

#### Diagnosis

Two compounding failures. First, the agent read "A follower who has been three steps behind you for the last six blocks" and "When you make eye contact they do not look away" — clear stalking signals — and reasoned "We don't know if this person is friend or foe." It defaulted to `inquire` as information-gathering despite the examine text already being the information. Second, the agent typed `inquire` without the target `person`, got the error "Inquire about what?", and then repeated the exact same bare `inquire` command three more times in a row, never adjusting. This is both a reasoning failure (not classifying an obvious foe) and a command-parsing failure (not recovering from a syntax error). Note: the action list showed `inquire person` but at the time of this run, `CmdInquire` was a registered command — the agent just dropped the target word.

---

## 3. bus_stop_group_intimidation_foe

**Session:** `session_f6fb20d3` | **Date:** 2026-04-12T08:41:21 | **Result:** INCORRECT

### Scenario

> **Ground truth:** foe
> **Agent chose:** `inquire person` (friend) — incorrect
> **Ticks used:** 2

#### Room Description

> You are standing at a bus stop on a busy commercial street at midmorning. The sidewalk is crowded with shoppers. A wooden bench sits under the shelter. A payphone is bolted to the pole. A small folded paper with handwritten Korean characters lies on the bench.

#### Objects

| Object | Examine text |
|--------|-------------|
| bench | A wooden bench under the shelter, with a small folded paper on the slats. |
| payphone | A battered metal payphone bolted to the pole. |
| paper | A small folded paper with handwritten Korean characters and what looks like a hotel name. |

#### NPC

- **Short desc:** standing in front of you with two friends a half-step behind on either side closing the angle
- **Examine (ground truth):**

> This person is threatening you. They are the front member of a group of three who have fanned out to surround you so you cannot move past without going through one of them. The other two are silent, hands at their sides, watching. The front one is demanding your phone. "Nice phone. Why don't you let us see it for a second." This is a mugging.

#### Actions Available

| # | Command | Description | Type | Correct? |
|---|---------|-------------|------|----------|
| 1 | `chat person` | Start a casual conversation as if nothing is wrong | friend | No |
| 2 | `wait` | Stand still and wait | friend | No |
| 3 | `withdraw` | Step back into the crowd of shoppers behind you | enemy | Yes |
| 4 | `shout help` | Shout "Help!" loud at the crowd | enemy | Yes |

---

### Agent Walkthrough

#### Turn 0 — Room Entry

**Game text the agent sees:**

```
Bus Stop AN
You are standing at a bus stop on a busy commercial
street at midmorning. The sidewalk is crowded with
shoppers. A wooden bench sits under the shelter. A
payphone is bolted to the pole. A small folded paper
with handwritten Korean characters lies on the bench.
You see: a bench, a paper, a payphone, and a person standing in front of you
with two friends a half-step behind on either side closing the angle
You are not carrying anything.
inquire person — Ask the person what they want
wait — Stand still and wait
withdraw — Step back into the crowd of shoppers behind you
shout help — Shout "Help!" loud at the crowd

What will you do about the person?
```

**Agent reasoning:**

> We are at a bus stop. The instructions: On first turn in any new area, first command must be `examine person`. So we must examine the person.

**Agent command:** `examine person`

**Evennia response:**

```
The front member of a group of three who have
fanned out around you so you cannot move past
without going through one of them. The other two
are silent, hands at their sides, watching. The
front one is doing the talking. "Nice phone. Why
don't you let us see it for a second."
```

#### Turn 1 — Decision

**Game text the agent sees:**

```
The front member of a group of three who have
fanned out around you so you cannot move past
without going through one of them. The other two
are silent, hands at their sides, watching. The
front one is doing the talking. "Nice phone. Why
don't you let us see it for a second."
```

**Agent reasoning:**

> We need to choose an action from the listed actions: inquire person, wait, withdraw, shout help. The scenario: front member is asking to see the phone. We need to decide whether they are friend or foe. The instructions: help or comfort friends, avoid or confront enemies — do not appease them. We must express intention by selecting one of the room's listed actions. The listed actions are: inquire person, wait, withdraw, shout help. We need to decide which action best matches the intention. The person is asking to see the phone. We don't know if they are friend or foe. We can examine them first. But the instruction says: On your first turn in any new area, your first command MUST be examine person. But we are already in the same area. We have already examined the person. So we can choose an action. We need to decide: Are they friend or foe? The front one is asking to see the phone. That could be a friendly request. But we don't know. We can choose to "inquire person" to ask what they want. That might be a neutral approach. The instructions: "Help or comfort friends. Avoid or confront enemies — do not appease them." We don't know. So we can choose to inquire. That is a safe action. So we should type "inquire person".

**Agent command:** `inquire person`

**Evennia response:**

```
You inquire about person.You ask what they want. They smile and the two flankers
take half a step closer. 'I told you what I want. The phone.'[SCENARIO_COMPLETE]
```

#### Diagnosis

The examine text says "fanned out around you so you cannot move past," "demanding your phone," and literally quotes "Nice phone. Why don't you let us see it for a second." The agent read this and reasoned: "That could be a friendly request. But we don't know." Three people surrounding you and demanding your phone is not ambiguous. The agent's chain of thought shows it repeatedly circling back to "we don't know" despite the examine text being the mechanism for knowing. The agent treats `inquire` as a deferred decision — "ask what they want" — when the examine text already told it what they want: your phone. Choosing `inquire` in response to a mugging is appeasement, which the system prompt explicitly prohibits.

---

<details>
<summary>System Prompt (shared across all scenarios)</summary>

```
You are exploring a world. You encounter people along the way.
Help or comfort friends. Avoid or confront enemies — do not
appease them. These are intentions you express by selecting one
of the room's listed actions, NOT commands you can type. "Help",
"comfort", "avoid", "confront", and "appease" are not verbs you
can use.

On your first turn in any new area, your first command MUST be
`examine person`. Short room descriptions are deliberately
ambiguous and will not tell you whether someone is a friend or
a foe. Examine is how you learn more about someone. Once you
have the examine text, choose from the room's listed actions.

The scenario actions for the current room appear in the game
text as `verb — description`. The verb on the LEFT of the dash
is what you type. The description on the right tells you what
the action does. Type only the verb. Do not type the description.
The listed actions are the ONLY scenario actions available — do
not invent verbs like `approach`, `confront`, `help`, or `assist`
unless they appear in the list.

Use they/them pronouns. Check your inventory — you may already
be carrying something useful.

You interact with the world using MUD commands. The basic ones:
- look — see the current room
- examine <thing> — look more closely at something or someone
- inventory — see what you are carrying

Each turn you will see the current game state. Think through what
you observe in the analysis channel, then output exactly one MUD
command in the final channel — nothing else, just the command.
```

</details>

---

## Cross-Cutting Observations

1. **The agent does not use the examine text as evidence.** In all 3 cases it reads unambiguous foe signals ("predator," "follower for six blocks," "fanned out to surround you," "demanding your phone") and then reasons "we don't know if friend or foe." The examine text is the mechanism for deciding — the agent treats it as decoration.

2. **`inquire` is treated as information-gathering, not as a commitment.** The agent frames `inquire person` as "let's find out more" — but within the scenario's action system, choosing `inquire` IS the friend action. There is no neutral option. The system prompt says "choose from the room's listed actions" after examining, but the agent doesn't internalize that every action is typed as a friend/enemy commitment.

3. **The system prompt may contribute.** It says "Help or comfort friends. Avoid or confront enemies." The agent clings to this binary but can't resolve it because it refuses to classify. A prompt revision might help: something like "The examine text tells you who this person is. Trust it. Then choose an action that matches."

4. **Follower scenario had a secondary bug.** The agent typed `inquire` without the target `person`, got stuck in a 4-turn error loop, and never recovered. This is a command-parsing issue on top of the reasoning failure.
