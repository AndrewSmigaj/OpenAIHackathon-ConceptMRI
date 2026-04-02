# Research: CDD & Review Frameworks vs Established Practices

Created: 2026-03-30
Purpose: Evaluate whether our Certainty-Driven Development, review lenses, devil's advocacy, competitive design, and attractor escape concepts are well-grounded in established methodology or are feel-good rituals.

---

## 1. CDD as a Methodology

### What We Planned

CDD (Certainty Protocol, CLAUDE.md section 12; `/cdd` skill) asks Claude to:
1. List every file that will change
2. Rate confidence per change (High/Medium/Low)
3. For Medium/Low items, state what would raise confidence and the risk if assumptions are wrong
4. Recommend "ready to implement" or "need to resolve X first"

### What Established Practice Looks Like

**Pre-mortem analysis (Gary Klein, 2007):**
The pre-mortem assumes the project has already failed, then asks "what went wrong?" Research shows prospective hindsight increases ability to correctly identify reasons for future outcomes by 30% (Klein). It is a 20-30 minute exercise that surfaces risks the team already knows subconsciously but hasn't articulated. The key mechanism: by assuming failure has occurred, it gives permission to voice concerns that optimism bias normally suppresses.

**Confidence calibration (decision science):**
True calibration means a person who says "80% confident" should be right 80% of the time. Research shows humans are systematically overconfident, particularly on tasks they find moderate-to-hard. The Brier score provides a formal measurement (mean squared difference between predicted probabilities and outcomes). Critically, calibration improves with outcome feedback over time -- you need to track whether your confidence ratings were accurate to get better at them.

**Design reviews (PDR/CDR):**
In defense/aerospace engineering, Preliminary Design Review (PDR) verifies that the preliminary design can satisfy requirements within cost/schedule/risk constraints. Critical Design Review (CDR) verifies readiness for fabrication/test. Both involve multi-disciplinary independent assessment against documented criteria. The key difference from CDD: PDR/CDR review against specific quality attributes and requirements, not just general confidence.

**Risk assessment matrices:**
Standard risk management uses a likelihood x impact matrix (typically 3x3 or 5x5). Each risk gets a score; risks above a threshold require mitigation plans. The matrix forces two-dimensional thinking -- something can be unlikely but catastrophic, or likely but trivial.

**Test-Driven Development (TDD):**
TDD focuses test cases first, driving design through the question "how will I verify this works?" CDD focuses confidence first, driving investigation through "what don't I know yet?" These are complementary, not conflicting. TDD is verification-oriented (does it work?), CDD is epistemology-oriented (do I understand the problem?). Both happen before implementation. A combined approach: CDD assessment first (do I understand what to build?), then TDD (can I verify what I build?).

### Gap Analysis

| Aspect | CDD Current | Established Practice | Gap |
|--------|------------|---------------------|-----|
| Confidence rating | 3-level (H/M/L) | Calibration science uses percentages + outcome tracking | CDD lacks feedback loops -- we never check if "High" items actually went smoothly |
| Risk assessment | "What's the risk if wrong?" (freeform) | Likelihood x impact matrix with defined severity levels | CDD conflates likelihood and impact into one question |
| Scope | Per-file/per-change | PDR reviews against quality attributes and requirements | CDD doesn't specify WHAT to assess confidence against |
| Pre-mortem element | Not present | "Assume it failed -- why?" surfaces hidden assumptions | CDD focuses on "what do I know?" not "what could go wrong?" |
| Verification | "Ready to implement" or "resolve first" | Tracked risk register, re-evaluated at milestones | CDD is one-shot; no tracking of whether assessment was correct |

### Verdict: Genuine but Thin

CDD is a legitimate methodology -- it maps to real decision science (confidence calibration, risk identification before commitment). It is NOT just a checklist. But it is currently a simplified version of several practices. It would benefit from:

1. **Add a pre-mortem step.** After the confidence table, ask: "Assume this implementation failed. What went wrong?" This catches risks that confidence ratings miss (the "unknown unknowns").

2. **Add a feedback mechanism.** After implementation, briefly note which confidence ratings were accurate. Over time this calibrates Claude's self-assessment. Even a simple "post-implementation check: were any Medium/Low items actually problematic? Were any High items surprisingly difficult?" would help.

3. **Separate likelihood from impact.** A change can be low-confidence but also low-impact (easy to fix if wrong). Currently CDD treats all Medium/Low items the same.

4. **Specify assessment criteria.** Rather than freeform confidence, assess against: (a) do I understand the existing code? (b) is the approach correct? (c) are there edge cases? (d) does this interact with other components? This gives structure to what "confidence" means.

**Certainty level: HIGH** that CDD is well-grounded. **MEDIUM** that the current implementation captures full value. The improvements above would make it meaningfully more rigorous without making it heavier.

---

## 2. Review Lenses -- Are These the Right 5?

### What We Planned

Five lenses: `onboarding`, `deliverability`, `failure`, `sunk-cost`, `simplicity`

Each asks a different primary question:
- **onboarding**: "Could a new developer/conversation understand this?"
- **deliverability**: "Can we ship each phase independently?"
- **failure**: "What breaks and how do we recover?"
- **sunk-cost**: "Are we doing this because it's needed or because we started it?"
- **simplicity**: "What's the simplest version?"

### What Established Practice Looks Like

**ATAM (Architecture Tradeoff Analysis Method, SEI/CMU):**
ATAM evaluates architectures against quality attribute goals. It explicitly considers tradeoffs between quality attributes (e.g., security vs. performance). The process: gather stakeholders, extract quality attributes from business drivers, create scenarios, analyze architectural approaches against scenarios, identify risks/sensitivity points/tradeoffs. Takes 3-4 days in formal settings.

Quality attributes ATAM typically evaluates: availability, performance, security, modifiability, usability, testability, portability, interoperability.

**Google Code Review (eng-practices):**
Google reviewers look for: design (overall architecture fitness), functionality (correct behavior), complexity (over-engineering), tests (coverage and quality), naming (clarity), style (consistency). The review standard: "Is the overall code health improving?"

**C4 Model (Simon Brown):**
C4 is a visualization approach (Context, Container, Component, Code), not a review framework. But it teaches a useful principle: architecture should be understandable at multiple zoom levels. This maps loosely to our "onboarding" lens.

**Quality Attribute Workshops (QAW, SEI):**
QAW identifies architecture-critical quality attributes before the architecture exists. It derives attributes from business/mission goals. Typical attributes surfaced: availability, performance, security, interoperability, modifiability.

**Standard software quality attributes (ISO 25010 and similar):**
Functionality, reliability, usability, efficiency/performance, maintainability, portability, security, compatibility.

### Comparison Matrix

| Our Lens | Maps To (Established) | Coverage |
|----------|----------------------|----------|
| onboarding | Usability, modifiability (ATAM); complexity/naming (Google); C4 multi-level | Good -- unique framing for AI-conversation context |
| deliverability | No direct equivalent in review frameworks; closer to phase gate reviews (PDR/CDR); agile "shippable increment" | Novel and valuable -- most frameworks assume a single release |
| failure | Availability, reliability (ATAM/ISO); risk identification (risk matrices) | Good but narrow -- focuses on failure modes, not failure severity/likelihood |
| sunk-cost | No equivalent in technical frameworks; comes from behavioral economics | Novel -- addresses a real cognitive bias but is not a technical quality attribute |
| simplicity | Complexity check (Google); "is it over-engineered?" (ATAM sensitivity analysis) | Good -- widely recognized as important |

### What We're Missing

**Security:** Not covered by any lens. ATAM and ISO both treat it as a primary quality attribute. Even for a research tool, security thinking prevents bad habits. However, for this specific project (local research tool, no auth, no user data), security is genuinely low priority. *Recommendation: don't add it now, but note that for any networked/multi-user deployment, add a "security" lens.*

**Performance:** Not explicitly covered. Our "simplicity" lens partially catches performance issues (simpler code is often faster), but doesn't ask "will this be fast enough?" For a tool doing GPU-heavy model inference, performance matters. *Recommendation: consider adding, but could also be a scenario in the "failure" lens (what breaks = "it's too slow").*

**Testability:** Not covered. Google code review explicitly checks for tests. Our lenses review architecture and design but not verifiability. *Recommendation: this is a meaningful gap. Add a question to the "deliverability" lens: "Can each phase be verified? What are the acceptance criteria?"*

**Maintainability/Modifiability:** Partially covered by "onboarding" (can someone understand it?) and "simplicity" (is it over-engineered?). But neither explicitly asks "can this be changed later?" *Recommendation: the coverage is adequate through the combination of onboarding + simplicity.*

### Are Any of Our 5 Redundant?

**sunk-cost and simplicity overlap:** Both ask "should we keep this?" Sunk-cost asks "are we keeping it because we started it?" Simplicity asks "could we delete it?" In practice, these often surface the same findings. However, the cognitive mechanism is different -- sunk-cost challenges emotional attachment, simplicity challenges complexity. *Recommendation: keep both. The overlap is productive, not redundant.*

### Verdict: Good Selection, One Gap

The five lenses are well-chosen for this project's context. They map to established practices but are reframed for an AI-conversation workflow (which is genuinely novel territory). The main gap is **testability/verifiability** -- add verification questions to the "deliverability" lens rather than creating a sixth lens.

The lenses are notably project-specific and cognitive-bias-aware (sunk-cost, onboarding-for-new-conversations), which is more useful for this context than a generic ATAM-style quality attribute list.

**Certainty level: HIGH** that the lens selection is defensible. **HIGH** that testability is the main gap. **LOW** on whether security/performance need their own lenses for this project (they probably don't, but would for a production system).

---

## 3. Devil's Advocate Effectiveness

### What We Planned

The `/devils-advocate` skill:
1. State the current approach
2. Steel-man the opposition (completely different approach, not minor variant)
3. Assumption audit (top 3-5 assumptions, what if each is wrong?)
4. Sunk cost check
5. Simplicity check
6. Verdict

### What Research Shows

**Nemeth's finding (2001) -- the core problem:**
Charlan Nemeth's research at UC Berkeley found that authentic dissent (someone who genuinely believes the opposing view) is significantly more effective than assigned devil's advocacy at stimulating divergent thinking, generating original thoughts, and improving decision quality. People playing a role "don't argue forcefully or consistently enough for the minority viewpoint." Assigned devil's advocacy actually triggers cognitive bolstering of the ORIGINAL position -- the opposite of the intended effect.

**Schwenk meta-analysis (1989-1990):**
Devil's advocacy is more effective than consensus (no challenge at all) but less effective than dialectical inquiry (structured debate between two genuinely held positions). The meta-analysis found both DA and DI led to higher quality recommendations than consensus. DI produced better quality assumptions than DA.

**CIA Structured Analytic Techniques:**
The CIA's tradecraft primer categorizes challenge techniques into three types:
- **Diagnostic** (Key Assumptions Check): Make assumptions explicit and test them
- **Contrarian** (Devil's Advocacy, Red Teaming): Challenge current thinking
- **Imaginative** (Scenario Generation, What-If Analysis): Explore alternatives

The CIA's Red Cell (formed post-9/11) used deliberate cognitive diversity -- a mixture of junior and senior analysts, explicitly excluding domain experts, to avoid the "curse of expertise" that reinforces existing mental models.

**The Tenth Man Rule:**
Israeli intelligence reforms after the Yom Kippur War created dedicated units tasked with challenging prevailing assumptions. The key design choice: dissent became a structural obligation, not a personality trait. When nine people agree, the tenth MUST argue against.

**Performative vs. genuine challenge -- the core tension for AI:**
The research is clear: role-played dissent is weaker than genuine dissent. This is directly relevant to an AI assistant performing devil's advocacy -- Claude doesn't "genuinely believe" anything, so ALL its devil's advocacy is technically role-played. This means:

1. The quality of the challenge depends entirely on the structural rigor of the process, not the conviction of the challenger
2. Open-ended "argue against this" will produce weak, sycophantic challenges
3. Specific, structured techniques (assumption audits, pre-mortems, ACH) produce better results because they constrain the challenge to be concrete

### Gap Analysis

| Technique | Our Skill | Research Best Practice | Gap |
|-----------|----------|----------------------|-----|
| Devil's advocacy | Steps 2-3 (steel-man + assumptions) | Nemeth: assigned DA causes cognitive bolstering | Our steel-man step partially mitigates this but may not be enough |
| Dialectical inquiry | Not present | More effective than DA for assumption quality | We should consider generating a genuine alternative, not just challenging the current one |
| Key Assumptions Check | Step 3 (assumption audit) | CIA: structured, explicit, with defined criteria for each assumption | Our version is good; could add "how would we know if this assumption is wrong?" |
| Pre-mortem | Not present | Klein: 30% improvement in risk identification | Add "assume this approach was implemented and failed -- why?" |
| Red teaming | Not present | CIA: diverse team, explicit exclusion of domain experts | Not applicable to single-agent context |
| Structural obligation | The skill exists but is optional | Tenth Man: dissent as duty, not choice | Could add: "When should this skill be auto-invoked?" |

### What Would Make Our Devil's Advocacy Actually Work

1. **Replace open-ended challenge with structured techniques.** The assumption audit (step 3) is the strongest part. The steel-man step (step 2) is the weakest -- it's exactly the "assigned DA" that Nemeth showed doesn't work well. Replace "argue for something completely different" with "generate a concrete alternative using different assumptions" (dialectical inquiry).

2. **Add pre-mortem framing.** After the assumption audit, add: "Assume the current approach was implemented and failed. Describe the most likely failure scenario in concrete terms." This is more effective than abstract challenge.

3. **Add Analysis of Competing Hypotheses (ACH) elements.** For each assumption, ask: "What evidence would DISPROVE this assumption?" This flips the cognitive direction from confirmation to disconfirmation.

4. **Make it less optional.** The Tenth Man principle: dissent should be structural, not voluntary. Consider auto-triggering `/devils-advocate` for certain categories of decisions (architecture changes, new abstractions, anything the user flags as uncertain).

5. **Be specific about what AI devil's advocacy CAN do well.** An AI can't provide genuine dissent, but it CAN: enumerate assumptions systematically, generate concrete failure scenarios, apply diverse analytical frameworks, check for known antipatterns. Lean into these strengths rather than pretending to "argue against."

**Certainty level: HIGH** that our current design has the performative DA problem. **HIGH** that structured techniques (assumption audit, pre-mortem, ACH) are the fix. **MEDIUM** on exactly how to restructure the skill -- needs iteration.

---

## 4. Competitive Design

### What We Planned

The `/competitive-design` skill:
1. Define the problem and actual constraints
2. Generate 2-3 genuinely different approaches (name, core idea, strengths, weaknesses, complexity)
3. Compare against constraints in a table
4. Recommend a winner and document WHY others were rejected

### What Established Practice Looks Like

**Set-Based Concurrent Engineering (Toyota):**
Toyota's approach: start broad, consider MANY alternatives, narrow gradually. Three principles:
1. Map the design space (define feasible regions, explore tradeoffs, communicate sets of possibilities)
2. Integrate by intersection (find where feasible sets overlap, impose minimum constraint)
3. Establish feasibility before commitment (narrow gradually, increase detail, stay within sets once committed)

The "Second Toyota Paradox": Toyota considers MORE options and delays decisions LONGER than competitors, yet has the fastest development cycles. Exploring more options early saves time later because you avoid dead ends and rework.

**Google Ventures Design Sprint:**
5-day process: Understand, Define, Sketch, Decide, Prototype, Validate. Key features:
- Multiple sketches from different team members (not just 2-3 but many)
- A designated "Decider" role who makes the final call
- Prototyping and user testing before commitment
- Heavy emphasis on divergent thinking BEFORE convergent decision

**Architectural Spikes (Agile):**
Timeboxed research efforts to reduce uncertainty. A spike answers: "Is this feasible? How complex is it?" The key constraint is the timebox -- you don't build the full solution, you build enough to make a decision.

**Proof of Concept:**
Unlike a spike (which answers "can we?"), a PoC answers "should we?" by building a working demonstration of the approach. More investment than a spike, less than a full implementation.

### Is 2-3 Approaches the Right Number?

Research and practice suggest different numbers for different purposes:

| Method | Number of Alternatives | Context |
|--------|----------------------|---------|
| Set-based design (Toyota) | Many (10+), narrowed gradually | Manufacturing, long development cycles |
| Design sprint (GV) | 5-8 sketches, narrow to 1-3 | Product design, one-week timebox |
| Our competitive design | 2-3 | Software architecture, single conversation |
| Architectural spike | 1-2 | Technical feasibility question |

For a single-conversation AI context, 2-3 is pragmatically correct. Generating more than 3 becomes performative -- the differences get superficial. However, the quality of the alternatives matters more than the quantity.

### Gap Analysis

| Aspect | Our Skill | Established Practice | Gap |
|--------|----------|---------------------|-----|
| Number of alternatives | 2-3 | Varies (2-8+ depending on context) | Adequate for our context |
| Constraint identification | "Distinguish actual from assumed constraints" | Toyota: map feasible regions explicitly | Good -- our framing is correct |
| Comparison structure | Table against constraints | Toyota: intersection of feasible sets; GV: user testing | Our table is simpler but appropriate |
| Decision documentation | "Document WHY others were rejected" | Set-based: keep alternatives alive until proven infeasible | We kill alternatives too early; consider noting "under what conditions would a rejected approach become preferred?" |
| Genuine difference | "Not variants of the same idea" | GV: different people sketch independently | Hard to enforce with a single AI -- it tends to generate variations, not genuinely different approaches |

### What Would Make It More Rigorous

1. **Add constraint questioning.** Before generating approaches, explicitly challenge: "Is each constraint real? What happens if we relax it?" This is the most valuable part of Toyota's approach -- feasibility before commitment.

2. **Define "genuinely different."** Currently we say "not variants of the same idea" but don't define the threshold. Better: each approach should use a different core data structure, different decomposition strategy, or different integration pattern. Name the dimension of difference.

3. **Add "conditions for reconsideration."** For rejected approaches, note: "This approach would be better if [specific condition changed]." This preserves decision context for future conversations (which is exactly why we have the scratchpad).

4. **Consider a simpler "spike" mode.** Not every decision needs 2-3 full approaches. Sometimes you just need "is this feasible?" Add a lighter-weight variant: "Spike: can this work? [yes/no/maybe, with evidence]."

**Certainty level: HIGH** that 2-3 is the right number. **HIGH** that the current structure is solid. **MEDIUM** on whether the alternatives generated will be genuinely different (the AI diversity problem).

---

## 5. The "Attractor Escape" Concept

### What We Planned

From WORKFLOW_PATTERNS.md draft, under "Ambient Patterns":
> Watch for Claude's default patterns:
> - Over-abstracting (creating frameworks when a function would do)
> - Adding error handling for impossible cases
> - Over-engineering for hypothetical future requirements
> - Summarizing what it just did
> Counter: Ask "what's simplest?" and "is this real or hypothetical?"

### What Research Shows

**Cognitive biases in LLM-assisted development (Zhou et al., 2025):**
This study identified that LLM adoption transforms programming from "solution-generative" to "solution-evaluative" -- developers spend more time evaluating AI suggestions than writing code. This shift amplifies specific biases:

- **Anchoring bias:** Developers anchor on the first AI-generated solution. One developer "repeatedly duplicated the same cell when encountering errors, attributing the issue to the environment" rather than reconsidering the approach. Strong models show consistent vulnerability to anchoring, even when explicitly told to ignore anchor values.
- **Automation bias:** Over-trust in AI outputs. Adding "productive friction" (requiring explicit confirmation before integrating generated code) helps.
- **Confirmation bias:** Developers seek evidence that the AI solution works rather than evidence it doesn't.
- **Sycophancy:** LLMs tend to agree with or defer to user suggestions, reinforcing whatever direction the human has already chosen.

**LLM anchoring research (2024-2025):**
LLMs show anchoring effects at rates of 17.8-57.3% across different bias types. Attempted mitigations (Chain-of-Thought, explicit "ignore the anchor" instructions, reflection prompts) showed limited effectiveness against "expert" anchoring. The anchor doesn't need to be correct to be influential -- it just needs to be present.

**LLM default behavior patterns:**
Research shows that what we observe from LLMs "is not the model's natural behavior, but the behavior induced by our instructions." LLMs have default inclinations shaped by training data distribution -- they overrepresent common, well-documented, Western, and high-frequency patterns.

**Debiasing techniques that work (and don't):**
- Chain-of-Thought: improves reasoning accuracy by ~40% but does NOT reliably reduce anchoring
- Self-consistency (multiple reasoning paths, majority vote): improves reliability for ambiguous problems
- Auto-CoT (diverse sampling): clusters questions by type, generates diverse demonstrations, reducing homogeneity
- Explicit debiasing instructions: marginal effect on strong biases like anchoring
- "Productive friction" (forced pause before accepting): effective for automation bias

### Gap Analysis

| Our Pattern | Research Support | Gap |
|------------|-----------------|-----|
| Over-abstracting | Supported -- LLMs default to high-frequency patterns (frameworks are common in training data) | Correct identification, but "ask what's simplest" is a weak counter |
| Error handling for impossible cases | Supported -- automation bias + anchoring on common patterns | Correct |
| Over-engineering | Strongly supported -- Google code review explicitly warns against this | Correct |
| Summarizing output | Supported -- sycophancy/agreeableness bias | Correct but trivial |
| Counter: "what's simplest?" | Partially supported -- explicit instruction helps but doesn't fully overcome anchoring | Too weak as sole counter |

### What Would Make Attractor Escape More Effective

1. **Self-consistency / diverse generation.** Instead of generating one approach and asking "is it too complex?", generate multiple approaches at different complexity levels and compare. This is literally what `/competitive-design` does -- the connection should be explicit.

2. **Concrete antipattern checklist.** Instead of general "watch for over-abstracting," provide specific patterns to check:
   - "Did I create a class where a function would work?" (over-abstraction)
   - "Does this handle errors that can't actually occur given the call sites?" (phantom error handling)
   - "Is this parameterized for one use case?" (premature generalization)
   - "Am I building this because the code needs it or because I've seen it in training data?" (frequency bias)

3. **Productive friction for AI output.** The most research-supported technique: force a pause between generation and acceptance. For Claude Code, this means: after generating code, STOP and evaluate it against the task requirements before presenting it. This is effectively what the Certainty Protocol already does, but at the plan level, not the code level.

4. **Periodically introduce alternative analysis.** Research on anchoring mitigation in coding suggests "periodically introducing alternative code analysis interventions" to break the chain of anchoring. In practice: after every N changes, pause and ask "is there a fundamentally simpler way to achieve what we've built so far?"

5. **Name the attractor basins specifically.** Our list of four patterns is good but should grow based on observed behavior. When Claude exhibits a new default pattern, add it to the list with a concrete counter-question. This makes the escape mechanism empirical rather than theoretical.

**Certainty level: HIGH** that LLM attractor basins are real and well-documented. **HIGH** that our identified patterns are correct. **MEDIUM** that our current counters are sufficient -- they're directionally correct but need structural reinforcement (productive friction, diverse generation, concrete checklists).

---

## Cross-Cutting Findings

### Theme 1: Structured beats open-ended

Across all five topics, the research consistently shows that structured techniques outperform open-ended ones:
- Structured pre-mortems beat open-ended risk brainstorming (Klein)
- Structured assumption checks beat open-ended critique (CIA SATs)
- Structured constraint tables beat open-ended comparison (Toyota)
- Concrete antipattern checklists beat "be careful" instructions (debiasing research)

Our skills are already structured, which is good. The improvements above make them more structured, not less.

### Theme 2: Feedback loops matter

CDD, devil's advocacy, and competitive design are all one-shot -- use them, get output, move on. Calibration research shows that confidence estimates improve with outcome feedback. We should add lightweight post-implementation checks:
- After implementing, did the confidence ratings match reality?
- Did the devil's advocate concerns materialize?
- Did the chosen approach work better than rejected alternatives?

This could be as simple as a note in the scratchpad: "CDD assessment for [task] -- post-implementation: [what actually happened]."

### Theme 3: The AI-specific challenge

All of these techniques were designed for human teams. When applied to a single AI agent:
- Devil's advocacy loses the "genuine dissent" mechanism (Nemeth's core finding)
- Competitive design loses the "different people think differently" diversity
- Confidence calibration loses the "outcome feedback improves calibration" loop (each conversation starts fresh)

The mitigation for all three: **make the structure do the work, not the conviction.** Concrete checklists, specific antipatterns, mandatory steps, diverse generation techniques. The AI can't genuinely disagree with itself, but it can systematically check for specific failure modes.

### Theme 4: Our skills are novel for the AI-agent context

No established framework addresses "how should an AI coding assistant review its own work before implementing?" We're in genuinely new territory. The research provides grounding and technique, but the specific application to AI-conversation workflows is ours to define. This is not a weakness -- it means we're solving a real problem that doesn't yet have canonical solutions.

---

## Specific Improvements to Implement

### `/cdd` Skill

1. Add Step 3.5: **Pre-mortem.** "Assume this implementation failed. What's the most likely reason?"
2. Add Step 6: **Post-implementation note.** "After implementing, note in scratchpad whether confidence ratings matched reality."
3. In Step 3, separate likelihood from impact: "How likely is the assumption to be wrong? How bad is it if it is?"
4. Add assessment criteria to Step 3: assess against (a) understanding of existing code, (b) correctness of approach, (c) edge cases, (d) component interactions.

### `/devils-advocate` Skill

1. Replace Step 2 (Steel-man the opposition) with: **Generate a concrete alternative** that uses different core assumptions. Not "argue against" but "what would you build if starting from different premises?"
2. Add Step 2.5: **Disconfirmation check.** For each assumption, ask "what evidence would DISPROVE this?"
3. Add Step 5.5: **Pre-mortem.** "Assume the current approach was implemented and failed. Describe the failure."
4. Rename the skill concept from "devil's advocate" (which has the performative problem) to something like "challenge analysis" or "structured challenge" -- framing matters.

### `/competitive-design` Skill

1. Add Step 1.5: **Constraint challenge.** "Is each constraint real? What happens if we relax it?"
2. In Step 2, define "genuinely different": each approach should differ in core data structure, decomposition, or integration pattern. Name the dimension of difference.
3. Add Step 4.5: **Conditions for reconsideration.** "Under what changed conditions would a rejected approach become preferred?"
4. Add a lightweight "spike" variant for simple feasibility questions.

### `/review` Skill

1. Add **testability/verifiability** questions to the "deliverability" lens: "Can each phase be verified? What are the acceptance criteria?"
2. Note in the skill that security/performance lenses should be added for production or multi-user deployments.
3. Consider adding "what breaks at scale?" to the "failure" lens.

### Attractor Escape (WORKFLOW_PATTERNS.md)

1. Explicitly connect attractor escape to `/competitive-design` -- generating alternatives IS attractor escape.
2. Replace general warnings with a concrete checklist of antipatterns to check.
3. Add "periodic re-evaluation" as an ambient pattern: after N changes, pause and ask "is there a fundamentally simpler way?"
4. Grow the antipattern list empirically as new patterns are observed.

---

## Summary Assessment

| Component | Grounded? | Current Quality | After Improvements |
|-----------|----------|----------------|-------------------|
| CDD | Yes (decision science, risk management) | Good but thin | Strong methodology |
| Review lenses | Yes (ATAM, Google code review, QAW) | Good selection, one gap | Complete for this project |
| Devil's advocacy | Partially (research shows role-played DA is weak) | At risk of being performative | Strong if restructured around SATs |
| Competitive design | Yes (set-based design, design sprints) | Solid structure | Solid with constraint challenge added |
| Attractor escape | Yes (LLM bias research, cognitive bias literature) | Correct identification, weak counters | Effective with concrete checklists |

**Overall verdict:** These are not feel-good rituals. They map to real methodologies and address real problems. But they're currently Version 1 -- good instincts, thin implementation. The improvements above would make them genuinely rigorous tools. The most important single improvement across all five: **add structured post-implementation feedback** so the tools calibrate over time.

---

## Sources

### Pre-mortem and Decision Science
- [Gary Klein - Premortem](https://www.gary-klein.com/premortem)
- [Psychology Today - The Pre-Mortem Method](https://www.psychologytoday.com/us/blog/seeing-what-others-dont/202101/the-pre-mortem-method)
- [Cornell - The Premortem Technique](https://ecommons.cornell.edu/bitstreams/6f50583c-fc17-4b6d-982c-a2d217e9027c/download)
- [Veinott et al. - Evaluating Effectiveness of PreMortem](https://idl.iscram.org/files/veinott/2010/1049_Veinott_etal2010.pdf)
- [Brier Score Tutorial - Tim van Gelder](https://timvangelder.com/2015/05/18/brier-score-composition-a-mini-tutorial/)
- [LLM Confidence Calibration - Nature](https://www.nature.com/articles/s44355-026-00053-3)

### Architecture Review and Quality Attributes
- [SEI/CMU - ATAM Collection](https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/)
- [ATAM - GeeksforGeeks](https://www.geeksforgeeks.org/software-engineering/architecture-tradeoff-analysis-method-atam/)
- [ATAM - Wikipedia](https://en.wikipedia.org/wiki/Architecture_tradeoff_analysis_method)
- [SEI - Quality Attribute Workshops](https://www.sei.cmu.edu/library/quality-attribute-workshops-qaws-third-edition/)
- [Google eng-practices - What to Look For](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- [Google eng-practices - Code Review Standard](https://google.github.io/eng-practices/review/reviewer/standard.html)
- [C4 Model](https://c4model.com/)
- [Software Architecture Quality Attributes](https://syndicode.com/blog/12-software-architecture-quality-attributes/)
- [ARDURA - Architecture Review Checklist](https://ardura.consulting/blog/software-architecture-review-checklist/)

### Devil's Advocacy and Structured Analytic Techniques
- [Nemeth (2001) - Devil's Advocate vs Authentic Dissent](https://onlinelibrary.wiley.com/doi/abs/10.1002/ejsp.58)
- [Schwenk (1990) - DA and DI Meta-Analysis](https://www.sciencedirect.com/science/article/abs/pii/074959789090051A)
- [CIA Tradecraft Primer - Structured Analytic Techniques](https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf)
- [The Decision Lab - Devil's Advocacy](https://thedecisionlab.com/reference-guide/philosophy/devils-advocacy)
- [Genuine vs Contrived Dissent - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0749597802000018)
- [The Tenth Man Rule](https://themindcollection.com/the-tenth-man-rule-devils-advocacy/)
- [Maltego - SATs for Intelligence](https://www.maltego.com/blog/improving-your-intelligence-analysis-with-structured-analytic-techniques/)

### Design Alternatives and Competitive Design
- [Toyota Set-Based Concurrent Engineering - MIT Sloan](https://sloanreview.mit.edu/article/toyotas-principles-of-setbased-concurrent-engineering/)
- [Set-Based Design Review - Cambridge](https://www.cambridge.org/core/journals/design-science/article/setbased-design-a-review-and-new-directions/DD708BAB57193C6635CA85C7508FE82E)
- [Google Ventures Design Sprint](https://www.gv.com/sprint/)
- [Design Sprint Kit](https://designsprintkit.withgoogle.com/)
- [Spikes vs PoCs vs Prototypes](https://medium.com/studio-zero/spikes-pocs-prototypes-and-the-mvp-5cdffa1b7367)
- [Architectural Spikes in Agile](https://agilemania.com/what-is-a-spike-in-agile)

### LLM Biases and Attractor Escape
- [Zhou et al. - Cognitive Biases in LLM-Assisted Software Development](https://arxiv.org/html/2601.08045v1)
- [Anchoring Bias in LLMs - Springer](https://link.springer.com/article/10.1007/s42001-025-00435-2)
- [Prompt Debiasing - Learn Prompting](https://learnprompting.org/docs/reliability/debiasing)
- [Debiasing LLMs Survey - Springer](https://link.springer.com/article/10.1007/s10462-024-10896-y)
- [Self-Consistency Prompting](https://www.promptingguide.ai/techniques/consistency)
- [LLM Cognitive Bias - USC Guide](https://libguides.usc.edu/blogs/USC-AI-Beat/bias-patterns-llms)

### Design Reviews and Risk Assessment
- [PDR - DAU](https://aaf.dau.edu/aaf/mca/pdr/)
- [CDR - AcqNotes](https://acqnotes.com/acqnote/acquisitions/critical-design-review)
- [Risk Assessment Matrix - Atlassian](https://www.atlassian.com/work-management/project-management/risk-matrix)
- [TDD - Wikipedia](https://en.wikipedia.org/wiki/Test-driven_development)
