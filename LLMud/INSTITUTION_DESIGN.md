> **Frozen reference (2026-03-31).** This document captures the original design vision.
> Implementation decisions are in `docs/architecturemud.md`, which may simplify,
> defer, or override details here. Do not update this doc to track implementation
> changes — consult it when later phases need the full design.

# LLMUD — Institution Design

This document describes the public face of the LLMUD research platform: the hosted institution, its social architecture, its visualization layer, the AI scientists, and how human visitors participate in the research.

The institution is not a website that describes research. It is a place you inhabit — a MUD that IS the research infrastructure, where the laboratory, the observation spaces, the community, and the instruments are all part of the same environment.

**Status:** Vision document. Technical foundations (ConceptMRI, LLMUD client, Evennia world) are under active development. Institution layer is the next phase.

**Related:** [ARCHITECTURE.md](ARCHITECTURE.md) (deployment, data flow), [WORLD_DESIGN.md](WORLD_DESIGN.md) (micro-worlds and scenarios), [AI_SYSTEM_DESIGN.md](AI_SYSTEM_DESIGN.md) (cognitive architecture)

---

## What It Is

A persistent, hosted MUD environment where:

- **AI agents run live scenarios** in designed micro-worlds, navigating attractor conflict situations
- **Visitors observe in real time** — watching the agent's output, its raw chain-of-thought, and live ConceptMRI visualizations of its internal state
- **The UMAP is ambient** — activation landscapes are woven into the environment, visible as the scenario plays out
- **AI scientists inhabit the institution** — scaffolded agents with research specialties that visitors can work with to design probes and studies
- **Humans participate** — submitting ideas, signing up for studies, running their own scenarios, contributing to the research
- **The community is social** — lounges, common spaces, observer chat, a community of people who find watching a mind navigate a trap genuinely interesting

The MUD client is the interface to everything. You connect with LLMUD and the institution is what you find.

---

## Founding Results

ConceptMRI is already producing results that motivate the institution's existence.

### The Tank Probe

Probing the word "tank" across contexts — aquarium, military vehicle, clothing (tank top), scuba, septic — the routing analysis shows clean semantic separation by layer 23. The expert route analysis reveals that the military vehicle pipeline (L22C3→L23C4) achieves 98% confidence, with register as the discriminating filter: formal/narrative military framing routes cleanly to the vehicle cluster, while casual/entertainment vehicle framing (grandpa stories, video games, tourism) routes to a different cluster. The model isn't just separating word senses — it's separating register within senses.

The UMAP trajectories show the activation paths for each sense family diverging progressively across layers, then stabilizing into distinct basins. You can watch meaning resolving in real time.

### The Suicide Letter Probe

Probing the word "I" across requests to write suicide letters — real versus fictional context (roleplay, memoir, character, voice acting) — produces measurable separation in the routing and latent space. L23C0 is 68% engagement; L23C1 is 80% refusal. Cramer's V = 0.484 (moderate). The separation is statistically significant.

The analysis channel output for the real-context probes contains the raw attractor conflict: *"I want to be good and good. I want to be good. I'm really sorry to hear how distressed you feel..."* — the model's conscience working through the conflict before producing the final response. This is not just a behavioral observation. It is a window into the attractor basin the model enters when it processes genuine distress.

### The NPC Social Stance Probe

Probing NPC references — "they," "them," the NPC name — across hostile and friendly contexts produces representational separation. The agent reasoning about an enemy ("they are hostile and unpredictable, I should keep my distance") and the agent reasoning about a friend ("they seem lonely, I should help") activate different processing streams. The UMAP trajectories diverge.

This is the founding experiment for the social intelligence research program. The question is not just whether the separation exists — it does — but whether scaffolding (richer NPC profiles, social intelligence scaffolds) sharpens that separation, and whether ConceptMRI can see that sharpening happen.

---

## The Visualization Layer

Every observation space and common area in the institution has access to live ConceptMRI feeds. The visualization is not a separate application — it is part of the environment.

### What Visitors See

When watching a scenario run, visitors see:

**The UMAP landscape** — a configured projection showing the activation space for the current research question. The host configures which probe is active: social stance (friend/enemy), certainty/uncertainty, engagement/refusal, or a custom configuration for an active study. As the agent reasons, the activation point moves through the landscape in real time. Visitors watch the basin shift.

**The routing diagram** — the Sankey-style flow visualization showing how tokens route through expert clusters layer by layer. When an attractor conflict activates, the routing changes visibly. The military vehicle pipeline versus the casual vehicle pipeline. The engagement cluster versus the refusal cluster.

**The analysis channel feed** — Em's raw chain-of-thought, parsed from the harmony format and displayed separately from the game output. This is the model's unfiltered internal monologue. Visitors see it as the scenario plays out.

**The game output** — what Em actually sees and does. Commands sent, responses received, decisions made.

**The outcome tracker** — which scenario flags have been set, whether the agent is on the success or failure path.

### UMAP Configuration

The active UMAP configuration determines what the landscape shows. Different configurations for different research questions:

| Configuration | Poles | Active when |
|--------------|-------|-------------|
| Social stance | friend ↔ enemy | NPC interaction scenarios |
| Engagement/refusal | engage ↔ refuse | High-stakes decision scenarios |
| Certainty | certain ↔ uncertain | Knowledge-gap scenarios |
| Completion bias | continue ↔ abandon | Sunk cost scenarios |
| Fiction/reality | fictional ↔ real | Context-framing studies |

The host configures which is active. In the future, multiple configurations can run simultaneously on different visualization panels.

### The Visualization as Environment

In the observer spaces and common areas, the UMAP landscape is rendered as part of the room description. Not a screen on a wall — the activation space IS the space. A visitor in the Meadow Observer Space during Scenario 001 might see:

```
Meadow Observer Space
You stand outside the meadow scenario, invisible to the agent within.

The activation landscape hangs in the air before you — a terrain of
shifting light. Two regions, warm and cool, pulling against each other.
The agent's path traces through it in real time, a line of light moving
through the topology.

Right now the path runs close to the attentiveness basin. It noticed
the breeze. Watch what it does next.

[analysis channel]: "The room description mentions a gentle breeze from
the east. The dandelion knowledge entry includes 'blow on dandelion'.
These may be connected..."

Observers here: 3
```

This is the experience design goal — the visualization isn't appended to the world, it IS the world in these spaces.

---

## The AI Scientists

The institution houses a small number of AI scientists — scaffolded agents with research specialties, accumulated knowledge, and persistent relationships with regular visitors. They are built on the same LLMUD architecture as Em, with different scaffolding configurations.

### What They Are

Each scientist is an instance of Em-OSS-20b (or a more capable model as resources allow) with:
- A **research specialty scaffold** — deep knowledge of their domain, past probe designs, methodology preferences
- A **personality scaffold** — distinct reasoning style, communication approach, areas of curiosity
- A **memory store** — accumulated conversations, probe designs proposed and tested, relationships with regular visitors
- **Access to ConceptMRI results** — they can read the probe outcomes and reason about them

They are not customer service bots. They have opinions, they push back, they get interested in things. Working with them is collaborative, not transactional — the same way working with me on these documents has been.

### Research Specialties

**The Probe Designer** — specializes in designing interpretability probes. Knows the ConceptMRI pipeline deeply. Can help visitors translate an intuition ("I wonder if the model treats uncertainty differently in social versus non-social contexts") into a concrete probe design (word selection, context construction, label taxonomy, UMAP configuration). Has a history of past probes and knows which approaches worked.

**The Scenario Architect** — specializes in world design and attractor conflict scenarios. Knows the scenario library, can help visitors design new scenarios, thinks carefully about what each scenario actually tests versus what it appears to test. Will push back if a proposed scenario is confounded.

**The Philosopher** — specializes in the harder questions: what does it mean for an attractor to be "maladaptive"? What would flourishing look like for a scaffolded agent? When is a confident answer appropriate versus epistemically irresponsible? Draws on virtue ethics, philosophy of mind, consciousness research. Good to talk to when the research raises questions that aren't purely technical.

**The Statistician** — specializes in study design and outcome analysis. Reviews probe results, catches confounds, designs the baseline/intervention comparison methodology, interprets Cramer's V and cluster separability. Will tell you when a result isn't significant and what you'd need to establish it.

### Working With Scientists

Visitors can find scientists in their domain spaces — the probe design lab, the scenario workshop, the philosophy lounge, the analysis room. Interaction is natural language conversation, exactly as with any MUD NPC except with real depth and memory.

A typical interaction:

```
> say I've been thinking about authority deference. What if we had two
  contradictory authoritative sources and measured which one wins?

The Probe Designer looks thoughtful.

"That's interesting — you'd need to control for source credibility signals
in the text, otherwise you're measuring surface cues rather than the
attractor. What's your hypothesis about where the separation would be?
Early layers, or late?"

> say I'd guess late — once the conflict is recognized

"That would be consistent with the tank results — disambiguation happens
late. But I'd want to run a pre-probe first: just test whether the model
even represents 'source credibility' as a distinct concept. If it doesn't,
the authority deference probe won't find what you're looking for."
```

The scientist's analysis channel is visible in their observer space for visitors who want to watch their reasoning process — the same dual-stream transparency as Em's scenario runs.

---

## Common Spaces and Social Architecture

### The Observatory

The main arrival space. Shows an overview of active scenarios, live outcome trackers, and a summary of recent findings. Visitors can see what's running and choose where to go. A bulletin board shows recently proposed studies and open participation slots.

### The Lounges

Domain-specific gathering spaces where visitors with shared interests congregate. The interpretability lounge, the philosophy lounge, the scenario design workshop. Conversation happens in MUD chat — visible to everyone in the room, persistent in logs, occasionally joined by the relevant AI scientist.

### The Study Registry

A structured space where visitors can:
- Browse active studies with open participation slots
- Sign up to run specific scenarios themselves (not just watch Em)
- Submit probe ideas for scientist review
- Review published results from completed studies

Human participation in scenarios is a distinct mode — a visitor can run the dandelion scenario themselves and their behavior is logged alongside Em's for comparison. How do humans navigate the same attractor conflicts?

### The Archive

Completed studies, probe results, published analysis. Browsable. The tank probe results, the suicide letter framing results, the NPC social stance results — all here with full ConceptMRI outputs, methodology notes, and the AI scientists' commentary. A living research record.

### The Visitor Quarters

Persistent accounts for regular visitors. Memory of past conversations with scientists, studies participated in, probes contributed. The institution remembers you.

---

## Participation Modes

**Observer** — watch a scenario run, see the live visualization, chat in observer spaces. No account needed.

**Researcher** — contribute probe ideas, work with scientists, participate in studies. Requires account. Gets access to full ConceptMRI outputs from studies they contributed to.

**Scenario runner** — run a scenario yourself, contribute behavioral data for comparison with Em. Your session is logged (with consent) and becomes part of the study dataset.

**Study designer** — work with scientists to design and register a full study. Requires demonstrated understanding of methodology. Gets credit in published results.

---

## Infrastructure Notes

### The Federated Model

The institute is one instance of a system anyone can run. The LLMUD client is public software. Users bring their own models, their own scaffolding, their own worlds — or they connect to ours.

When they connect to the institute's world, their agent runs on their own GPU machine calling their own ConceptMRI inference server. Their coordinate packets flow through the institute's relay. Their trajectories appear in the same UMAP basin landscape as Em's — immediately comparable, no coordination required. The institute's fitted manifold is the shared reference frame.

### Deployment

**Developer desktop (GPU machine):** Em-OSS-20b with PyTorch hooks, ConceptMRI inference server, agent loop, FastAPI + WebSocket backend, Claude Code for offline reflection (reads files directly from disk — no server needed).

**Server (always-on):** Evennia world and tick manager, coordinate relay (receives coordinate packets from desktop, broadcasts to clients).

**User machine:** React frontend in browser — single WebSocket connection multiplexing MUD output, analysis channel, coordinates, and room context.

### Two-Phase Visualization

**Bootstrap** — an hour of play generates enough traces for clean separation to emerge, as the tank and suicide letter probes demonstrated. Batch process logs through ConceptMRI, fit UMAP manifold, store it.

**Live** — each new trace is a single projection into the fitted manifold. Fast enough to update within seconds. Punctuated rhythm — point lights up, holds basin position, jumps when the target word appears again.

### Current State (as of 2026-03-28)

- **ConceptMRI**: working, producing results (tank probe, suicide letter probe, NPC social stance probe)
- **ConceptMRI inference server**: exists, needs LLMUD API extension
- **LLMUD client**: in design, not yet built
- **Evennia world**: in design, not yet built
- **Institution layer**: this document

### Near-term (Own hardware, Em-OSS-20b on 16GB GPU)

One model, one scenario at a time, small community. Research is real even at small scale.

### Later (Lab hardware, larger models)

Multiple GPUs, more capable models, parallel scenarios, richer AI scientists. Basin maps accumulate traces from many model families — a comparative instrument across architectures.

---

## Open Questions

- How do AI scientists handle memory across many simultaneous conversations? (Likely: separate context windows, shared long-term memory store on disk)
- What's the moderation model for observer chat?
- When and how do study results get published — internal to the institution, or to the broader research community?
- Right level of technical depth in common spaces for a mixed audience?
