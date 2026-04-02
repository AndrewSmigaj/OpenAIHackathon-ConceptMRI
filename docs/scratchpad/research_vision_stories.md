# Research: VISION.md Additions & User Stories Assessment

Created: 2026-03-30
Agent: Vision & User Stories Assessment

---

## 1. VISION.md Gap Analysis

**The plan is correct: VISION.md describes research vision but not software vision.** However, the gap is more nuanced:

- VISION.md already has substantial content: the three components, scaffold hierarchy, scaffold dynamics, the agent, cognitive loop, research institution, Claude Code as runtime, 5-phase overview, ethics.
- What it does NOT have: what the software looks like (no MUD terminal + viz panels layout), what a researcher's workflow is, what a visitor's experience is, how ConceptMRI and MUD integrate, what the current software does RIGHT NOW before any MUD work.
- The nuance the plan misses: software vision content already exists scattered across INSTITUTION_DESIGN.md (what visitors see) and architecturemud.md (the unified interface). The gap is that none of it is in VISION.md where a new conversation would look first.

**Placement recommendation:** Add the new section AFTER "Scope Philosophy" and BEFORE "Ethical Considerations" -- not before "Why Text Worlds" as the plan proposes. The document argues research motivation first; breaking that flow early would be disorienting. The reader needs to understand why MUDs matter before being told what the MUD interface looks like.

**Recommended subsections:**
1. "What You See Today" -- ground the reader in the current working ConceptMRI system
2. "The Unified Interface" -- MUD terminal + viz panels, experience-focused
3. "Two Modes, One Tool" -- basin identification vs. live mode, researcher vs. visitor
4. "The Progression" -- current ConceptMRI -> MUD shell -> Evennia -> agent sessions

**Certainty: HIGH** that the gap exists. **MEDIUM** on exact placement/structure.

---

## 2. User Stories Completeness

**Two critical stories are missing from the 8 candidates:**

**A. "Run the full analysis pipeline"** -- This is what the software does TODAY. The 6-stage pipeline (PIPELINE.md): design probe -> capture activations -> categorize outputs -> explore clustering in UI -> Claude analyzes and writes reports -> present findings. None of the 8 candidates captures this end-to-end. This should be story #1.

**B. "Claude Code analyzes a dataset"** -- Claude Code is a first-class runtime consumer. It reads cluster route data from the API, examines sentence distributions, writes element descriptions and window reports, produces cross-window synthesis. The plan mentions Claude Code as a persona but has no dedicated story.

**Also missing (lower priority):**
- C. Troubleshoot a failed capture (OOM recovery, GPU management)
- D. First-time setup

**Additional personas needed:**
- **Emily as system administrator** -- real persona with distinct needs (server lifecycle, GPU memory, WSL2 quirks). The `/server` skill serves this persona. Brief operational stories, not full stories.
- **Claude Code as analysis runtime** -- the MOST underrepresented persona. Not a traditional "user" but a first-class consumer of APIs and data with its own 6-stage workflow. Needs 2-3 "capability stories" in its own section.
- **Em-OSS-20b** and **AI scientist agents** -- Phase 4+ and Phase 5+ respectively. Do NOT include in near-term stories.

---

## 3. Story Accuracy (per story)

| # | Story | Accuracy | Issue |
|---|-------|----------|-------|
| 1 | Explore polysemy experiment | HIGH | Works today. Note dependency on prior `/analyze` run for descriptions. |
| 2 | Run a new probe | HIGH | Works today. Consider splitting into design+capture and categorize+explore. |
| 3 | Compare scaffold effects | **LOW** | No comparison mechanism exists. No scaffold field in ProbeRecord. Cross-session comparison is informal only. Rewrite to reflect current manual capability. |
| 4 | Watch agent reason in real-time | **LOW** (current) | Requires Phase 4 agent loop, live capture, streaming, live UMAP. Keep but mark Phase 4+. |
| 5 | Investigate routing anomaly | HIGH | Exactly what Claude Code does during Stage 5 analysis. |
| 6 | Temporal basin analysis | HIGH | `/temporal` skill exists, backend endpoints work, frontend has TemporalAnalysisSection. |
| 7 | Cross-session synthesis | MEDIUM | Works informally (Claude reads multiple sessions). No structured infrastructure. Rewrite honestly. |
| 8 | Design a new micro-world | **LOW** (current) | Micro-world YAML configs "not yet created." MUD Creator panel is Phase 5. Rewrite as Phase 2+. |

---

## 4. Vision-Architecture Alignment

**Major contradiction: Three different phase numbering systems.**
- VISION.md "Scope Philosophy": 5 phases focused on the agent (connect, memory, knowledge, autonomy, swarm)
- architecturemud.md: 7 phases (0-6+) focused on the MUD interface
- DEV_PROCESS.md: 5 phases focused on agent architecture

These describe the same project with incompatible numbering. The software vision section must either reconcile them or clearly state which system it uses. architecturemud.md phases are the most implementation-accurate.

**Other issues:**
- "Existing probes ARE micro-worlds" (architecturemud.md 1.C) is a conceptual stretch that could confuse readers
- INSTITUTION_DESIGN.md features (AI scientists, federated model, study registries) are far beyond what architecturemud.md supports. Software vision must not promise these in near-term.
- VISION.md Phase 1 says "Connect to a MUD" while architecturemud.md Phase 1 says "local commands, no Evennia" -- direct contradiction.

**Certainty: HIGH** that phase reconciliation is needed.

---

## 5. Missing Personas

| Persona | Include in Stories? | Rationale |
|---------|-------------------|-----------|
| Emily (sysadmin) | Brief operational section | Real persona, distinct needs, but operational not analytical |
| Claude Code (runtime) | YES -- dedicated section | Most underrepresented. First-class pipeline consumer. 2-3 capability stories. |
| Em-OSS-20b (agent) | NO | Phase 4+. System design concern, not user story. |
| AI scientists | NO | Phase 5+ at earliest. Vision doc material. |
| Paper reviewer | NO | Same software needs as researcher, different intent. |

---

## 6. Revised Story List (13 stories)

**Current System (works today):**
1. Run the full analysis pipeline
2. Explore a completed experiment
3. Investigate a routing anomaly
4. Run temporal basin analysis
5. Cross-session synthesis (informal)

**Claude Code as Runtime:**
6. Categorize model outputs
7. Analyze clusters and write reports

**MUD Phase (Phase 1-3):**
8. Command-driven exploration
9. Visitor browses micro-worlds

**Full Vision (Phase 4+):**
10. Watch an agent reason in real-time
11. Compare scaffold effects on basin separation
12. Design a new micro-world

**Operational:**
13. Start a research session
