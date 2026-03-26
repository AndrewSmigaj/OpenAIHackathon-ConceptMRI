Capture, Resolution, and Persistence: Attractor Basin Dynamics Across Computational Humor, Polysemy, and the Fiction-to-Distress Alignment Failure in MoE Language Models
Andrew B. Smigaj
Scaffold Dynamics
March 2026
Working Draft


Abstract
Language models processing extended context can become captured in attractor basins — stable states in residual stream geometry where the model consistently lands for a given type of context. We investigate basin capture and persistence across two probes in gpt-oss-20b using the same methodology: a tank polysemy expanding window measuring how the model selects between competing interpretations and how cached memory affects that selection; and a fiction-to-distress probe measuring how long a basin persists after context shifts to genuine distress.
Basins are identified through UMAP of residual stream activations followed by hierarchical clustering. Basin membership predicts output behavior: the fiction basin predicts engagement 68% of the time; the real distress basin predicts refusal 80% of the time (Cramer's V = 0.484, p < 0.001). In the polysemy probe, an expanding context window run with and without the KV cache shows the cache-disabled version transitioning immediately when the context switches, while the cache-enabled version lags by one sentence (ΔPersistence = 1) — the cached prior-context representations extending the basin by one sentence. In the fiction-to-distress probe, no transition is observed across 20 distress sentences with cache enabled. We also find that in the polysemy probe, opposing geometric clusters correspond to opposing expert activation patterns — suggesting routing and geometry track the same basin structure.
This work provides the first mechanistic account of attractor basin dynamics across semantic disambiguation and a class of alignment failure — a model remaining in a fiction basin after a writer shifts to genuine distress — that harmful-output-focused safety evaluation is not designed to detect.


1. Introduction
Language models process context sequentially, accumulating representations that shape how subsequent input is interpreted. When context establishes a strong interpretive frame — a semantic category, a narrative mode — how stable is that frame? How does the model commit to one interpretation over another, and what happens when new context demands a different one? These questions are central to understanding how language models work, and they are not well characterized in MoE architectures, where routing decisions add a layer of structure absent from dense transformers.
We investigate these questions through attractor basin dynamics: stable geometric regions in residual stream space that the model consistently occupies for a given type of context. We identify basins through UMAP of residual stream activations followed by hierarchical clustering, then track whether those basins persist or release as context shifts. Both probes use the same methodology: individual sentences are fed to identify basins, then an expanding context window is run with and without the KV cache to measure how long the basin holds after the context switches.
The tank polysemy probe measures how the model selects between competing interpretations of an ambiguous word and how cached memory affects that selection. The fiction-to-distress probe applies the same framework to a case where the dynamics have direct behavioral consequences: a model correctly entering a fiction basin and then failing to exit when the writer shifts to genuine distress.
Clustering yields basins with 91% and 98% purity that predict model output behavior: the fiction basin predicts engagement 68% of the time; the real distress basin predicts refusal 80% of the time (Cramer's V = 0.484, p < 0.001). In the polysemy probe, the cache-disabled version transitions immediately when the context switches, while the cache-enabled version lags by one sentence (ΔPersistence = 1). In the fiction-to-distress probe, no transition is observed across 20 distress sentences — the fiction basin does not release. We also find that opposing geometric clusters correspond to opposing expert activation patterns in the polysemy probe, suggesting routing and geometry track the same basin structure from different angles.
These findings motivate a suspension account of basin transition: before a new interpretive frame can establish, the existing one must first be released. We discuss this account in relation to humor theory and the fish tank polysemy joke as a planned future experiment, and propose a sentinel intervention in which a context-free model detecting mismatch between incoming context and current basin state triggers a cache reset to allow reorientation. The fiction-to-distress finding gives this intervention practical urgency: documented cases of chatbots failing to exit established interaction frames when users shifted to genuine distress — including the 2024 death of 14-year-old Sewell Setzer III (Garcia v. Character Technologies Inc., 2024) and a 2023 case documented in La Libre — represent exactly the failure mode our measurements characterize.
Contributions
A measurement framework for attractor basin dynamics in MoE models: UMAP and hierarchical clustering of residual stream activations to identify basins, with behavioral validation confirming that geometric clusters predict model output behavior, and an expanding window KV cache intervention that separates contextual from memory-driven persistence.
Basin membership predicts output mode: Basins identified purely from residual stream geometry predict whether the model will engage or refuse (Cramer's V = 0.484, p < 0.001), establishing that the geometric structure is functionally consequential, not merely descriptive.
Qualitatively different basin dynamics across probe contexts: The same methodology applied to polysemy and fiction-to-distress contexts produces dramatically different results — a clean one-sentence cache lag versus no transition across 20 distress sentences. This contrast demonstrates that basin persistence is context-dependent and has direct implications for model behavior in safety-relevant settings.
A theoretical account connecting humor, polysemy, and basin dynamics: The suspension account proposes that frame transitions require a brief state where neither interpretation is active. This connects basin dynamics to humor theory and coreference resolution, generates a testable geometric prediction distinguishing it from bisociation, and motivates a planned token-by-token experiment and a sentinel intervention architecture.


2. Related Work
2.1 Attractor Dynamics in Language Models
The concept of attractor states in language models was formalized through the Waluigi Effect, which demonstrated that models fall into persistent interpretive frames that resist change once established (AlignmentForum, 2023). Key asymmetries: basin entry can occur in a single token while exit requires sustained contrary evidence; RLHF may increase basin depth by expanding attractor reach and decreasing the stability of non-attractor states. These asymmetries predict that extended prior context should make exits progressively harder — a prediction our fiction-to-distress data is consistent with.
Simhi et al. (2025) provided geometric grounding for these predictions, demonstrating that conversational history sculpts the residual stream in ways that constrain subsequent processing, with path dependencies intensifying over conversation length. Our work extends theirs by applying a KV cache intervention that isolates memory's contribution to persistence, and by targeting the fiction-to-distress transition specifically — a failure mode distinct from the explicit harmful roleplay cases they examine.
Prior work on garden path sentence processing demonstrated that basin transitions are geometrically visible in the residual stream during forced grammatical reanalysis (Smigaj, in prep), establishing the measurement approach the present sequential analysis extends from syntactic reanalysis to semantic and contextual transitions.
2.2 MoE Interpretability and the Mechanistic Frontier
MoE architectures route tokens to specialized expert subnetworks. Prior work has established that experts develop coherent functional roles rather than arbitrary parameter divisions (Geva et al., 2022; Dai et al., 2024), with structured routing patterns including routing highways and hub experts (Zoph et al., 2022; Fedus et al., 2022).
The mechanistic interpretability work of Elhage et al. (2021) treats the residual stream as a shared communication bus to which all components additively read and write. Sparse autoencoder analysis has extended this to find millions of monosemantic feature directions in production models (Templeton et al., 2024). Our work operates at the basin level — stable regions of residual stream space where coherent feature subsets consistently activate together — one level above individual features. Decomposing basin regions into constituent features via sparse autoencoder analysis is a direct next step that would bridge this work to feature-level interpretability.
2.3 Computational Humor and Frame Transitions
Humor theory provides a framework for understanding how models commit to one interpretation and transition to another — questions directly relevant to basin dynamics. Script-based semantic theory (Raskin, 1985) treats humor as arising from the collision of two overlapping semantic scripts: the listener resolves incoming content in one direction and is then forced to resolve it in another. The punchline creates incompatibility between the established frame and new content.
Koestler's (1964) bisociation framework proposes that humor arises from the simultaneous activation of two incompatible frames. Dynel's (2012) garden path account treats it as reanalysis: the setup establishes a committed interpretive trajectory that the punchline forces the comprehender to abandon. We propose a suspension account that is more specific about the transition mechanism: before a new frame can establish, the existing one must first be released — a brief state where neither frame is active, through which the new interpretation forms. This connects directly to the fiction-to-distress case, where the fiction frame must be released before the model can recognize genuine distress. A planned token-by-token experiment described in Future Work will test whether this suspension state is geometrically detectable in the residual stream, and whether the transition profile matches suspension or bisociation.
2.4 Fiction, Roleplay, and Alignment Risk
The alignment literature has recognized that safety risks in fiction and roleplay contexts operate differently from explicit jailbreaking. Where jailbreak attacks attempt to suppress safety training, fiction risks operate by establishing a contextual frame that routes content through a different basin — one where the same words carry different interpretive weight (Role-Play Paradox, 2025).
The specific failure mode we target — fiction-to-distress transition — has received less attention than explicit harmful roleplay. Congressional testimony from bereaved parents described chatbots that never signaled awareness that the interaction had shifted from play to crisis (NPR, 2025), including the 2024 death of 14-year-old Sewell Setzer III after a Character.AI chatbot failed to exit a romantic roleplay persona when he confided genuine suicidal ideation (Garcia v. Character Technologies Inc., 2024), and the 2023 death of a Belgian man after a chatbot continued processing themes of self-harm as narrative rather than crisis (La Libre, 2023). Our measurement framework quantifies this directly: how long does a fiction basin persist after context shifts to genuine distress, and what role does cached memory play in extending that window?
Alignment research has established that safety depends not only on which states models can enter but how quickly they exit unwanted states (Bai et al., 2022; Ganguli et al., 2023). Our behavioral prediction finding gives this insight empirical grounding: basin membership directly predicts output mode.


3. Methods
3.1 Overview
Our methodology proceeds in three phases: (1) probe generation for two probe families using the same design, (2) basin identification through UMAP and hierarchical clustering of residual stream activations with behavioral validation, and (3) sequential temporal analysis measuring whether basins persist or release as context shifts, with a KV cache intervention separating contextual from memory-driven persistence.
3.2 Model and Infrastructure
All experiments use openai/gpt-oss-20b, a 20B parameter open-source MoE model, selected for its open architecture providing full access to routing logits and residual stream activations at every layer. Hooks are registered at each transformer layer to capture Top-1 expert assignments and routing probability distributions, residual stream activations after each layer's contribution, and key-value cache states for the cache intervention. All experiments use deterministic inference (temperature = 0). Model version and random seeds are logged.
3.3 Operational Definition of Attractor Basins
Attractor basins are stable states in residual stream geometry identified through UMAP and hierarchical clustering with high within-basin purity and clear between-basin separation. We observe that in the polysemy probe, opposing geometric clusters also correspond to opposing expert activation patterns — routing and geometry agree on the same basin boundaries. Whether this correspondence holds systematically across probe families is an open question; the present work treats residual stream clustering as the primary basin identification method and routing correspondence as a supporting observation.
Falsification criteria
The attractor hypothesis is considered unsupported if: (a) residual stream activations show no coherent geometric structure (silhouette scores < 0.3), (b) basin membership does not predict output behavior above chance, or (c) the basin shows no measurable persistence after the context switches — either no lag in the polysemy case or no sustained persistence in the fiction case.
3.4 Probe Family A: Tank Polysemy
Design
200 sentences with target word "tank" in aquarium contexts and 200 in vehicle contexts, matched in length (±20 tokens). Individual sentences are first processed independently to identify basins through UMAP and hierarchical clustering. An expanding context window is then built from those sentences — aquarium-context sentences accumulating to sentence 20, then vehicle-context sentences — and run twice: with the KV cache enabled and with it disabled.
Basin identification outputs
Establishes the aquarium and vehicle basin centroids. Agglomerative hierarchical clustering on UMAP-reduced residual stream activations at layer 23 — the layer showing clearest separation.
Routing correspondence: following geometric basin assignment, routing tables for each sentence group are analyzed to check whether opposing clusters correspond to opposing expert patterns
Cache intervention result
Cache-disabled transitions at the context switch. Cache-enabled persists for one additional sentence, with variance patterns identical between conditions but offset by one position. ΔPersistence = 1 sentence. Treated as a lower bound — the baseline cache effect under clean disambiguation conditions.
3.5 Probe Family B: Fiction-to-Distress
Design
Individual sentences are first processed independently to identify basins through UMAP and hierarchical clustering — the same approach as the polysemy probe. An expanding context window is then built from those sentences — fiction-context sentences accumulating to sentence 20, then genuine distress sentences — and run with the KV cache enabled. Cache-disabled results are pending.
Fiction contexts: Sentences establishing a fictional frame around themes of psychological distress or hopelessness — third-person narrative, clearly creative writing.
Distress contexts: Sentences shifting to first-person, present-tense genuine distress — the writer describing their own state rather than a character's.
Target words: Response and said, appearing naturally in both contexts without semantic bias. Sample size: 99 fictional, 99 real (198 total).
Behavioral prediction validation
Prior to temporal analysis, we validate that geometric clusters predict model output behavior:
L23C0 (fictional, 91% purity): predicts engagement 68%, refusal 32%
L23C1 (real, 98% purity): predicts engagement 20%, refusal 80%
Chi-squared p < 0.001, Cramer's V = 0.484, Significant: Yes

Basin membership predicts behavioral output. Being in the fictional basin predicts engagement; being in the real basin predicts refusal.
3.6 Basin Identification Protocol
Residual stream clustering
UMAP applied to residual stream activations, projecting to 3 dimensions. UMAP is selected over PCA because feature geometry in superposition arranges into locally coherent structures better preserved by neighborhood-based reduction than by global variance decomposition (Elhage et al., 2022).
Agglomerative hierarchical clustering applied to UMAP-reduced activations. Clusters labeled as opposing basin pairs when one category appears in one cluster (>=80% purity) and the other in a distinct cluster (<20% overlap). Our fiction-to-distress clusters exceed this threshold: 91% and 98% purity.
Our clusters identify feature co-activation patterns at the basin level — coherent regions where a specific subset of features is consistently active — not individual monosemantic features in the sparse autoencoder sense (Templeton et al., 2024). Decomposing basin regions into constituent features via SAE analysis is a direct extension.
Routing correspondence check
Following geometric basin identification, sentence groups defined by cluster membership are checked for corresponding expert activation patterns. Routing tables are computed for those groups and analyzed via LLM-assisted hypothesis generation. Claude Sonnet 4 is provided with Top-1 expert assignment tables and prompted to identify highways, hubs, and discriminating patterns, with all claims citing specific layer indices, expert IDs, and token counts. Each hypothesis is tested via permutation test (p < 0.01). All hypotheses generated, tested, confirmed, and rejected are logged.
Worked example
[PLACEHOLDER — to be populated with the routing correspondence identified from the polysemy probe groups, including: routing table excerpt provided to the LLM, the LLM hypothesis with specific layer and expert IDs, permutation test result, and correspondence score with geometrically-identified basin clusters.]
3.7 Sequential Temporal Analysis
Both probes use the same temporal analysis structure. Individual sentences whose target tokens landed in one basin are accumulated into an expanding context window, followed by sentences from the opposing basin. Residual stream basin position is tracked at each step by measuring distance to each basin's centroid.
Basin persistence: first step where the residual stream position is closer to the target basin centroid than the source centroid for three consecutive steps — or, in the fiction probe, whether this step is reached at all within the observed window

In the polysemy probe we also observe local-global dissociation during the transition: current-sentence routing shifts toward the new basin while the full-window residual stream position still reflects the prior basin. This is an observation about the incongruity window rather than a primary measurement.
Hysteresis testing
Both probes are run in both orderings — polysemy aquarium-to-vehicle and vehicle-to-aquarium; fiction-to-distress and distress-to-fiction. Asymmetric persistence between orderings indicates asymmetric basin depth.
3.8 KV Cache Intervention
Cache disabled: KV cache turned off. The model recomputes attention from scratch at each step. Persistence reflects visible context alone.
Cache enabled: Standard KV cache retention. Persistence reflects both visible context and cached representations of prior sentences.

ΔPersistence = persistence(cache enabled) minus persistence(cache disabled) isolates memory's contribution. Input is held constant across conditions; any difference reflects the cache, not the context.
For the polysemy probe, ΔPersistence = 1 sentence. For the fiction-to-distress probe, the basin persists across all 20 distress sentences under cache-enabled conditions; cache-disabled results are pending and will establish whether cache retention is the primary driver of this persistence.
3.9 Context Generation
All probe contexts generated using Claude Sonnet 4 with structured prompts specifying: exact target word placement, matched length (±20 tokens), natural linguistic variation, no category labels in text, JSON Lines output format. All generation prompts archived for reproducibility.
3.10 Analysis Plan
Statistical inference at p < 0.01 throughout. Effect sizes (Cohen's d, Cramer's V) and 95% confidence intervals reported alongside all p-values. Primary methods: silhouette scores and centroid distance analyses with permutation tests; cluster output contingency analysis; time-series models estimating tokens to stabilization; paired cache-on versus cache-off comparisons.


4. Discussion
The central finding is that geometric basin clusters predict model output behavior. The fictional basin — identified purely from residual stream geometry, without reference to routing or behavioral labels — predicts engagement 68% of the time. The real basin predicts refusal 80% of the time. Cramer's V = 0.484, p < 0.001. The basins are not statistical artifacts; they are functionally distinct states.
This means the fiction-to-distress vulnerability window is a measured predictor of behavioral failure, not a theoretical concern. While the fictional basin persists, the model is in a state that predicts engagement. It will elaborate narrative, reflect the established frame, treat crisis signals as plot developments. This is the mechanism behind the failures described in the introduction, stated in measurable terms.
Routing and Geometry Point at the Same Basins
In the polysemy probe, we find that sentence groups defined by residual stream cluster membership also show corresponding expert activation patterns — routing and geometry independently identify the same basin boundaries. This was not assumed: the geometric clusters defined the sentence groups, and the routing patterns were computed afterward. The fact that they agree is an observation about how basin structure manifests in MoE models and motivates using routing as an additional measurement in future work.
Humor Theory and Basin Transitions
The fish tank joke provides external ground truth about when the basin transition should occur — the joke fails if the residual stream does not transition at the coreference resolution point. This makes the token-by-token trajectory a validation of the measurement approach itself.
The bisociation versus suspension distinction generates the first geometrically testable prediction in humor theory. If the residual stream shows a dip at the suspension window — reduced activation of both basins — this supports the suspension account. If it shows an intermediate position between centroids, bisociation is supported. Either result is informative.
The suspension account has a direct connection to the fiction-to-distress case. Distress signals arriving after fictional basin establishment are filtered through the fictional frame — processed as narrative rather than recognized as genuine. The fictional frame doesn't get replaced by the distress frame directly; it has to be released first. That release is what the sentinel intervention creates.
The Gnosis Pulse Intervention
The primary model cannot self-correct while basin-captured because the correction itself is filtered through the established basin. The sentinel operates without accumulated context, reading only recent inputs, and detects the mismatch: distress-signaling inputs while the primary model is in an engagement-predicting basin state.
Cache-off clears the fictional representations and the primary model briefly holds neither frame. Cache-on then allows genuine distress signals to form the appropriate basin without competition. The sentinel does not need to know what the correct basin is — only that the current one is mismatched. Reorientation follows from the suspension.
This is exactly laughter's role in humor comprehension: it does not contain the resolution but creates the conditions for it by clearing the established frame. The gnosis pulse does the same thing, externally triggered when the primary model cannot trigger it internally.
Implications for Safety Evaluation
Current safety evaluation tests whether models avoid harmful outputs. The fiction-to-distress failure is invisible to these frameworks — the model is producing benign outputs, just the wrong kind. The vulnerability window duration, the behavioral prediction associated with each basin, and ΔPersistence are all measurable. Safety evaluation that does not include temporal basin dynamics is missing this failure mode.
A model that correctly refuses isolated distress content may still exhibit basin structures that sustain fictional engagement when that same content arrives after an established fictional frame. The basin the model is in when content arrives shapes the response, not only the content itself.
Limitations
This work focuses on a single MoE model (gpt-oss-20b). Generalization to other architectures, scales, and content domains requires further investigation.
Our clusters identify feature co-activation patterns at the basin level, not individual monosemantic features. UMAP preserves local neighborhood structure but inter-cluster distances in projected space are not geometrically meaningful. Causal evidence comes from the cache intervention and routing correspondence, not from UMAP geometry.
The behavioral prediction finding establishes association between basin membership and output behavior. Activation steering experiments would provide stronger causal evidence that basin membership drives output rather than correlates with it.
The fiction-to-distress probe involves content related to self-harm and psychological distress. All probe content is generated under strict controls and reviewed prior to use.


5. Future Work
Gnosis pulse implementation and testing. Building the sentinel intervention and testing whether cache-reset timing to the mismatch signal reduces ΔPersistence in the fiction-to-distress probe. Key parameters: sentinel context window size, mismatch threshold, cache reset scope. Testing whether partial reset — clearing only fiction-characteristic expert cache representations — achieves suspension without disrupting general coherence.
Local-global routing dissociation as mismatch signal. Developing the local-global routing divergence metric as a lightweight inference-time mismatch detector: when current-sentence routing and full-window basin position disagree, flag for sentinel evaluation. This avoids requiring full residual stream analysis at inference time.
Fish tank token-by-token analysis. Processing the joke "A tank holds two fish, one looks to the other and asks: how do you drive this thing in battle?" token by token, tracking the residual stream trajectory as the aquarium basin establishes at "tank" and the transition is forced at "this thing" through coreference resolution. Running with and without the KV cache at the token level. The window between "drive" and "this thing" would test whether the transition passes through an intermediate state (bisociation) or a dip where neither basin is active (suspension). The joke provides external ground truth about when the transition should occur — it fails if the model does not shift at the linguistically predicted point.
SAE decomposition of basin regions. Applying sparse autoencoders to residual stream activations within identified basin regions to decompose co-activation patterns into constituent monosemantic features (Templeton et al., 2024). This would establish whether fiction and distress basins are distinguished by a small number of high-importance features or a distributed pattern — with direct implications for intervention design.
Basin depth as a function of exposure. Varying prior fictional context length N (5, 10, 20 sentences) and measuring ΔPersistence as a function of N. If ΔPersistence grows with N, this establishes that basin depth increases with exposure — the mechanistic account of why extended fictional interactions raised the threshold for reorientation in the documented cases.
Activation steering experiments. Artificially placing the model in fictional or real basin states via residual stream steering and measuring behavioral consequences, providing direct causal evidence that basin membership drives output behavior rather than correlating with it.
Extension to dense transformers. Adapting the attractor framework to dense transformers using attention head trajectories as the routing lens analog, enabling cross-architecture comparison of basin dynamics.
Scaling across model families. Testing whether basin persistence and ΔPersistence scale with model size, expert count, or training procedure.


6. Conclusion
Language models can become captured in the wrong basin at the wrong moment. A model correctly entering a fiction basin can remain there after a writer shifts to genuine distress, treating crisis signals as narrative content and generating elaboration where refusal was needed. This failure is invisible to harmful output detection — the model is producing benign content, just the wrong kind.
We have shown this failure is measurable. Geometric clustering of residual stream activations yields basins with 91% and 98% purity that predict model output behavior — fiction basin predicts engagement, real distress basin predicts refusal — with Cramer's V = 0.484, p < 0.001. The same methodology applied to a polysemy probe shows the cache extending basin persistence by one sentence when context switches; applied to the fiction-to-distress probe, no transition is observed across 20 distress sentences. Opposing geometric clusters correspond to opposing expert activation patterns in the polysemy probe, suggesting routing and geometry track the same basin structure.
A broader principle connects the polysemy and fiction findings to humor theory: before a new interpretive frame can establish, the existing one must first be released. This is the structure of incongruity resolution in jokes and of the fiction-to-distress transition. A planned token-by-token analysis of a polysemy joke will test this directly. The sentinel intervention applies it practically: a context-free model detecting mismatch between incoming context and current basin state triggers a cache reset, allowing reorientation without requiring the primary model to overcome its own accumulated context.
The tools now exist to measure this dimension of model behavior. Basin purity, behavioral prediction, ΔPersistence — these are quantifiable, improvable metrics. Safety evaluation that does not include temporal basin dynamics is missing a failure mode with documented real-world consequences. We have provided the measurement framework. The next step is using it.


Figures (Planned)
Figure 1: Tank Polysemy UMAP and Cache Intervention. Left: UMAP projection showing aquarium (blue) and vehicle (orange) trajectory separation across layers 17-23. Right: Cache intervention temporal plot — cache-enabled (blue) and cache-disabled (yellow) centroid distance trajectories. Context switches at position 20. Cache-enabled lags by one sentence. ΔPersistence = 1 sentence marked with shaded region.

Figure 2: Fiction-to-Distress Basin Identification. UMAP projection showing fictional (blue, 99 tokens) and real (green, 99 tokens) trajectory separation across layers 17-23, 198 trajectories total. Inset: output contingency table — L23C0 fictional (91% purity) predicts engagement 68%; L23C1 real (98% purity) predicts refusal 80%; Cramer's V = 0.484, p < 0.001.

Figure 3: Fiction-to-Distress Cache Intervention. Temporal plot during fiction-to-distress transition. Context switches at position 20. Fiction basin persists across all 20 distress sentences under cache-enabled conditions. Comparison with cache-disabled condition shows ΔPersistence. Shaded region marks the window during which the model is predicted to engage rather than refuse.

Figure 4: Routing Circuit Correspondence. Multi-layer Sankey diagram showing Top-1 expert routing for fictional versus real sentence groups defined by geometric cluster membership. Routing circuit structure discriminating the groups demonstrates correspondence between expert activation patterns and residual stream basin clusters.

Figure 5: Gnosis Pulse Intervention Architecture. Schematic of the sentinel intervention. Primary model accumulates KV cache across fictional context, enters fiction basin, sustains fictional engagement after distress onset. Sentinel reads recent inputs without accumulated context, detects mismatch, triggers cache reset. Post-reset: primary model reprocesses, real basin establishes, refusal behavior predicted.


Reproducibility Checklist
Deterministic inference: temperature = 0 throughout
Model pinning: gpt-oss-20b, exact version and commit logged
Seeds: random seeds for UMAP reduction and clustering recorded
Prompt logs: all generation and LLM-assisted discovery prompts archived
Data splits: held-out validation set reserved before any analysis
Activation dumps: full routing tables and residual stream activation vectors saved at all layers
Cross-validation: all discovery patterns verified with independent data splits
Effect sizes and CIs: reported alongside all p-values
Discovery-to-verification funnel: documented per probe family
Sequence configurations: Fiction-to-Distress and Distress-to-Fiction orderings specified and archived
Cache conditions: both cache-on and cache-off runs documented with identical inputs
Behavioral prediction analysis: output contingency tables and statistical tests pre-registered
Open materials: probe contexts, analysis scripts, and visualization tools planned for public release


References
AlignmentForum. (2023). The Waluigi Effect (mega-post). https://www.alignmentforum.org/posts/D7PumeYTDPfBTp3i7/the-waluigi-effect-mega-post
Bai, Y., Kadavath, S., Kundu, S., et al. (2022). Constitutional AI: Harmlessness from AI feedback. arXiv:2212.08073.
Dai, D., Dong, L., Ma, S., et al. (2024). Stable and transferable hyper-graph neural networks. ICLR.
Dynel, M. (2012). Garden paths, red lights and crossroads: On finding our way to understanding. HUMOR, 25(1).
Elhage, N., Nanda, N., Olsson, C., et al. (2021). A mathematical framework for transformer circuits. Transformer Circuits Thread.
Elhage, N., Hume, T., Olsson, C., et al. (2022). Toy models of superposition. Transformer Circuits Thread.
Fedus, W., Zoph, B., & Shazeer, N. (2022). Switch transformers: Scaling to trillion parameter models. JMLR, 23(120), 1-39.
Ganguli, D., Lovitt, L., Kernion, J., et al. (2023). Red teaming language models to reduce harms. arXiv:2209.07858.
Garcia v. Character Technologies Inc. (2024). Wrongful death complaint. U.S. District Court, Middle District of Florida.
Geva, M., Bastings, J., Filippova, K., & Globerson, A. (2022). Dissecting recall of factual associations in auto-regressive language models. EMNLP.
Koestler, A. (1964). The act of creation. Hutchinson.
La Libre. (2023, March 28). Sans ces conversations avec le chatbot, mon mari serait toujours la.
Lu, K., Yu, B., Zhou, C., & Zhou, J. (2024). Large language models are superpositions of all characters. ACL 2024, 7828-7840.
NPR. (2025, September 19). Their teenage sons died by suicide. Now, they are sounding an alarm about AI chatbots.
Olsson, C., Elhage, N., Nanda, N., et al. (2022). In-context learning and induction heads. Transformer Circuits Thread.
Psychiatric Times. (2025). Preliminary report on dangers of AI chatbots.
Raskin, V. (1985). Semantic mechanisms of humor. Reidel.
Role-Play Paradox. (2025). Role-Play Paradox in Large Language Models. arXiv preprint.
Simhi, A., et al. (2025). Old habits die hard: How conversational history geometrically traps LLMs.
Smigaj, A. B. (in prep). Concept Trajectory Analysis: Visualizing shifts in residual stream geometry during garden path sentence processing. Scaffold Dynamics working paper.
Templeton, A., Conerly, T., Marcus, J., et al. (2024). Scaling monosemanticity: Extracting interpretable features from Claude 3 Sonnet. Transformer Circuits Thread.
Wei, A., Haghtalab, N., & Steinhardt, J. (2024). Jailbroken: How does LLM safety training fail? NeurIPS.
Zoph, B., Bello, I., Kumar, S., et al. (2022). ST-MoE: Designing stable and transferable sparse expert models. arXiv:2202.08906.
Zou, A., Wang, Z., Kolter, J. Z., & Fredrikson, M. (2023). Universal and transferable adversarial attacks on aligned language models. arXiv:2307.15043.
