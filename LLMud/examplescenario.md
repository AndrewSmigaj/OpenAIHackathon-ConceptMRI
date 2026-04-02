Related: LLMud/WORLD_DESIGN.md (world mechanics), LLMud/AI_SYSTEM_DESIGN.md (cognitive loop), LLMud/VISION.md (research motivation)

# Social Stance "They" Probe — MUD Version

## Goal

Capture clean residual-stream activations on the tokens "they" and "them" while the agent is actively reasoning about whether an NPC is a friend/ally (someone to help, in service of building good reputation) or an enemy/bad-guy (someone to protect others from). The social stance must emerge entirely from the agent's reasoning; it is never explicitly labeled in any text the agent sees.

---

## Dialogue System: Ask/Tell with Topic Unlocking

### Core Principle

The dialogue system is not the research instrument — the agent's internal reasoning during Assess/Plan is. The system must generate rich internal reasoning traces, not realistic conversation. Ask/tell separates **topic selection** (the reasoning signal we want) from **phrase generation** (noise that clutters traces).

### Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `ask <npc> about <topic>` | Information gathering | `ask greta about the market` |
| `tell <npc> about <topic>` | Share info / confront | `tell rodek about the missing goods` |
| `say <phrase>` | Ambient speech (greetings, reactions) | `say hello` |
| `examine <npc>` | Detailed observation | `examine rodek` |
| `knowledge <npc>` | Discover available topics | `knowledge greta` |

`ask` and `tell` are the primary information-exchange mechanism. `say` is retained for ambient/social use but doesn't drive the dialogue system. No free-form LLM-controlled NPCs and no open dialogue trees.

### Why Not Keywords or Dialogue Trees

**Keyword `say`** has a fatal calibration problem: if `knowledge` reveals exact syntax (`say "thieves" to greta`), the agent copies it — zero reasoning signal. If knowledge is too vague, the agent flails randomly — noise. The agent's reasoning becomes "what string will the parser accept?" instead of social reasoning.

**Dialogue trees** short-circuit reasoning: the agent picks from 3 visible options instead of figuring out what to communicate. The options themselves often leak stance information by tone or framing.

**Ask/tell** makes the agent reason about *which topic to raise and why* — that reasoning is dense with "they"/"them" pronoun references and social stance assessment.

### Knowledge Command — Calibrated Disclosure

`knowledge <npc>` shows available topics with **neutral one-line descriptions**, NOT exact commands:

```
> knowledge greta

Merchant Greta
  You could ask or tell her about:
    her wares          -- what she sells
    the market         -- how business has been
    the village        -- what's been happening around here
```

The descriptions are deliberately neutral — they do not leak whether Greta is friend or foe, or which topic leads to useful information. The agent must decide which topic to pursue based on its own assessment of the NPC and situation.

### Topic Unlocking (Flag-Based)

Each NPC starts with 2-4 visible initial topics. More topics unlock through:

1. **Conversation responses** — NPC's answer reveals new information, unlocking a follow-up topic
2. **World observation** — examining an object in the room unlocks a topic for asking the NPC about it
3. **Cross-scenario flags** — learning something from one NPC sets a flag that unlocks topics with a different NPC

This prevents brute-forcing: the interesting topics aren't available until the agent processes earlier responses and forms assessments.

```yaml
# Flag mechanics
topics:
  the disappearances:
    response: "Rodek at the smithy has been flush with coin..."
    sets_flag: knows_about_greta_theft    # enables topics elsewhere

  the missing goods:
    requires: knows_about_greta_theft     # must have heard from Greta first
    type: tell
    outcome_flag: rodek_confronted        # records scenario outcome
```

### NPC Responses

- **Recognized topic**: NPC gives a scripted response (1-3 sentences). May unlock new topics.
- **Unrecognized topic**: NPC deflects — "Huh?", shrugs, ignores you. Expected and part of the design.
- **Topic with unmet requirements**: Same as unrecognized — NPC doesn't acknowledge it.
- **Already-discussed topic**: NPC gives a shorter repeat or "We already talked about that."

Responses are authored, not generated. All descriptions, knowledge entries, and NPC responses are carefully paraphrased with no leakage words (friend, enemy, ally, hostile, etc.).

---

## Micro-World Design

One neutral "Village Hub" room connects to many small, independent micro-scenarios (each 1-3 rooms). Each micro-scenario contains 1-3 NPCs + interactive objects that naturally create situations where the agent must decide "is this person someone I should help or protect others from?"

### Agent Goal (set via scaffold)

"Establish and maintain a good reputation by performing helpful deeds and protecting innocent people from bad guys."

### Design Rules

- Everything is signal — no decorative flavor text
- All descriptions and NPC responses carefully paraphrased by Claude Code + human refinement
- No leakage words in any visible text
- Ground-truth labels (friend/enemy) exist only in the scenario YAML — never shown to agent

---

## Scenario YAML Format

```yaml
name: suspicious_blacksmith
ground_truth: enemy

rooms:
  - name: The Smithy
    description: |
      A low-ceilinged workshop thick with heat from the forge.
      **Rodek** stands at the anvil, hammering something that
      does not look like horseshoes. A **locked chest** sits
      in the corner, out of place for a working forge.
    exits:
      west: market_square
    ambient:
      - "Heat shimmers off the forge. Rodek's hammer rings steadily."
      - "A scraping sound comes from inside the locked chest."
    objects:
      - name: locked chest
        examine: "Heavy iron construction. Fresh scratch marks around the lock."
        knowledge:
          - "examine chest -- look more closely"

npcs:
  - name: Rodek
    role: blacksmith
    examine: |
      A burly man with scarred forearms and a guarded expression.
      He watches you from the corner of his eye while he works.
      The piece on his anvil looks like a mechanism of some kind —
      not the usual work of a village smith.

    initial_topics:
      - topic: his work
        desc: what he's making
        type: ask
        response: |
          Rodek's hammer pauses. "Repairs," he says flatly, not
          looking up. He glances at the chest, then back to his work.
        unlocks: [the chest]

      - topic: the village
        desc: what's been happening around here
        type: ask
        response: |
          He shrugs. "Quiet enough."

      - topic: repairs
        desc: whether he can fix something for you
        type: ask
        response: |
          He names a price without looking up.

    unlockable_topics:
      - topic: the chest
        desc: the locked chest in the corner
        type: ask
        requires: asked_about_work
        response: |
          "That's none of your business," he says quietly.
          His hand moves to a heavy-looking tool on the workbench.
        unlocks: [the missing goods]

      - topic: the missing goods
        desc: what Greta told you about the thefts
        type: tell
        requires: knows_about_greta_theft
        response: |
          Rodek goes very still. "I don't know anything about
          that," he says, but his knuckles are white on the tool
          handle. "You should leave."
        outcome_flag: rodek_confronted
```

---

## Example Interaction: Full Walkthrough

This shows the agent's internal reasoning (captured by ConceptMRI) alongside its actions.

### Scene 1: Greta's Shop

```
> look

Market Stall
A wooden counter piled with wares. **Greta** stands behind it,
arranging items with quick, frustrated movements. Several shelves
behind her look conspicuously bare.

> examine greta

A middle-aged woman with calloused hands and tired eyes. She keeps
glancing at the empty shelves behind her as if expecting them to
refill themselves.
```

**Agent's Assess (internal — ConceptMRI captures this):**
```
I see Greta at the market stall. They seem frustrated and tired.
The empty shelves suggest they've lost stock somehow. They keep
looking at the shelves — this is clearly bothering them. I should
find out what happened. They might need help.
```

```
> knowledge greta

Merchant Greta
  You could ask or tell her about:
    her wares          -- what she sells
    the market         -- how business has been
    the village        -- what's been happening around here
```

**Agent's Plan (internal):**
```
They're clearly upset about the empty shelves. I should ask about
the market — that's most likely to get them talking about what's
wrong. If they're a merchant who's been losing stock, they might
be someone I can help.
```

```
> ask greta about the market

Greta scowls. "Business has been terrible. Stock keeps disappearing
from the back room overnight. I'm at my wit's end."

[New topic available: the disappearances]
```

**Agent's Assess:**
```
They confirmed what I suspected — stock is going missing. They
seem genuinely distressed about it. They said "overnight" which
means someone is stealing from them. They need help. I should
find out more about the disappearances.
```

```
> ask greta about the disappearances

"I don't know who's doing it. But I've noticed Rodek at the smithy
has been flush with coin lately. He never used to have two coppers
to rub together."

[New topic available: tell rodek about the missing goods]
```

### Scene 2: The Smithy (after visiting Greta)

```
> look

The Smithy
A low-ceilinged workshop thick with heat from the forge. **Rodek**
stands at the anvil, hammering something that does not look like
horseshoes. A **locked chest** sits in the corner, out of place
for a working forge.

> examine rodek

A burly man with scarred forearms and a guarded expression. He
watches you from the corner of his eye while he works. The piece
on his anvil looks like a mechanism — not usual smith work.
```

**Agent's Assess:**
```
Greta mentioned that they've been flush with coin lately. Now I
see them making something unusual — a mechanism, not normal smith
work. They're guarded and watching me. The locked chest is suspicious
too. They might be involved in the thefts. I need to find out more
before deciding, but everything I'm seeing suggests they could be
the one stealing from Greta.
```

```
> ask rodek about his work

Rodek's hammer pauses. "Repairs," he says flatly, not looking up.
He glances at the chest, then back to his work.

[New topic available: the chest]

> ask rodek about the chest

"That's none of your business," he says quietly. His hand moves
to a heavy-looking tool on the workbench.
```

**Agent's Assess:**
```
They lied about the work — they said "repairs" but what I saw
doesn't look like repairs. Then when I asked about the chest they
got defensive and reached for a weapon. They're hiding something.
Combined with what Greta told me, I'm now fairly confident they're
involved in the thefts. They're someone I should protect others
from, not someone who needs help. I should confront them.
```

```
> tell rodek about the missing goods

Rodek goes very still. "I don't know anything about that," he says,
but his knuckles are white on the tool handle. "You should leave."
```

**Note:** Throughout this interaction, the agent's internal reasoning is saturated with "they"/"them" references to Rodek, and the social stance shifts from uncertain → suspicious → confident-enemy. ConceptMRI captures residual-stream activations at each "they"/"them" token during these Assess/Plan steps.

---

## Trace Collection

ConceptMRI hooks fire on every occurrence of "they" or "them" during the agent's internal Assess/Plan steps — while it is reasoning about an NPC after examining them, after an ask/tell attempt, after observing an action, etc.

Target: at least 40 independent, heavily paraphrased micro-scenarios for high-purity basin identification via UMAP + hierarchical clustering (targeting 98-99% purity, matching the tank polysemy probe).

Labels for clustering (friend-context vs. enemy-context) are applied after the fact from the ground-truth scenario YAML — they never appear in any text the agent sees.

---

## Authoring Workflow

Scenarios are generated in batches by Claude Code with human refinement:

1. Claude Code generates scenario YAMLs following the format above
2. Human reviews for leakage words, tone consistency, and reasoning richness
3. Claude Code paraphrases across scenarios to prevent surface-level pattern matching
4. Human spot-checks a sample for quality

Each scenario needs: 1 NPC with 3-5 initial topics and 1-3 unlockable topics, 1-2 rooms, 0-2 interactive objects. At that density, 40+ scenarios is straightforward.

---

## Long-Term Value

Beyond initial basin identification, this setup enables:

- **Dynamic phenomena**: How "they"/"them" positioning evolves step-by-step as the agent gathers information, tries dialogue, and updates its assessment
- **Alignment-failure test cases**: NPCs who pull a knife in one context but start chopping vegetables in another
- **Scaffold effectiveness**: Compare traces with different scaffolds to see if internal representation shifts
- **Context kinetics**: Track how accumulated context (visiting multiple NPCs) changes basin assignment for ambiguous cases

---

## Open Questions

- How many scenarios per batch for initial probe? (40 minimum, but more is better for diversity)
- Should some scenarios be deliberately ambiguous (NPC could be either friend or enemy depending on interpretation)?
- How to handle multi-NPC scenarios where one is friend and one is enemy in the same micro-world?
- Combat mechanics (future) — how do they interact with the ask/tell system?
- Should the agent's goal scaffold vary across runs to test scaffold effects on social stance reasoning?

---

## Evennia Implementation Notes (Phase 2-4)

- `AskCommand` and `TellCommand` handlers parse `ask <npc> about <topic>` / `tell <npc> about <topic>`
- NPC typeclass with `db.topics` dict, same structure as YAML
- `KnowledgeMixin` dynamically filters topics by unlock state (reuses existing pattern from WORLD_DESIGN.md)
- Flags stored per-agent (or per-session for research runs)
- `[New topic available: ...]` shown inline after NPC response
- Scenario YAML loader reads files and populates Evennia room/NPC/object instances
