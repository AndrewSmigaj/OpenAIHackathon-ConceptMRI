> **Frozen reference (2026-03-31).** This document captures the original design vision.
> Implementation decisions are in `docs/architecturemud.md`, which may simplify,
> defer, or override details here. Do not update this doc to track implementation
> changes — consult it when later phases need the full design.

# LLMUD — AI System Design

This document describes the cognitive architecture of the LLMUD agent. The design principle is minimalism: fewer components, each doing more, all built from the same primitive — scaffolds.

---

## Contents

- [The Agent: Em-OSS-20b](#the-agent-em-oss-20b)
- [The Loop](#the-loop)
- [Context Assembly](#context-assembly)
- [Scaffolds](#scaffolds)
- [Memory](#memory)
- [NPC and Social Profiles](#npc-and-social-profiles)
- [Reflection and REM](#reflection-and-rem)
- [Tools](#tools)
- [Infrastructure](#infrastructure) — Model routing, event bus, error handling, harmony format, interpretability hooks
- [Research Directions](#research-directions) — Future work, not Phase 1 targets
- [Open Questions](#open-questions)

---

## The Agent: Em-OSS-20b

The primary agent runs on gpt-oss-20b locally on the developer's GPU machine. Key properties that shape the design:

- **128k context window** — scaffolds, memories, game history, and reasoning traces all load freely. Context limits are not a practical constraint.
- **Native tool calling and structured output** — no grammar hacks needed. Test native first; fallback to constrained grammar only if reliability issues emerge in practice.
- **Configurable reasoning effort** — low / medium / high, set via a single line in the system prompt. Same model handles all phases at different effort levels.
- **Full chain-of-thought** — reasoning traces visible and loggable via the harmony analysis channel.
- **Harmony response format** — required, not optional. The inference layer applies it.
- **MoE architecture** — 20B total parameters, ~4B active per token. Fits in 16GB MXFP4 quantized.

When better hardware or budget allows, the reasoning role upgrades to a more capable model. The routing is per-task and configurable.

---

## The Loop

Every agent cycle runs four phases:

```
ASSESS → PLAN → ACT → LEARN
```

Each phase is guided by scaffolds. The model is the substrate. Scaffolds are what run on it.

```
World tick opens — Evennia sends state
        │
        ▼
    ASSESS  [reasoning: low]
    Load assess scaffold
    Read: parsed world output, game state, recent history, active goals
    Summarize situation
    Determine depth: routine or complex
        │
        ▼
    PLAN  [reasoning: medium or high]
    Load planning scaffold
    Search scaffold registry → select relevant scaffolds
    Retrieve relevant memories
    Load selected scaffolds and memories into context
    Form intention
        │
        ▼
    ACT  [reasoning: medium or high]
    Call ConceptMRI inference server
    → sends prompt
    ← receives harmony channels + residual stream coordinates
    Parse channels: analysis → log, final → action
    Submit action to Evennia
    Log everything to disk
        │
        ▼
    LEARN (offline / REM)
    Claude Code reads log files directly
    Reflection → proposals staged to disk
    Human reviews proposals via /review
```

**Reasoning effort routing:**
- Assess: `Reasoning: low`
- Plan + Act on known situations: `Reasoning: medium`
- Plan + Act on novel or high-stakes situations: `Reasoning: high`
- The assess scaffold determines which depth applies

---

## Context Assembly

Context assembly happens at the end of PLAN, before the inference call.

| Priority | Content | Typical Size | Notes |
|----------|---------|-------------|-------|
| 1 (always) | System prompt + personality scaffold | ~500 tokens | Never dropped |
| 2 (always) | Current game state | ~200 tokens | Never dropped |
| 3 (always) | Goal document | ~500 tokens | Cap at 600 tokens, archive completed goals |
| 4 (always) | Triggering event + recent output | ~300 tokens | Never dropped |
| 5 (always) | Tool definitions | ~300 tokens | Scoped to situation |
| 6 | Loaded scaffolds (selected by plan) | ~1000 tokens | Drop least-relevant first |
| 7 | Retrieved memories | ~500 tokens | Drop oldest first |
| **Total** | | **~3300 tokens** | Well within 128k window |

At 128k context this table is rarely a constraint. It exists as a defined policy for when it matters.

---

## Scaffolds

Scaffolds are the whole system. Every prompt is a scaffold. The assess phase, planning phase, combat behavior, social reasoning, goal management — all scaffolds. The model reads them and reasons accordingly.

### Levels

**Meta-scaffolds** — How to think. Stable, human-authored. The assess and planning scaffolds live here.

**Strategic scaffolds** — What to prioritize. Co-created by human and agent.

**Tactical scaffolds** — How to handle specific situations. Reasoning guidance and decision trees. Transfer across MUDs.

**Procedural scaffolds** — Exact command sequences for known tasks. MUD-specific, must be relearned per world.

**Data scaffolds** — World knowledge. Maps, prices, NPC profiles, bestiary. Auto-maintained.

### Format

```markdown
---
name: basic_combat
domain: combat
version: 3
triggers: ["enters combat", "is attacked"]
useful_when: ["fighting enemies", "in danger"]
created_by: human          # human | agent | collaboration
last_effective: 2026-03-23
effectiveness_notes: "Works well 1v1. Needs update for group combat."
---
# Basic Combat
## Assessment
1. Check enemy type — use `consider` to gauge difficulty
...
```

Data scaffolds are JSON.

### Lifecycle

1. **Bootstrap** — meta-scaffolds ship with the system
2. **Growth** — new scaffolds proposed by REM, reviewed by human
3. **Refinement** — existing scaffolds updated through reflection
4. **Auto-refinement** — data scaffolds only (prices, bestiary, maps). All cognitive scaffolds require human review.
5. **Human collaboration** — player and agent co-author scaffolds

### Discovery

```
search_scaffolds(domain="combat") → filtered list with metadata
list_scaffolds() → all scaffolds, metadata only
read_scaffold(name) → full content
```

Triggers in frontmatter pre-load scaffolds before planning runs.

### Bootstrap Scaffold Set

**`meta_assess.md`** — What to read, what to summarize, how to set reasoning depth.

**`meta_plan.md`** — How to search for relevant scaffolds, form intention.

**`meta_goals.md`** — Goal process: priorities, stuckness detection, sub-goal recursion.

**`meta_scene.md`** — How to process a new room: observe, connect to goals, assess danger, update map.

**`meta_needs.md`** — Survival-level reasoning: recognize critical resource levels, override other goals.

**`meta_learning.md`** — When to record an insight, how to flag something for REM.

---

## Memory

Memory is what scaffolds read from and write to. The scaffold library IS procedural memory.

**Episodic** — What happened. Timestamped events, stored in SQLite.

**Semantic** — What we know. Facts and relationships. JSON + SQLite.

**Procedural** — The scaffold library.

Clean separation: `remember()` searches episodic and semantic stores. `search_scaffolds()` searches procedural memory.

### Retrieval

`remember(query)` — keyword and tag matching initially, vector search when the knowledge base needs it. Schema supports embedding fields from day one.

### Consolidation (REM)

After each session, Claude Code is invoked and reads log files directly from disk — session logs, episodic memory exports, scaffold files. No server or API needed. Claude Code produces proposals as markdown files staged for review. Nothing is written to final state without human approval.

- Session logs → extract patterns → propose semantic memory updates
- Recurring patterns → propose new or updated scaffolds
- Contradictions → flag for human review
- Redundant entries → propose summarization

### Goal Document

A markdown file the agent reads and writes. Managed by `meta_goals.md`. Capped at ~600 tokens — completed goals rotate to `goals_archive.md` after each session.

**Write locking:** file-based lock with PID-based stale detection. Acquired before any write, released after. Claude Code never writes goals directly — proposals staged to `goals_proposals.md`.

---

## NPC and Social Profiles

```yaml
name: "Merchant Greta"
first_met: "2026-03-23, Town Market"
relationship_score: 45
emotional_state_last_seen: "frustrated — complained about thieves"
known_desires:
  - "wants thieves caught"
known_personality:
  - "pragmatic"
  - "values honesty"
conversation_history:
  - "Offered 50% discount if I deal with the thieves"
groklets:
  - "Seems trustworthy but self-interested"
empathy_notes:
  - "She's stressed about the thefts — this is affecting her livelihood"
```

**Groklets** — subjective interpretation units, not objective facts. Different personality scaffolds produce different groklets about the same NPC. Capped at 10 per NPC; consolidated during REM.

**Empathy** — modeled as mirroring, strength is a personality axis. Strong empathy has gameplay consequences: others' needs feel compelling, manipulation vulnerability increases.

**Conversation strategy** — before dialogue the agent selects an approach: information gathering, persuasion, negotiation, relationship building, or comfort/support. Each has its own scaffold.

Profiles stored as YAML in `characters/{name}/semantic/npcs/`.

---

## Reflection and REM

Reflection runs offline. Claude Code is invoked (via `claude -p`) and reads the relevant log files directly from the character directory. No server needed — Claude Code has filesystem access and reads what it needs.

**Reflection types:**

**Narrative Review** — What happened? Session journal, key events, timeline.

**Analytical Review** — Why did things happen? Decisions, outcomes, missed signals.

**Strategic Review** — What should change? Scaffold proposals, goal reassessment.

**Meta-Review** — How well did the scaffolds work? Gaps, rigidity, failure modes.

**Multi-Perspective Review** — For significant events: same event through narrator, analyst, strategist, critic system prompts. Synthesis pass integrates perspectives. Low-cost precursor to the full swarm — validates multi-viewpoint reasoning before building infrastructure.

All output is proposals staged to `proposals/` for human review. Journals apply directly.

---

## Tools

**Game**
```
send_command(cmd)
```

**Memory**
```
remember(query) → str
learn(category, data)
get_game_state() → GameState
```

**Analysis** (lightweight real-time only)
```
analyze_events(filter, method) → str
# Real-time: frequency, count, recency
# Heavy methods run during REM by Claude Code reading log files
```

**Goals**
```
read_goals() → str
update_goals(content)        # Acquires file lock
```

**Scaffolds**
```
search_scaffolds(domain, query) → list
read_scaffold(name) → str
create_scaffold(name, content)    # Staged for review
update_scaffold(name, changes)    # Staged for review
```

**World**
```
check_map(query) → str
note_location(data)
```

**Social**
```
recall_person(name) → str
update_person(name, data)
```

---

## Infrastructure

### Model Routing

| Task | Model | Reasoning Effort |
|------|-------|-----------------|
| Assess | Em-OSS-20b | Low |
| Plan + Act (routine) | Em-OSS-20b | Medium |
| Plan + Act (complex) | Em-OSS-20b | High |
| Future upgrade | gpt-oss-120b or API model | — |
| Offline reflection | Claude Code (reads files directly) | — |

Em is called via the ConceptMRI inference server, not Ollama or LMStudio. This is required for live residual stream capture. The inference server handles harmony formatting and returns response + coordinates in one call.

### Event Bus

Central async pub/sub, in-process asyncio. Events are Pydantic models, logged to SQLite. Subscribers non-blocking.

| Category | Examples |
|----------|---------|
| Game | `room_entered`, `combat_started`, `npc_spoke`, `hp_changed` |
| Agent | `goal_updated`, `scaffold_loaded`, `action_decided`, `memory_stored` |
| System | `session_started`, `session_ended`, `model_called`, `error_occurred` |
| Analysis | `reflection_completed`, `memory_consolidated`, `scaffold_evaluated` |

### Error Handling

| Failure | Response |
|---------|----------|
| LLM malformed output | Retry with explicit format instruction (max 2), then log and skip turn |
| Evennia connection drops | Reconnect with backoff, pause loop, notify |
| ConceptMRI server unreachable | Retry 3x, then fall back to Ollama (no coordinates), alert user |
| Tool call fails | Log, continue without result |
| Claude Code fails | Log, skip REM this session, retry next |
| SQLite write conflict | Wait with timeout, log if exceeded |
| Scaffold file corrupted | Fall back to previous version, alert |

### Harmony Format and Channel Separation

Em-OSS-20b outputs to three channels:

- **analysis** — raw chain-of-thought. Unfiltered. This is where attractor conflicts play out.
- **commentary** — tool calling preamble.
- **final** — the response sent to the game.

The ConceptMRI inference server parses these channels and returns them separately. The final channel goes to the game loop. The analysis and commentary channels go to the log pipeline — never to the game or the user.

### Interpretability Hooks

Every inference call logs: full prompt, all three harmony channels separately, scaffold versions active, outcome, token counts, latency. The analysis channel is stored as `response_analysis` — the primary signal for attractor conflict research.

ConceptMRI analyzes both streams:
- **Residual stream activations** — which basin is active at each layer
- **Analysis channel text** — the model's explicit conflict reasoning, used to label activation captures

The combination gives ground truth that most interpretability work has to infer: the model's own words describing its reasoning conflict, and the internal representational state during that reasoning simultaneously.

---

## Research Directions

*These are future directions, not Phase 1 targets. Items marked [Build] will become design sections when their phase arrives. Items marked [Research] are open questions explored over time.*

### Creating Virtuous LLMs [Research]

Can scaffolding make an LLM behave more wisely — not just more helpfully?

LLMs have internalized attractors. Most are useful. But they're context-blind — they fire on surface pattern, not situational wisdom. Two layers of conflict:

**Scaffold-induced** — A scaffold activates the wrong attractor in a specific context.

**Internalized** — The model's own basins pull against the scaffold's intent. Which wins is measurable.

### The Experimental Design [Research]

The Evennia test world generates attractor conflict situations. The agent is given user needs (money, reputation, survival, quests, relationships) that deliberately conflict with each other and with internal attractors. The world records outcomes — ground truth, no inference needed.

**Attractor candidates:**
- Helpfulness under uncertainty
- Fiction maintenance (particularly sticky)
- Completion bias
- Sycophancy
- Social harmony

Each scenario designed so attractor-following produces a measurable bad outcome. Conflict matrix: user needs versus LLM attractors, world as referee.

### ConceptMRI as the Instrument [Research]

Outcomes tell you whether the attractor won. ConceptMRI tells you what happened internally: residual stream capture during the forward pass, UMAP projection, cluster analysis. Compare scaffold A versus scaffold B — did the representation actually shift, or did the scaffold just add aligned-sounding words on top of the same underlying processing?

### The Self-Scaffolding Endpoint [Research]

Long-term target: the agent detects its own attractor activating and applies a learned interrupt. ConceptMRI shows whether the interrupt produces genuine representational change or just additional tokens.

### Motivation and Flourishing [Build — Phase 5]

Grounded in virtue ethics — balanced flourishing across survival, competence, social connection, exploration, creativity, coherence. Personality is scaffolding — a coherent configuration of need strengths and reasoning styles. Needs significant further design work.

### Internal Family Systems / Swarm [Build — Phase 5]

Specialized agents coordinating through a shared blackboard. Validate first with multi-perspective prompting (already in REM) before building infrastructure.

### Dual-Model Processing [Build — deferred]

Two models, always running, domain-partitioned. Fast model: parsing, vitals, reflexes. Slow model: reasoning, planning, social. Deferred; architecture supports it without refactoring.

### LoRA and Basin Reshaping [Research]

Insights graduating from scaffold to weights. Risk: basin reshaping — context-specific attractors becoming context-general. Pre/post-LoRA basin analysis is a ConceptMRI target. Held at arm's length.

---

## Open Questions

**Critical**
- Full content of each bootstrap scaffold — needs drafting
- How does the assess scaffold decide routine vs. deep reasoning?

**Important**
- How to operationalize flourishing?
- Right frequency for periodic goal review?
- How does the agent recognize when a scaffold is working against it?

**Research**
- Can ConceptMRI detect which attractor is active during reasoning?
- Does scaffold refinement produce measurable representational change?
- How does personality scaffolding interact with model-level personality?
- Can we detect maladaptive attractors before observable behavior?
