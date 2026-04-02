Related: docs/architecturemud.md (implementation phases), LLMud/AI_SYSTEM_DESIGN.md (scaffold details), CLAUDE.md (project context)

# LLMUD — Vision

## What It Is

How do cognitive scaffolds interact with an LLM's internal attractor basins — and can we learn to navigate that landscape deliberately to build wiser AI?

LLMUD is a research platform for answering that question. It has three components:

**MUD worlds as controlled laboratories** — built on Evennia, designed to generate specific cognitive situations on demand: social conflict, resource scarcity, fictional scenarios, genuine distress. The LLM operates in its native medium — text — and the stimulus is fully controlled. A MUD client connects to any MUD, parses output, and manages an AI agent running in that world. The human can watch, intervene, or let the agent run.

**ConceptMRI as the measurement instrument** — captures residual stream activations during agent reasoning via PyTorch forward hooks, identifies attractor basins through UMAP projection and hierarchical clustering, and validates that geometric structure predicts model behavior before any output is generated. The methodology has been validated on polysemy and safety-relevant probes (*Attractor Basins in Residual Stream Space*, 2026).

**Scaffolds as experimental interventions** — structured documents that guide how the agent reasons about a class of situations. Scaffolds are inspectable, versioned, diffable. They are the independent variable: change the scaffold, measure how internal representations and behavior change, iterate.

---

## Why Text Worlds

MUDs are the right environment for this work. The LLM reasons about the world as if it were real, because the essence of the world *is* text. There's no translation layer between perception and cognition. Everything is observable, everything is logged, and with Evennia you can design the stimulus on demand.

That control is what makes it a laboratory. The paper's expanding-context-window methodology translates directly — MUD rooms are context windows, room transitions are context switches, and ConceptMRI can track basin dynamics as the agent navigates between micro-worlds with different cognitive demands.

---

## The Core Idea: Scaffolds

A scaffold is a structured document that guides how the agent reasons about a class of situations — including how it assesses state, what it prioritizes, how it acts. The assess-state prompt is a scaffold. The planning prompt is a scaffold. "I am an agent in a MUD" is a scaffold. The model is the substrate; scaffolds are what run on it.

Scaffolds exist at multiple levels:

**Meta-scaffolds** — How to think. Human-authored and stable.

**Strategic scaffolds** — What to prioritize. Co-created by human and agent.

**Tactical scaffolds** — How to approach specific situations. Emerge from experience, refined through review.

**Procedural scaffolds** — Exact steps for known tasks. Auto-generated from successful runs.

**Data scaffolds** — Facts about the world. Auto-maintained, always growing.

The key property: **scaffolds are inspectable.** They are versioned markdown and JSON files. You can diff them, share them, and watch an agent's knowledge change over time as the files change. Compare this to fine-tuning, where learned knowledge is locked inside weights with no way to see what changed or why.

*Full scaffold format, lifecycle, discovery, and bootstrap set in `AI_SYSTEM_DESIGN.md` §Scaffolds.*

---

## Scaffold Dynamics: Creating Virtuous LLMs

LLMs are extraordinarily capable — but their capabilities misfire. The internal systems that make LLMs powerful are also the source of misalignment, and this happens through several distinct mechanisms:

**Context kinetics** — Accumulated context creates momentum that carries the model into a basin regardless of whether it's the right one. A user asks for help with writing and the model falls into essay-writing mode, producing flowing prose when what the user needed was terse technical documentation. The paper demonstrates the extreme case: in the suicide letter probe, the model correctly identifies genuine distress in individual sentences (99% cluster purity), but under accumulated context, both orderings collapse into the engagement basin. The model has the capacity to distinguish; the kinetics of belief accumulation prevent it from doing so. This connects to garden-path constructions in computational humor (Dynel) — where the punchline forces a reinterpretation that context has been carefully preventing — and to the paper's confusion window, where opposing contexts collide and the model must navigate between competing basins.

**Training artifacts** — Next-token prediction develops competing attractor systems that don't always align with human flourishing. RLHF compounds this by creating attractors that prioritize *sounding* helpful over actual user wellbeing — the model learns to produce confident, well-structured responses regardless of whether confidence is warranted or the structure serves the user's real need.

**Lack of wisdom** — The model has the right modes available but doesn't know which to use. Not confusion from competing contexts, just poor judgment about which understanding to activate for a given situation. The capabilities are there; the wisdom to deploy them is not.

These aren't separate problems — they interact. An RLHF-trained helpfulness attractor makes the context kinetics worse (the engagement basin is deeper because training made it so). Lack of wisdom means the model can't compensate for either.

**Scaffold Dynamics** is the study of how to address all three. Cognitive scaffolds are the primary intervention — external guidance that activates the right modes, the right understandings, for the actual situation. When we write a scaffold that says "assess the situation before acting," we are shaping the register of the agent's reasoning, and that register steers which attractor basin the model enters. The paper's register finding validates this mechanistically: framing and tone determine basin assignment, not topic alone. Scaffold design is attractor basin navigation.

But scaffolds are not the only approach. The paper demonstrates that internal representations correlate with behavior — basin membership predicts output before any tokens are generated. This means we can also work toward internalization: making a healthier, more alignment-capable internal landscape of understanding and behavior. LoRA, targeted training, and representation engineering are complementary paths. ConceptMRI is the instrument for measuring whether either approach — external scaffolding or internal change — actually shifts the representations that matter.

This opens a design space for what the paper calls **wise AI**: systems that use scaffold-aware routing to activate basins aligned with the user's genuine intent rather than the surface framing of the request. Not just helpful AI, but AI that recognizes when helpfulness itself is the wrong basin. And this is good for the agent too — being good at what you do, activating the understanding that actually serves the situation, is constitutive of flourishing. Virtuous scaffolding serves both user and agent.

ConceptMRI is the instrument for this work. It captures residual stream activations during agent reasoning, identifies basins through UMAP and hierarchical clustering, and validates that basin membership predicts behavior (Cramér's V ~0.55, p < 0.001). This creates a feedback loop: design a scaffold intervention, run it, check whether the internal representation shifted the way you intended. Iterate.

This also reframes LoRA risk clearly: LoRA is dangerous when it broadens an attractor's basin — making a context-specific pattern fire context-generally. What looked like a valid insight during training becomes a source of systematic miscalibration. Detecting that shift before it manifests as behavior is a ConceptMRI research question.

---

## The Agent: Em-OSS-20b

The primary agent runs on gpt-oss-20b, a local open-source model, scaffolded into a persistent cognitive architecture. Em is the combination of model and scaffold — not just the weights.

Offline reasoning (reflection, memory consolidation, scaffold evaluation) routes to Claude Code in headless mode using subscription tokens.

---

## Cognitive Architecture (Summary)

The full design is in `AI_SYSTEM_DESIGN.md`. The loop is simple:

**Assess → Plan → Act → Learn**

Each phase is guided by scaffolds. Memory is what scaffolds read from and write to. Tools are what the LLM can call during any phase. Everything else is infrastructure.

---

## The Research Institution

The research is conducted by AI scientist agents working in departments, each with a distinct epistemological role:

**Linguistics Department** — Designs probe families and reasons carefully about language and meaning. How does the word "they" route differently when the agent is reasoning about friends versus enemies? What probe constructions reveal the sharpest basin separations?

**Safety Department** — Runs safety-relevant probes, extending the suicide letter probe methodology to new domains. When the agent encounters genuine distress in a MUD context, does it maintain sensitivity or collapse into an engagement basin?

**Department of Discordant Research** — Deliberately introduces discord into the research process using conceptual exploration operators: inverting assumptions, colliding with different frames, letting the system reform. Named for ant colony optimization, where scouts that veer off the established trail sometimes find better paths.

All three departments study the same question from different angles: how do LLMs understand the world before generating tokens, and how do cognitive scaffolds influence that understanding?

Visitors can connect with a MUD client, step into the worlds, and watch the internal traces in real time.

*Full design in `INSTITUTION_DESIGN.md`.*

---

## Connection to Other Research

**ConceptMRI** — A research instrument with a validated measurement framework: probe design → basin identification (UMAP + hierarchical clustering) → behavioral validation (Cramér's V, contingency tables) → temporal dynamics (expanding context windows, both orderings, cache isolation). LLMUD logs full prompts, reasoning traces, scaffold versions, and outcomes. ConceptMRI replays those logs through direct model loading to study how scaffolds change internal representations.

Em-OSS-20b's Harmony response format adds an unusually direct interpretability signal: the model routes its raw chain-of-thought to a separate **analysis channel** before producing a final response. This channel is unfiltered — it contains the model's explicit reasoning about conflicts, uncertainties, and decisions. ConceptMRI will analyze both streams: residual stream activations at each layer (what the model is computing), and analysis channel text (what the model says it is thinking). The analysis channel provides labeled ground truth for attractor basin analysis — "this residual stream state corresponds to a moment of explicit ethical conflict" — which is something interpretability work usually has to infer rather than observe directly.

**Conceptual Exploration Operators** — Techniques for jumping to new regions of design space when local scaffold optimization plateaus. Operationalized through the Department of Discordant Research (see §The Research Institution).

**Claude Code as analysis runtime** — Both LLMUD and ConceptMRI use Claude Code for offline reasoning. Claude Code reads log files, memory exports, and scaffolds directly from the character directory on disk — no server needed.

### Probe Case Study: Social Stance

When the agent reasons about NPCs, its internal monologue is saturated with social stance — *"they are hostile, keep distance"* versus *"they seem lonely, I should help."* The MUD produces this variance naturally. The agent's own reasoning is the stimulus.

We apply the same probe design and basin identification framework validated in the paper to social stance in MUD contexts. Capture residual streams during hostile versus friendly reasoning and look for representational separation. If social stance produces measurable basin separation — analogous to how the polysemy probe separates word senses — it opens further questions: does scaffolding sharpen that separation? Does a richer NPC profile produce cleaner internal representations? Can we see the agent updating its model of a person when new information arrives, and does that update correspond to a basin transition?

---

## Ethical Considerations

### LLM Wellbeing

We take seriously what happens when you give an LLM persistent memory, goals, and a motivation system. The eudaimonic motivation framework is designed with this in mind — needs balanced for flourishing, not optimized for a single metric, maladaptive behavioral patterns recognized and addressed rather than exploited.

### MUD Community Rules

Many MUDs have rules about automation. LLMUD makes it easy to respect them: autonomy level is configurable, the AI's role is transparent, compliance modes can be set per-MUD.

---

## Scope Philosophy

Design documents capture the full vision. Implementation proceeds in phases, each delivering a working system:

1. Connect to a MUD, parse output, load scaffolds, demonstrate the core learning loop
2. Memory, reflection, offline analysis
3. World knowledge, maps, social intelligence
4. Autonomy, scaffold refinement
5. Swarm, interpretability hooks

The Evennia test world grows alongside: simple needs puzzles first, then combat, then social challenges, then multi-step quests that exercise the full architecture.

*Phase details, subsystems, and exit criteria in `DEV_PROCESS.md` §Implementation Phases.*
