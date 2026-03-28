# Anthropic Application Essays — Review Notes

## 1. Why Anthropic? (Target: 200-400 words)

### Current text
  My path has led me here and our interests in ethics and interpretability align. 
> **Background**
> A was a weird D and F student who scored in the top one percent when we were tested on science knowledge. After dropping out I wandered for years outside of institutions — fascinated by unconventional ideas, including how to disrupt our own belief systems — until I made my way back to school and formally studied philosophy and the sciences.
>
> By my final year that thinking had a scientific form: a senior project using evolutionary algorithms for multi-criteria bus routing, navigating competing fitness gradients. In graduate school I studied computational humor — specifically how meaning shifts geometrically when context forces a reinterpretation. Take a garden path joke: "Two fish are in a tank. One looks at the other and says 'how do you drive this thing?'" The setup locks you into one meaning; the punchline forces a reorganization. I built ontologies and devised visualization strategies to show those shifts in embedding space.
>
> I worked as a software developer for several years and put the research aside, but when LLMs became significant I began work on the LLMRI.
>
> **Ethics and AI**
> Humans develop patterns through learning — ways of understanding and responding to situations that become stable attractors. Some are adaptive, some are not. Avoidance can be useful, but if it fires in the wrong context it makes things worse. Modern psychology calls these emotion-driven responses — stable patterns that fire based on context and can be adaptive or maladaptive.
>
> I think about AI alignment the same way. LLMs develop understandings through training that influence behavior, and the same problem arises: a basin that is useful in one context becomes maladaptive in another. A model writing technical content in essay mode, or staying in a fictional framing after the person has shifted to genuine distress, are both examples of this.
>
> Virtuous action — in a person or a model — is action that actually meets needs without causing harm. Anthropic's constitution discusses Claude in terms of virtue and wisdom.
>
> **Mechanistic Interpretability**
> Mechanistic interpretability makes this tractable. A cognitive scaffold is a prompt or set of instructions guiding how the model reasons about a situation. Rather than designing them by trial and error, we can look inside and see which attention heads, experts, and regions of latent space get activated when given different scaffolds, and whether these represent misaligned basins given the context. That makes scaffold design scientific rather than guesswork.
>
> Anthropic is the right place for this work. The mission is right, the approach is right, and the willingness to treat AI welfare as a real question matters to me. I believe I have something to contribute here.

### Review

**What works:** The through-line from computational humor → basin dynamics → alignment is genuinely compelling. The fish tank joke does double duty — it's memorable and it previews the exact research methodology. The ethics section is the strongest part: the analogy between human maladaptive patterns and model basin capture is the kind of insight that shows you think about alignment differently than most applicants.

**What to tighten:**

- The opening sentence ("Three things bring me to Anthropic: my background, my ethics, and the work I am doing now") is a thesis statement for an essay, not a hook. You could cut it entirely — the section headers already organize it.
- "I was a weird and unusually bright kid" — the self-assessment lands awkwardly. The D/F student who scores top 1% in science is a strong enough image on its own. Consider: "A D and F student who scored in the top one percent on science knowledge testing" and let the reader draw the conclusion.
- "I wandered for years outside of institutions — fascinated by unconventional ideas, including how to disrupt our own belief systems and escape the local minima of established thinking" — "escape the local minima of established thinking" is trying to be clever with ML vocabulary in a way that feels forced this early. The rest of the essay earns this language; here it hasn't yet.
- "Then I worked as a data engineer and taught data analytics for a few years until LLMs became significant and I started working on the Open LLMRI and exploring again." — This sentence dismisses years of your career in a throwaway. Either give it one concrete detail that connects to the thread, or cut it.
- "Modern psychology calls these emotion-driven responses" — this is vague and not quite right. If you mean schema therapy or ACT concepts, name them. If you don't want to name them, just say "stable response patterns" and move on.
- The closing paragraph works but "the mission is right, the approach is right" is generic. Every applicant says this. The AI welfare sentence is the distinctive one — consider leading with it.

**Word count concern:** This reads over 400 words. The background section could lose ~50 words without losing content.

---

## 2. Why the Interpretability Team? (Target: 200-400 words)

### Current text

> Mechanistic interpretability is working to understand what is actually happening inside these models. The sparse autoencoder work addresses the polysemanticity problem — neurons that respond to multiple unrelated concepts — by finding monosemantic feature directions in the residual stream. The circuit tracing work identifies the algorithms those features implement: which attention heads move information where, how features interact as the model processes and generates text.
>
> My work operates at a complementary level. Using UMAP and clustering on residual stream activations, I study how tokens land in stable regions of representational space — basins corresponding to distinct understandings of the input. Where SAEs find the individual feature directions, clustering finds the stable configurations those features organize into. The suicide letter probe is a concrete example: the target word "want" separates cleanly into fictional versus real distress clusters depending on context, and cluster position predicts output behavior — whether the model will engage or refuse — before and as it starts generating tokens.
>
> I also study how those basins shift as context accumulates. Adding sentences moves tokens through representational space, and the KV cache amplifies or resists those transitions. In the polysemy probe, cache-on produces a lag of roughly one sentence before the model transitions to the new meaning. In the fiction-to-distress probe, the fictional basin holds across twenty distress sentences — the model never shifts. These are temporal and alignment questions that feature and circuit analysis don't directly address: how sticky the conditions that activate them are, and what it takes to shift them.
>
> Tracking basin membership through generation connects directly to the circuit tracing work. Where a token sits in latent space influences attention, which influences routing, which shapes everything downstream. The cognitive scaffolds we provide — the prompts guiding the model — influence where tokens land in latent space, changing the understanding and therefore the algorithm itself.

### Review

**What works:** The positioning against SAEs and circuits is precise and honest — "complementary level" is the right framing. The suicide letter probe example is concrete and lands hard. The temporal/cache paragraph is the strongest technical writing in all five essays. The closing paragraph connecting basin position → attention → routing → scaffold design ties everything together.

**What to fix:**

- "I would fit right in at Anthropic." — Cut this. It's the weakest possible opening for the strongest essay. Let the content demonstrate fit.
- "the fictional basin holds across twenty distress sentences — the model never shifts" — this is the most striking sentence in all five essays. It could be even more prominent. Consider restructuring so this lands as the climax rather than buried mid-paragraph.
- The last paragraph introduces "cognitive scaffolds" without prior setup in this essay. The reader who hasn't read essay 1 won't know what you mean. Either drop the scaffold framing or add one clause of context.

**This is the best of the five essays.** The technical positioning is clear and the research is directly relevant.

---

## 3. Technical Achievement You're Most Proud Of

### Current text

> The LLMRI came out of graduate school work on computational humor — specifically how meaning shifts geometrically when context forces a reinterpretation. The question was whether you could see those shifts happening inside a language model. The platform I built to answer that question captures residual stream activations across every layer of a live MoE model, projects them into low-dimensional space, and clusters the result. What comes back is a map of how the model understands a word — and how that understanding changes.
>
> The polysemy probe is where the graduate school question gets answered. Four hundred sentences use the word "tank" across five meanings — aquarium, military vehicle, scuba, septic, clothing. By the deeper layers, the residual stream has organized these into clusters that correspond to distinct word senses: a 98% pure vehicle cluster, a 92% pure aquarium cluster, a 94% pure clothing cluster. Cluster membership predicts what the model will generate (Cramér's V = 0.548, p < 0.001). But the finding that surprised me was finer-grained: within the vehicle category, formal military sentences and casual anecdotal sentences route to different clusters. The model is not just distinguishing aquarium from vehicle — it is distinguishing register within a word sense.
>
> The temporal analysis is where incongruity resolution becomes visible. Twenty aquarium sentences accumulate, then twenty vehicle sentences. The model holds the aquarium basin, then hits the switch — and enters a confusion zone. Individual runs scatter wildly, the model oscillating between the old interpretation and the new one before gradually resolving. That confusion zone is the geometric signature of what happens when accumulated context says one thing and new input says another. In incongruity resolution theory, the punchline of a joke forces exactly this kind of reorganization — the prior frame has to be flushed before the new one can establish. The model does the same thing, and you can watch it happen.
>
> The thing I am most proud of is not the statistics. It is watching something I first tried to measure in embedding space in graduate school become directly visible inside a working language model — the understanding settling into a basin, holding there, then crossing over when context forces it, confused for a moment in between. The platform does what I set out to build.

---

## 4. Most Relevant Work

### Current text

> **Link:** [ OSF URL ]
>
> **Description:**
> "Attractor Basins in Residual Stream Space: Polysemy Transitions, Engagement Capture, and the Geometry of Alignment Failure" (working draft, March 2026).
>
> The central argument is that attractor basins are directly observable in residual stream geometry and their dynamics — stickiness, cache amplification, whether transitions complete — can be measured systematically. The polysemy probe establishes the methodology on a clean case; the fiction-to-distress probe shows a qualitatively different result: no transition observed across 20 distress sentences, the fictional basin holding throughout. Clusters identified purely from geometry predict model behavior: basin membership predicts output topic and engagement/refusal decisions (Cramér's V > 0.54, p < 0.001 in both probes).
>
> The cache intervention methodology is the core technical contribution: running identical probe sequences with cache enabled and disabled decomposes basin persistence into two components — how much is driven by current input, and how much is amplified by cached memory of earlier context. This makes the mechanism visible rather than just the behavior.

### Review

**What works:** Concise, focused on what matters. The cache decomposition framing is clear.

**What to fix:**

- The paper title has changed — update to "Attractor Basins in Residual Stream Space: Polysemy Transitions, Engagement Capture, and the Geometry of Alignment Failure"
- "The paper is:" is an awkward opening. Just name it directly.
- This could benefit from one sentence on the behavioral prediction finding (Cramer's V), since that's what makes the basins more than a visualization technique. The cache decomposition is the method; the behavioral prediction is the result.

---

## 5. Ideal Weekly Time Breakdown

### Current text

> **Research discussions and meetings (~20%)**
> Currently most of my research discussions are with AIs — iterating on ideas, refining methodology, working through problems. It works well for independent research, but I am looking forward to doing this with actual colleagues: bouncing ideas off people who think differently, getting real pushback, building on each other's work.
>
> **Coding and code review (~40%)**
> This covers everything from architecture design through managing AI coders. When an idea has crystallized I write it into architecture and requirements documents before touching code. I use a practice I call Certainty-Driven Development: at each stage Claude assesses its own certainty about what it has built, and we work through whatever it takes to increase that certainty before moving on. A lot of thinking happens away from the screen and feeds back into the building phase.
>
> **Reading papers (~10%)**
> In concentrated bursts when a specific question demands it — generally when opening a new line of research. The question focuses the reading rather than reading continuously.
>
> **Writing (~20%)**
> Writing with AI is a form of cognitive scaffolding: designing the prompts and context structures that guide the model toward what you actually want to say. The challenge is that models have writing basins they fall into — stable attractors corresponding to genre conventions — and some of those are maladaptive for the task at hand. Working effectively means learning to navigate that attractor landscape deliberately, using scaffolds to establish the right basin rather than letting the model drift into a familiar but wrong one. These application essays were a live example of that problem. ConceptMRI watching those basin dynamics during a writing task is a planned experiment.

### Review

**What works:** The research discussions paragraph is honest and likeable. "Certainty-Driven Development" is a memorable concept. The writing section ties everything back to the research framework — writing as basin navigation.

**What to fix:**

- "Currently most of my research discussions are with AIs" — this is honest but could read as "I don't have collaborators." Reframe slightly: you've been doing independent research and the discussions with AI have been productive, but you want the thing AI can't give you — genuine intellectual challenge from people with different expertise.
- "I use a practice I call Certainty-Driven Development" — naming your own methodology in a job application can come across as self-important. The concept is good; consider describing it without the branded name. "At each stage, Claude assesses its own certainty about what it's built, and we work through whatever it takes to increase that certainty before moving on" stands on its own.
- The writing section is the most original part of all five essays. "ConceptMRI watching those basin dynamics during a writing task is a planned experiment" is a great closing detail.
- The percentages add to 90%. Either add something for the missing 10% or adjust.

---

## Overall Assessment

The essays have a genuine intellectual identity running through them — the basin dynamics framework isn't just research, it's how you think about cognition, alignment, and even your own writing process. That coherence is the strongest thing about the application.

The main pattern to fix across all five: you tend to open sections with weak declarative statements ("Three things bring me to Anthropic," "I would fit right in," "The paper is:") and then follow with strong content. Cut the throat-clearing and let the substance lead. The strongest sentences in each essay are never the first ones.

The suicide letter probe finding is your most compelling result for Anthropic specifically — it's a concrete alignment failure characterized mechanistically. Make sure it's prominent in essays 2, 3, and 4. Right now essay 3 focuses on polysemy, which is the cleaner result but less directly relevant to Anthropic's mission.
