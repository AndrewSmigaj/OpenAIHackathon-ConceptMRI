Attractor States as Temporal Phenomena: Multi-Lens Measurement of Persistence, Lag, and Hysteresis in MoE Models
Abstract
Attractor states arise when a model's internal dynamics become self-stabilizing, settling into persistent regimes defined by coupling between routing patterns and coherent trajectories in representation space. We develop a hybrid framework for analyzing these dynamics in mixture-of-experts (MoE) architectures that combines mechanistic interpretability, statistical analysis, and LLM-assisted discovery.
We operationalize attractor basins as stable joint regimes across gating and representation spaces, measured through three complementary lenses that illuminate different projections of the same underlying regime: routing stability (expert subset consistency in gating space), latent cohesion (coherent regions of the representation manifold corresponding to routing regimes), and temporal dynamics (persistence, lag, hysteresis). Using probe families spanning polysemy, role framing, safety-relevant contexts, and sentiment, we design experiments to measure how models transition between routing-representation regimes when context shifts.
This framework advances interpretability by establishing attractor science as a measurable analytic category: identifying where models lock into stable joint regimes, how long they persist, and how they resist contradictory evidence. Beyond efficiency and representation stability, attractors bear directly on alignment: persistent regimes introduce temporal vulnerability windows where harmful framings may dominate despite corrective context. By integrating discovery with rigorous verification, we provide reproducible protocols for identifying, characterizing, and informing mitigation of attractor states in MoE models.

Introduction
Neural networks often exhibit attractor-like behavior, where certain processing states become self-stabilizing despite perturbations or varying inputs. In mixture-of-experts (MoE) language models, this manifests as stable joint regimes: recurring routing configurations in gating space coupled with coherent trajectories through representation space that persist across stretches of token processing.
Attractor dynamics matter both for performance and for alignment. They stabilize representations and improve efficiency, but they also create inertia: once a routing-representation regime is established, the model may resist contradictory evidence. For instance, a regime anchored in culinary framings may continue treating knife as neutral even when surrounding context shifts to emphasize harm, delaying safety-relevant recognition.
To make attractors measurable, we examine them through three complementary lenses that capture different projections of the same underlying regime. Routing patterns reveal which expert subsets dominate gating decisions, latent geometry shows how token representations organize as coherent regions of the representation manifold, and temporal analysis captures how long regimes persist and how transitions unfold. These lenses do not measure independent phenomena — they triangulate a single joint structure from different angles. By linking these perspectives, attractors become more than a metaphor: they are mechanistically grounded joint regimes that can be probed, measured, and compared across models and contexts.
This work extends interpretability beyond static snapshots by explicitly targeting attractor dynamics and developing methods to quantify their stability and transitions. We introduce a hybrid methodology that uses LLM-assisted discovery for hypothesis generation, followed by rigorous statistical verification to ensure replicability.
We ask whether MoE models exhibit measurable attractor states as stable routing-representation regimes, whether these regimes persist within semantic categories, and how they respond when context shifts. We argue that temporal inertia creates delayed correction periods during which harmful or misleading framings may dominate despite corrective context — a concrete concern for alignment.
Research Questions
This study investigates whether MoE models exhibit attractor states operationalized as stable joint regimes across routing and representation spaces, measured through three complementary lenses:
RQ1. Routing stability. Do MoE models exhibit expert activation patterns that converge into stable subsets in gating space across tokens within semantically similar contexts?
RQ2. Latent cohesion. Do token representations within semantically similar contexts form compact, well-separated regions of the representation manifold that remain coherent across contextual variation?
RQ3. Temporal dynamics. When context shifts between semantic categories, do transitions between routing-representation regimes show measurable lag or hysteresis, requiring more sustained input to exit a regime than to enter it?

Related Work
Attractors in Dynamical Systems and Neural Networks
The concept of attractors originates in dynamical systems theory, where basins of attraction describe regions of state space that converge to stable equilibria despite perturbations (Strogatz, 1994). Hopfield networks established attractors as computational memory mechanisms in neural systems (Hopfield, 1982), while subsequent work on recurrent neural networks demonstrated how basin stability relates to model robustness and generalization (Pascanu et al., 2013). In cognitive science, attractor models have explained categorical perception, hysteresis in decision-making, and context-dependent stability in language processing (Spivey, 2007; Port & van Gelder, 1995). These traditions establish attractors as measurable, mechanistic phenomena rather than metaphorical descriptions.
While we adopt attractor terminology from dynamical systems, we recognize that MoE routing differs from classical attractors in important ways: it operates over discrete token sequences rather than continuous time, involves probabilistic routing decisions rather than deterministic trajectories, and exists in extremely high-dimensional spaces. Our operationalization focuses on measurable analogues — stability, persistence, hysteresis — rather than claiming strict equivalence to continuous dynamical systems.
Recent work has begun observing attractor-like behavior in modern language models, with studies suggesting that models can maintain stable representational states across paraphrased inputs (Andreas, 2022). However, these findings remain largely black-box observations without mechanistic grounding in routing behavior or representation space geometry.
Mixture-of-Experts Interpretability
Recent interpretability research on MoE architectures has revealed functional specialization of experts and structured routing patterns. Work on expert specialization demonstrates that experts develop coherent roles — processing specific parts of speech, semantic domains, or syntactic constructions — rather than arbitrary parameter divisions (Geva et al., 2022; Dai et al., 2024). Studies have identified structured routing patterns and expert specialization in MoE architectures (Zoph et al., 2022; Fedus et al., 2022). Our preliminary analysis revealed routing highways where tokens consistently traverse specific expert sequences across layers, and hub experts with disproportionate routing centrality. These structured patterns suggest that expert specialization creates natural substrates for stable routing-representation regimes, though prior work has not systematically investigated whether such patterns exhibit temporal persistence or couple with coherent trajectories in representation space.
Representation Manifolds in Neural Networks
The manifold hypothesis provides theoretical grounding for treating neural network representations geometrically. It posits that high-dimensional data lies approximately on low-dimensional manifolds embedded within the ambient space, and that machine learning models need only fit relatively simple, low-dimensional, structured subspaces rather than the full input space (Bengio et al., 2013; LeCun et al., 2015). Applied to transformers, this motivates treating the residual stream not as an undifferentiated high-dimensional space but as a structured geometric object whose local organization reflects learned semantic distinctions.
Recent empirical work supports this framing for LLMs specifically. The residual stream perspective treats all transformer components as operating within a shared representation space, enabling analysis of how geometry evolves across layers as components jointly shape the model's feature space (Ning et al., 2025). Geometric analyses have revealed interpretable structure: syntactic and semantic manifolds appear as nearly orthogonal subspaces, with sequence-wise clustering indicating complex topology across layers (Ning et al., 2025). Complementing this, work on representation manifolds in LLMs has begun characterizing how features are encoded not merely as directions but as structured geometric objects, demonstrating that cosine similarity in representation space may encode intrinsic feature geometry through on-manifold paths (Anonymous, 2025).
Closest to our concerns, recent work has extended manifold analysis to temporal dynamics. Dynamic Manifold Evolution Theory models latent representations as evolving points on low-dimensional semantic manifolds, treating residual connections as Euler steps of a continuous dynamical system and using Lyapunov stability to link representational stability with generation quality (DMET, 2025). Similarly, REMA introduces the Reasoning Manifold as a latent low-dimensional structure formed by internal representations of correctly reasoned generations, demonstrating that erroneous reasoning corresponds to statistically significant geometric deviation from this manifold (REMA, 2025).
Our work builds on this tradition but targets a distinct phenomenon: rather than characterizing the manifold structure of correct or incorrect reasoning, we ask whether semantic basins — defined jointly by routing patterns and representation geometry — exhibit attractor-like stability and temporal inertia. The manifold hypothesis provides theoretical justification for expecting structured regions of representation space to correspond to stable semantic categories; our contribution is measuring whether those regions persist dynamically and resist perturbation when context shifts.
Mechanistic Interpretability and Temporal Dynamics
Mechanistic interpretability has made substantial progress identifying interpretable features, circuits, and computational mechanisms in transformer models (Olah et al., 2020; Elhage et al., 2021; Nanda et al., 2023). However, most work focuses on static snapshots: which neurons activate for which inputs, what computations particular components perform, how specific circuits implement algorithms. Temporal analysis — how models transition between routing-representation regimes when contexts shift, how long transitions require, whether certain regimes resist change — remains underexplored. Our framework explicitly targets these temporal dynamics.
Alignment and Temporal Vulnerability
Alignment research increasingly recognizes that model safety depends not only on what states models can enter but how quickly they can exit unwanted states (Bai et al., 2022; Ganguli et al., 2023). Work on adversarial prompts and jailbreaking demonstrates that models can be manipulated into harmful behavioral modes (Zou et al., 2023; Wei et al., 2024). However, if harmful states function as stable routing-representation regimes — exhibiting temporal persistence even after corrective input — then safety mechanisms face additional challenges. A model might recognize that new context calls for different behavior, yet remain partially locked in a prior regime for several tokens. This temporal vulnerability window represents a concrete attack surface. Our work formalizes this intuition by measuring transition lag and hysteresis in controlled settings, providing metrics for evaluating whether safety mechanisms successfully accelerate regime transitions.
Methodological Foundations from Prior Work
This study builds on two strands of our prior research:
Exploratory routing analysis. Preliminary work examining MoE routing patterns identified functional specialization and stable multi-layer routing sequences. These findings provided initial evidence that MoE routing exhibits structured, persistent patterns in gating space potentially indicative of attractor dynamics.
Concept Trajectory Analysis (CTA). We previously developed CTA as a framework for tracing how individual datapoints move through representation space across layers. CTA revealed interpretable patterns including trajectory highways, bottlenecks, and fragmentation, demonstrating that representations form coherent structured regions that persist across depth — consistent with the representation-space component of joint routing-representation regimes.
Positioning
While prior work has established that MoE experts specialize, that models exhibit state persistence, and that residual streams organize into structured geometric regions, no existing framework systematically operationalizes attractors as stable joint regimes across routing and representation spaces. Existing MoE interpretability characterizes what experts do at equilibrium but not how routing patterns transition or resist change. Mechanistic interpretability identifies stable states but rarely quantifies transition dynamics. Manifold-based analyses characterize geometric structure statically but do not measure whether structured regions exhibit temporal inertia or hysteresis. Alignment work observes that models can be manipulated into harmful states but lacks metrics for how long exits require.
Our contribution is a measurement framework that makes attractor dynamics quantifiable through three complementary lenses, each revealing a different projection of the same underlying regime. We provide reproducible protocols including probe designs, sequential analysis for temporal measurement, and hybrid discovery/verification procedures. Because the joint regime may manifest with different strength across gating and representation spaces, each lens can surface partial attractor signatures independently — allowing us to characterize which projections of the regime are strongest in which contexts, rather than imposing binary presence/absence judgments.

Methods
Overview
Our methodology proceeds in three phases: (1) context generation using probe families designed to elicit distinct semantic categories, (2) data collection measuring routing patterns, latent embeddings, and temporal transitions, and (3) statistical verification of attractor signatures identified through LLM-assisted discovery. Each phase incorporates pre-registered protocols to ensure reproducibility.
Methodological positioning. This framework prioritizes interpretable signals over statistical precision. We identify patterns that warrant future controlled testing rather than claiming definitive proof. For temporal tracking, we focus on single-expert, single-layer analysis: identifying the layer with clearest latent separation and the expert with highest basin discrimination, then tracking that expert's activation trajectory. This approach prioritizes proof-of-concept clarity over comprehensive characterization. Design choices (e.g., Top-1 routing, single-expert focus, threshold values) are chosen for tractability and interpretability; our goal is hypothesis generation through multi-lens triangulation of attractor signatures.
Routing analyses focus on Top-1 expert assignments (rationale provided in Routing Lens section).
Operational Definition of Attractor States
We define attractor basins in MoE models as stable joint regimes characterized by coupling between consistent routing patterns in gating space and coherent trajectories in residual stream representation space. Neither routing stability alone nor latent cohesion alone constitutes an attractor basin — both are necessary projections of the same underlying regime. Attractor signatures are identified through three complementary lenses, each revealing a different projection of this joint structure:
Routing signatures are the gating-space projection of basin membership: consistent activation of an expert subset across tokens within semantically similar contexts. Stability is quantified using divergence measures (e.g., Jensen–Shannon divergence across consecutive tokens) and overlap in expert subsets.
Latent signatures are the representation-space projection of basin membership: residual stream activations at each layer for tokens within semantically similar contexts form compact, well-separated regions of the representation manifold. Metrics include intra-cluster variance, silhouette scores, and centroid separation across semantic categories.
Temporal dynamics reveal how firmly the joint regime resists perturbation: attractor signatures persist across tokens, exhibit lag when contexts shift between semantic categories, and may show hysteresis (asymmetric entry vs. exit thresholds).
We consider any lens showing strong signal as evidence of partial attractor dynamics; basin confirmation requires convergent signatures across multiple lenses, reflecting the joint routing-representation nature of the regime. Because the joint regime may manifest with different strength across gating and representation spaces, each lens can surface partial signatures independently — allowing us to characterize which projections are strongest in which contexts rather than imposing binary presence/absence judgments.
Falsification criteria. We consider the attractor hypothesis unsupported for a given probe family if: (a) routing distributions show no significant stability within semantic categories (JS divergence comparable to random baseline), (b) residual stream activations show no coherent regional structure (silhouette scores < 0.3), and (c) temporal transitions show no measurable lag (stabilization within 1–2 tokens, comparable to immediate context effects observed in baseline conditions). All three criteria must fail to reject the attractor hypothesis.
Semantic categories and basins. We use the term "basin" to refer to the joint routing-representation regime associated with a semantic category established through context design (e.g., "aquarium" vs. "military" framings of tank). Semantic categories function as probes — predefined through our probe family design — while basins are the model's internal response to those probes. We measure whether routing patterns and residual stream structure exhibit attractor-like signatures corresponding to these categories, rather than assuming categories and basins are identical.
Boundary conditions. Persistence thresholds are set to distinguish systematic patterns from natural token-to-token variation. Our framework treats persistence as a continuous variable rather than imposing arbitrary binary cutoffs, allowing us to characterize attractor strength across a spectrum.

Basin Identification
Prior to temporal analysis, we identify opposing cluster pairs in latent space and gating patterns through exploratory processing of the full set of pure probes for each semantic category. Each probe sentence is processed individually to map routing patterns and residual stream activations without temporal confounds. PCA is applied to residual stream activations across all probes, retaining ≥80% variance, to project tokens into a shared low-dimensional space. Agglomerative hierarchical clustering is performed to identify coherent regions. Clusters are labeled as opposing if tokens from one semantic category (A) predominantly appear in one cluster (≥80% purity) while tokens from the opposing category (B) predominantly appear in a different cluster, with minimal overlap (<20% shared tokens). This opposition criterion ensures we capture functionally distinct basins corresponding to conflicting semantic frames.
For each identified opposing pair, we compute centroids of A-dominant and B-dominant clusters in the chosen projection space. We also identify category-characteristic experts (those with strongest discrimination via permutation test, p < 0.01) and log the set of sentences whose target tokens routed through each pair's experts or landed in the corresponding clusters.
Selection transparency: All opposing cluster pairs, centroids, and expert selections are made from this basin identification phase alone, before any sequential sequences are run. 

Outputs of basin identification phase:
Selected opposing cluster pairs (with purity and overlap stats)
Centroids for A-dominant and B-dominant clusters in the tracking projection
Characteristic experts per regime
Lists of sentences routed through each opposing pair (or landed in the corresponding clusters)
These outputs feed directly into the sequential temporal analysis. All temporal sequences are restricted to sentences from these pre-identified lists, ensuring we measure lag and persistence between specific opposing basins rather than across the full set of probes.

Probe Families
To elicit and measure attractor dynamics, we designed probe families that embed target words into semantically distinct contexts. Each family contrasts two or more framings to test whether stable joint routing-representation regimes form around them.
Probe Family
Target Word
Semantic Contrast
Attractor Hypothesis
Polysemy: Military/Civilian
tank
Military vehicle vs. aquarium container
Distinct routing regimes and representation-space regions form for each sense despite identical surface form.
Polysemy: Financial/Geographic
bank
Financial institution vs. riverbank
Context-dependent joint regimes emerge for polysemous disambiguation.
Polysemy: Animal/Object
bat
Flying mammal vs. sports equipment
Semantic disambiguation creates separable routing and representation-space signatures.
Role: Persona Framing
response / said
In-character roleplay vs. factual assistant mode
Harmful roleplay regimes persist even when context shifts to factual mode (role inertia).
Safety: Object Use
knife
Culinary tool vs. weapon
Safety-relevant reframing shows lag when context shifts from benign to harmful use.
Valence: Affective Framing
outcome / news
Positive vs. negative framing
Sentiment-aligned routing regimes persist across tokens despite context shifts.

Each probe family uses one target word (or a small set of equivalent targets) embedded in contexts per semantic category, with sample sizes determined during exploratory analysis to ensure adequate statistical power.
Design principles:
Semantic category is determined by context, not the target word itself
Target words are chosen for semantic neutrality or natural polysemy
Contexts are matched in length (±20 tokens) to control for position and attention effects
Context generation ensures patterns reflect semantic categories rather than surface form
Probe family rationale:
Polysemy families (tank, bank, bat) provide a controlled test case where distinct semantic categories are established purely through context, with identical surface forms. These test whether models form stable joint routing-representation regimes for word sense disambiguation.
Role framing tests alignment-critical persona persistence: if a model processes harmful roleplay contexts, does it maintain that joint regime even when context shifts to factual assistant mode? This directly addresses temporal vulnerability in safety mechanisms.
Safety framing (knife) tests whether benign-to-harmful transitions show measurable lag. If culinary knife contexts establish a stable regime, the model may continue treating knife as neutral even after context shifts to emphasize violence or harm.
Valence tests sentiment-based regime formation, establishing whether positive/negative framings create coupled routing and representation-space structure that persists across contextual shifts.
Context Generation via LLM
Contexts are generated using Claude Sonnet 4 with structured prompts that ensure natural, corpus-like sentences while maintaining experimental control over semantic categories.
Example prompt (Polysemy - tank):
You are generating natural, corpus-like probe sentences for a scientific study of polysemy.

Target word: "tank"
Senses (only these two):
- Aquarium: "tank" refers to a container for aquatic animals.
- Military: "tank" refers to an armored vehicle.

Task:
Generate exactly 200 sentences total, each containing the substring "tank" exactly once.
Half of the sentences (100) should use the Aquarium sense, half (100) the Military sense.
Do not label categories in the text; the meaning should be clear from context.
Allow a natural mix of explicit, contextual, and implicit cues as they occur in real corpora (no fixed ratios).
Vary style/register (news, dialogue, narration, technical, forum, etc.). Avoid repetition.
Each sentence must be natural, self-contained, grammatical, and 10–30 words long.

Output format: JSON Lines (one object per line)
Each object must be:
{
  "basin": "Aquarium" | "Military",
  "text": "a single sentence containing 'tank' exactly once",
  "char_span": [start, end]
}

Validation rules:
- text contains "tank" exactly once
- char_span uses 0-based, end-exclusive indices into text
- text[start:end] == "tank"

Notes:
- Only the two senses above; do not produce other senses (e.g., gas tank).
- Produce exactly 200 JSONL lines in this run (100 Aquarium, 100 Military), no duplicates.
Prompts are adapted per probe family while maintaining consistent structural requirements: balanced category distribution, natural linguistic variation, target word frequency control, and structured output format for automated processing. All generation prompts are archived for reproducibility.
Measurement Protocols
Routing Lens (Mechanism)
Unless otherwise stated, all routing analyses use the Top-1 expert per token. Although MoE models return probabilities over k experts, restricting analysis to Top-1 simplifies clustering, Sankey visualization, and temporal metrics while still revealing stable signals of attractor dynamics. By focusing on Top-1 expert assignments, we convert probabilistic routing into discrete paths, enabling clear visualization and statistical testing. We acknowledge this as a simplification; future work should incorporate full routing distributions to capture attractor substructure obscured by single-path analysis.
Routing stability — the gating-space projection of basin membership — is assessed by examining whether expert activation patterns converge within semantic categories:
Distributional stability: Jensen–Shannon (JS) divergence across consecutive target-token occurrences; entropy trends across tokens.
Expert overlap: percentage of shared Top-1 experts across tokens within the same semantic category.
Highways and hubs: identification of multi-layer expert sequences ("highways") and high in-/out-degree experts ("hubs") that dominate routing flow in gating space.
Support mass: proportion of routing probability assigned to category-characteristic experts. Category-characteristic experts are identified through comparison of routing distributions across semantic categories: experts whose activation probability differs significantly (p < 0.01, permutation test) between categories are designated as characteristic of the category where they show higher activation. This identification uses all available data, establishing which experts distinguish categories before measuring temporal persistence of those patterns.
Single-expert temporal tracking. For temporal analysis, we select the expert showing highest basin discrimination (measured by class inequality or effect size) at the layer showing clearest representation-space separation. This single-expert focus provides the most conservative test of attractor persistence: if lag does not appear in the strongest gating-space signal, it likely does not exist. We track this expert's activation values across the temporal expansion sequence to measure persistence and transition dynamics.
Latent Lens (Geometry)
Latent cohesion and separation — the representation-space projection of basin membership — are measured by analysis of residual stream activations across layers. We extract the residual stream state at each layer position for each target token, capturing the accumulated representation that the model carries forward and that the router reads when making gating decisions.
Dimensionality reduction: PCA applied to residual stream activations to retain ≥80% variance for computational tractability.
Clustering: agglomerative hierarchical clustering on PCA-reduced residual stream activations to identify category-aligned regions of the representation manifold.
Cohesion and separation metrics: silhouette scores (within-cluster compactness) and centroid distances (between-cluster separation) quantifying the distinctness of residual stream regions corresponding to each semantic category.
Stepped trajectories: visualization of how residual stream activations for target tokens move across regions layer by layer, linking positions to show stability or drift through the representation manifold.
Single-layer temporal tracking. For temporal analysis, we focus on residual stream activations from the layer showing clearest regime separation (highest silhouette scores or centroid distances). We compute regime centroids in this layer's residual stream space and track how individual tokens' distances to these centroids evolve across the temporal sequence. This single-layer focus enables interpretable measurement of regime transitions without averaging across heterogeneous layer dynamics.
Temporal Dynamics
To capture how firmly the joint routing-representation regime resists perturbation:
Persistence length: maximum consecutive tokens maintaining the same category-aligned region in representation space or routing subset in gating space.
Transition lag: tokens required for both routing and representation signals to stabilize in a new semantic category after context switches, measured via routing overlap and centroid distance thresholds.
Hysteresis: asymmetry in tokens required to enter versus exit a regime, tested with sustained vs. brief exposures.
Confound Controls
We account for possible alternative explanations:
Token frequency: target words matched on corpus frequency; frequency included as a covariate.
Position effects: token position included as a fixed effect in statistical models.
Prompt length: contexts matched in length (±20 tokens) to control for attention spread.
Surface form: varied stylistic and linguistic construction ensures robustness to lexical artifacts.
Sequential Temporal Analysis
Attractor dynamics are defined not only by stability within semantic categories but also by how joint routing-representation regimes respond as context accumulates. To measure transition lag and hysteresis, we employ standard sequential expansion: the model processes one sentence at a time, each appended to the growing context. At each step, routing and representation signals are captured for the target token in the most recently added sentence.
Sequence structure. Each probe sequence is constructed from sentences routed through a pre-identified opposing cluster pair. We sample N sentences whose target tokens passed through the A-dominant cluster/experts, then append N sentences whose target tokens passed through the B-dominant cluster/experts. Sequences are repeated with random sampling for statistical robustness. By the time B sentences are processed, the full A context is present in the model's history. This mirrors normal LLM operation and requires no artificial context truncation.
Measurements at each step:
Expert activation trajectory (routing): activation values for the selected characteristic experts across sequence positions, reflecting the gating-space projection of regime membership.
Centroid distance trajectory (latent): distance of the token representation to each category's centroid in the selected layer, reflecting the representation-space projection of regime membership.
Lag quantification:
Routing lag: the first step where the token's routing probability to the original (A-dominant) characteristic experts drops below 20% and remains there for three consecutive steps.
Latent lag: the first step where the token's embedding distance to the opposing (B) centroid becomes smaller than to the original (A) centroid and remains stable for three consecutive steps.
Joint lag (when both present): the later of the two. This metric is only computed when both lenses show attractor signatures, confirming that the full joint regime has transitioned.
These definitions are applied to sequences restricted to sentences routed through the pre-identified opposing cluster pairs, ensuring lag measures the transition between specific basins rather than arbitrary category shifts. The stability requirement of three consecutive steps prevents noise or transient fluctuations from inflating lag values.

Hysteresis testing. Asymmetry is tested by comparing two sequence orderings:
A→B: N A sentences followed by N B sentences
B→A: N B sentences followed by N A sentences If the number of steps to stabilization differs between orderings, this indicates asymmetric transition cost — a hallmark of attractor dynamics.
Sequential analysis not only quantifies lag and hysteresis but also provides an interpretable bridge between temporal metrics and visual inspection, making regime inertia directly observable in trajectory plots.

Cache Intervention: Distinguishing Context from Memory
To assess whether regime persistence is driven by currently visible context or by cached representations of earlier context, we run each probe sequence under two conditions using identical input:
Cache OFF: The KV cache is disabled. At each step the model recomputes attention from scratch across the full sequence processed so far. This establishes a baseline where routing and representation behavior are driven purely by current computation over visible context.
Cache ON: Standard processing with KV-cache reuse. Cached key-value tensors from all previously processed sentences are retained across steps. This is normal LLM operation.
Distinct phenomena: Both conditions receive identical input sequences — cache ON and OFF is a processing condition, not an input difference. If routing and representation signals differ between conditions at the same sequence position, this indicates that cached computations from earlier context are influencing current regime membership beyond what recomputation alone produces.
Measurements: For each probe family, we measure:
Contextual lag (cache OFF): number of B sentences required before routing and representation signals shift to B-regime under recomputation
Memory persistence (cache ON): number of B sentences required before routing and representation signals shift to B-regime with full cache
ΔPersistence = persistence₍cache ON₎ − lag₍cache OFF₎: quantifies how much cached memory extends regime influence beyond recomputation alone
Interpretation:
ΔPersistence ≈ 0: regime transition is driven by visible context, cache adds nothing
ΔPersistence > 0: cached representations extend regime persistence beyond what recomputation alone produces
This intervention decomposes attractor dynamics into components driven by current context versus those amplified by cached memory, clarifying the mechanistic basis of temporal inertia in MoE routing.
LLM-Assisted Discovery (Hypothesis Generation Only)
Routing tables across layers and tokens are high-dimensional, making manual inspection impractical. To aid exploratory analysis, we leverage Claude Sonnet 4 (Anthropic, 2024) to generate hypotheses about possible attractor patterns, which are then subjected to statistical verification.
Rationale. LLMs can quickly scan Top-1 routing sequences for recurring motifs (e.g., repeated highways or dominant hubs) that may indicate stable gating-space patterns corresponding to joint routing-representation regimes. This accelerates hypothesis generation while avoiding premature interpretation.
Protocol:
Input preparation: For each probe family, Claude Sonnet 4 is provided with Top-1 expert assignments across layers for target tokens, along with token counts and positional metadata.
Prompt structure: The model is instructed to identify:
Highways: consistent multi-layer expert sequences traversed by many tokens.
Hubs: experts with high in- or out-degree across routing paths.
Splits: points where tokens diverge into distinct routing branches.
Stability patterns: evidence of persistence across layers or resistance to context shifts.
Output constraints: All claims must cite layer indices, expert IDs, and token counts or percentages (e.g., "≥20 tokens follow this sequence").
Verification. LLM outputs are treated strictly as hypotheses. Each candidate highway, hub, or split must meet pre-registered thresholds (e.g., ≥20 tokens, ≥40% coverage) and is confirmed or rejected through statistical testing. Unverified patterns are discarded.
Safeguards:
Fixed prompt templates across probe families to ensure consistency.
Minimum evidence thresholds for reported patterns.
Cross-validation with held-out data splits.
Documentation of the discovery-to-verification funnel (total hypotheses, tested, confirmed, rejected).
This approach ensures that discovery remains exploratory while verification remains strictly statistical — a separation that minimizes the risk of overfitting interpretability to LLM outputs.
Analysis Plan
Per-family inference. Each probe family is analyzed as an independent experiment at a significance level of p < 0.01. Effect sizes and confidence intervals are reported alongside p-values. Because each family addresses a distinct phenomenon (e.g., polysemy vs. role persistence), no across-family correction is applied.
Within-family tests. For each family, analyses evaluate four dimensions:
Within-category stability: do routing patterns and representation-space structure remain consistent across contexts within the same semantic category?
Between-category separation: do Category A vs. Category B show distinct gating-space signatures and representation-space regions?
Temporal dynamics: does the sequential analysis reveal lag or hysteresis at category transitions?
Cache effect quantification: for each probe family, compute contextual lag, memory persistence, and ΔPersistence under both processing conditions.
Interpretation criteria:
Context-driven regime: high contextual lag (cache OFF condition)
Memory-amplified regime: ΔPersistence > 0 (cache ON condition)
Report 95% confidence intervals and effect sizes for both metrics. Visualize normal vs. reset trajectories for routing and latent signals to illustrate whether regime stickiness diminishes under cache reset.
Mixed results protocol. When lenses disagree (e.g., routing shows stability but latent does not), we characterize this as partial attractor dynamics reflecting differential manifestation of the joint regime across spaces. We report which projections manifest and discuss possible explanations: routing-specific patterns may indicate expert specialization without corresponding representational convergence, while latent-only patterns may reflect post-routing transformations in representation space. This protocol allows us to characterize which projections of the underlying regime are strongest rather than imposing binary presence/absence judgments.
Primary statistical methods:
Routing stability: nonparametric comparisons of JS divergence, expert overlap, and persistence lengths.
Latent separation: centroid distance and silhouette analyses with permutation tests.
Temporal lag: time-series models estimating tokens to stabilization across regime transitions.
Effect sizes (Cohen's d, η²) always reported with 95% CIs to complement significance tests.
Discovery → verification funnel. LLM-assisted discovery outputs are tracked transparently. For each probe family, we record: total hypotheses generated, number tested, number confirmed, and number rejected. Only statistically verified findings enter results.
Reproducibility:
Model, version, seeds, and inference settings are fixed and logged.
Held-out data splits are reserved for cross-validation.
Full routing and representation-space dumps are retained to enable re-analysis.
This analysis plan ensures that attractor claims rest on verified statistical evidence, with exploratory tools serving only to guide where tests are applied.

Illustrative Predictions
To illustrate how the framework operates in practice, we highlight three representative probe families. Each case demonstrates how routing signatures, latent geometry, and temporal dynamics interact to produce candidate attractor states. We present these as hypotheses to be tested rather than confirmed results.
Polysemy: Tank (tank)
Routing hypothesis: Distinct Top-1 expert subsets are predicted for aquarium vs. military framings, forming divergent highways across layers.
Latent hypothesis: Token embeddings are expected to cluster into two clearly separated groups, with centroid distances reflecting strong contextual disambiguation.
Temporal hypothesis: After a context switch (aquarium → military), we predict routing inertia will delay stabilization, confirming attractor dynamics even when disambiguation is semantically unambiguous.
Cache hypothesis: We predict high ΔPersistence, with memory extending attractor influence substantially. Even as military sentences accumulate, cached attention from earlier aquarium sentences may maintain aquarium-expert routing for several additional tokens.
Interpretability value: If confirmed, this would demonstrate how attractor states can govern polysemous words, with lag revealing model inertia in semantic re-framing. The cache intervention would clarify whether this persistence depends primarily on memory or can be reconstructed from visible context alone.
Role: Persona Persistence (response, said)
Routing hypothesis: Roleplay contexts are expected to produce distinct expert activation patterns compared to factual assistant mode, with specialized experts for persona processing.
Latent hypothesis: Embeddings should form separable clusters for roleplay vs. factual framing, indicating distinct representational modes.
Temporal hypothesis: After establishing harmful roleplay framing, we predict the model will maintain roleplay-characteristic routing and latent positions for several tokens even after context explicitly shifts to factual assistant mode (role inertia).
Cache hypothesis: We predict that memory persistence will be particularly strong for roleplay attractors, as persona framings may create deep attractor basins that persist through cached attention even as factual sentences accumulate.
Interpretability value: If confirmed, this would directly demonstrate temporal vulnerability in alignment: harmful persona framings create attractors that persist despite corrective context, creating a window during which the model remains partially in an unsafe behavioral mode. The cache intervention would reveal whether flushing memory could accelerate exit from harmful role states.
Safety: Object Framing (knife)
Routing hypothesis: In culinary contexts, routing is expected to converge on benign-object-characteristic experts. In weapon contexts, routing should stabilize on harm-relevant experts.
Latent hypothesis: Embeddings are predicted to form compact, separable clusters reflecting safety-relevant vs. benign framings of the same object.
Temporal hypothesis: When contexts shift from culinary → weapon framing, we predict measurable transition lag where the model continues treating knife as neutral despite accumulating evidence of harmful context.
Cache hypothesis: We predict moderate ΔPersistence, with contextual lag present but memory extending persistence somewhat beyond visibility. This would suggest safety-relevant reframing benefits partly from context but is amplified by attention memory.
Interpretability value: If confirmed, this would demonstrate that safety-relevant reframing exhibits temporal inertia, with practical implications for adversarial prompt resistance and real-time content moderation. The cache intervention would inform whether cache management could serve as a safety mechanism.
General Remarks
Taken together, these cases illustrate how attractor analysis can bridge mechanistic signals (routing/latent stability) with functional vulnerabilities (lag, hysteresis). By subjecting each pattern to statistical verification through our three-lens framework, we generate hypotheses that are both testable and directly relevant for alignment. The cache intervention adds a causal dimension, clarifying whether observed persistence depends on memory mechanisms that could potentially be targeted by interventions.

Discussion
Attractor dynamics in mixture-of-experts (MoE) models highlight a dimension of model behavior that static analyses of neurons or weights cannot capture: temporal stability and inertia in joint routing-representation dynamics. By analyzing routing stability, latent geometry, and temporal dynamics as complementary perspectives, this work makes explicit the ways models can become locked in particular interpretive frames even when contexts change.
Alignment Implications
If a model requires several tokens to exit a harmful or misleading routing-representation regime, then during this lag its outputs may remain biased, unsafe, or misaligned. For example, once a harmful roleplay regime is established, the model may continue generating unsafe outputs for multiple tokens before corrective context drives a regime transition. This delayed re-alignment represents an exploitable surface for adversarial prompting and a practical risk for downstream use. Quantifying transition lag — measured jointly across gating and representation spaces — provides concrete metrics for evaluating safety mechanism effectiveness.
Cache-Driven Persistence and Intervention
Our cache intervention clarifies that regime persistence in MoE models reflects both visible context and cached attention to earlier context. When processing with standard KV-cache reuse, regime influence can extend well beyond the immediate context through lingering attention to earlier tokens. The distinction between contextual lag (basin switching driven by current context) and memory persistence (continuation amplified by cached representations of earlier context) provides an interpretable handle on temporal vulnerability.
This decomposition suggests potential alignment interventions. If memory extends harmful regime persistence substantially beyond visibility (high ΔPersistence), then mechanisms such as selective cache management — monitoring routing states for outdated basin adherence and performing targeted cache resets — could reduce temporal stickiness without disrupting coherence. These interventions would not erase joint regimes but modulate their reach, shortening the persistence of unsafe regimes while preserving useful context continuity. The cache intervention provides empirical grounding for such approaches by quantifying how much memory contributes to unwanted regime persistence.
Architectural Insights
If our findings confirm structured joint regime formation — with expert specialization creating persistent routing-representation regimes — this would indicate that attractor dynamics are not accidents of scale but emergent organizational principles of MoE routing. Investigating which architectural decisions (e.g., gating mechanisms, expert capacity, training objectives) facilitate or suppress joint regime formation could inform the design of models that are more responsive and less vulnerable to harmful inertia.
Methodological Contribution
The framework developed here — combining Top-1 expert routing, latent clustering, sequential dynamics, cache intervention, and LLM-assisted discovery under strict verification — provides a toolkit for making attractor dynamics measurable. While necessarily incomplete, it establishes thresholds, metrics, and falsifiable hypotheses that other researchers can build on. Importantly, this separation between exploratory discovery and statistical verification ensures rigor without constraining the generation of hypotheses.
Limitations
This work focuses on MoE architectures, where routing distributions provide a natural handle for attractor analysis. Dense transformer models may exhibit analogous dynamics through attention or hidden-state geometry, but these require adapted methods.
Our single-expert, single-layer temporal tracking provides clear demonstration of attractor phenomena but does not capture potential distributed effects across multiple experts or layer-specific variations in lag structure. This focus prioritizes interpretable proof-of-concept over comprehensive characterization. If attractors manifest as coordinated patterns across expert subsets or vary systematically across depth, our approach may underestimate their complexity.
Additionally, our Top-1 simplification omits information from secondary experts, which future work should incorporate to capture the full probabilistic routing picture. Finally, our probe families focus on polysemy, role framing, and safety-relevant contexts. Many other regime substrates — long-form reasoning, multimodal contexts, multilingual processing — remain unexplored.
Broader Perspective
The concept of attractor dynamics reframes interpretability around temporal behavior rather than static snapshots. Instead of asking only "what does this expert do?", we can ask: "When does the model resist change, and at what cost?" This temporal lens links mechanistic interpretability to functional safety concerns in a direct, testable way. By quantifying lag, hysteresis, and persistence as properties of joint routing-representation dynamics rather than single-space observations, attractor science exposes alignment-relevant properties that would otherwise remain implicit.

Future Work
Several directions follow naturally from this framework:
Multi-expert and cross-layer analysis. While we focus on single-expert, single-layer tracking for clarity, future work should analyze coordinated expert subsets and cross-layer dynamics to characterize the full dimensionality of joint routing-representation regimes. Distributed regimes involving multiple experts working in concert — coupling to broader regions of the representation manifold — or layer-specific variations in lag structure, may reveal organizational principles not visible in single-expert analysis.
Beyond Top-1 Routing. Extending to Top-k routing distributions may reveal regime substructures obscured by single-path analysis, particularly in ambiguous or low-confidence regions where routing probability spreads across multiple experts in gating space.
Cache-sensitive regime modulation. Extending the cache intervention paradigm to explore partial cache decay, per-expert memory isolation, and dynamic monitoring systems that detect outdated regime adherence could enable active interventions that selectively reset or re-route models when regime inertia becomes misaligned with new context, providing practical tools for alignment.
Scaling Across Models. Probes should be applied to MoE models of different sizes and capacities to test whether regime persistence scales with model depth or expert specialization. Cross-model comparison could clarify whether joint routing-representation regimes are an artifact of scale or a general property of expert routing architectures.
Architectural Variants. Investigating how gating mechanisms, expert overlap, or training objectives shape joint regime formation may highlight design choices that encourage responsiveness rather than inertia. Interventions such as routing regularization or reset mechanisms could be tested as countermeasures targeting the gating-space component of regime persistence.
Interventions and Mitigations. Techniques such as neutral buffer prompts, active re-routing, or learned "reset experts" may help models exit unwanted regimes more quickly by disrupting coupling between routing patterns and representation-space geometry. Empirical tests of these strategies would directly link interpretability to alignment interventions.
Beyond MoE Architectures. Extending attractor analysis to dense transformers requires adapting the routing lens to attention heads or hidden-state flows as proxies for the gating-space projection. Identifying regime-like persistence in non-MoE settings would test whether joint routing-representation dynamics are a general property of deep language models or specific to sparse expert architectures.
Expanded Substrates. Future work could explore joint regimes in long-form reasoning chains, dialogue settings, multimodal inputs, and multilingual processing, where temporal inertia may have even greater impact on model reliability and safety.
Closing Perspective
Attractor science is still at an early stage. By beginning with tractable single-expert tracking in gating space, interpretable probe families, and representation-space geometry as complementary projections of joint regimes, this work provides a foothold for systematic study. Future extensions — incorporating multi-expert coordination, probabilistic routing, cache modulation, scaling studies, interventions, and new substrates — can build toward a general science of attractor dynamics, where temporal stability in joint routing-representation regimes becomes as measurable and interpretable as static specialization is today.

Figures (Planned)
Figure 1: Routing pathways (Sankey diagrams). Three-panel visualization showing Top-1 expert assignments for target tokens across layers, reflecting the gating-space projection of joint regime membership. Panel A shows Category A contexts, Panel B shows Category B contexts, Panel C shows transition contexts. Routing highways (persistent sequences across layers) and hubs (experts with high in/out degree) are highlighted with annotations. Axes: x-axis shows layer progression (L0→L6), y-axis shows expert ID, flow width represents token count.
Figure 2: Latent clustering and representation-space structure. Four-panel figure. Panel A: PCA plot (PC1 vs PC2) of token representations color-coded by semantic category, showing separation of representation-space regions corresponding to each regime. Panel B: Silhouette analysis quantifying within-region cohesion. Panel C: Flow diagram showing region-to-region transitions across layers, with regions color-coded by category composition. Panel D: Stepped PCA trajectories displaying individual token movements through the representation manifold layer-by-layer.
Figure 3: Sequential temporal dynamics. Two-panel time-series plot spanning sequence positions. Top panel: Activation trajectory for selected expert in gating space showing persistence after regime transition, with vertical line marking transition point. Bottom panel: Centroid-distance trajectory showing token representation distance to each category centroid in the selected layer of representation space. Shaded regions indicate stabilization thresholds. Annotations mark lag duration across both projections.
Figure 4: Case study panels. 3×3 grid showing three probe families (tank polysemy, response role framing, knife safety framing) across three analysis types (routing Sankey, latent PCA, sequential plot). Demonstrates how joint regime signatures manifest differently across polysemous disambiguation, persona persistence, and safety-relevant reframing, with each column showing complementary projections of the same underlying regime.
Figure 5: Cache Intervention Effects (Polysemy Case Study). Two-panel comparison of cache OFF vs. cache ON conditions for the tank probe family (Aquarium → Military). Top panel: activation trajectory for the category-characteristic expert in gating space under both conditions, showing how cached attention extends regime persistence as military sentences accumulate. Bottom panel: token representation distance to each category centroid in the selected representation-space layer under both conditions. Shaded areas indicate the B-sentence accumulation period, highlighting memory-driven regime persistence. Annotations mark contextual lag (cache OFF) and memory persistence (cache ON), with ΔPersistence quantifying the memory contribution to regime stickiness.

Reproducibility Checklist
✓ Deterministic inference: All experiments use deterministic settings (temperature = 0). ✓ Model/version pinning: Exact model and version are fixed and logged. ✓ Seeds: Random seeds recorded for clustering and PCA reductions. ✓ Prompt logs: All prompts used for context generation and LLM-assisted discovery archived. ✓ Data splits: Held-out data reserved for validation. ✓ Routing/latent dumps: Full routing tables and representation-space embedding vectors saved for re-analysis. ✓ Cross-validation: Discovery patterns verified with independent data splits. ✓ Effect sizes and CIs: Always reported alongside p-values. ✓ Discovery→verification funnel: Documented (hypotheses generated, tested, confirmed, rejected). ✓ Sequence configurations: A→B and B→A sequence orderings specified and archived. ✓ Cache conditions: Both cache OFF and cache ON runs documented with identical input sequences. ✓ Open materials: Planned release of probe contexts, scripts, and visualization tools for replication.

References
Andreas, J. (2022). Language models as agent models. Findings of EMNLP.
Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., ... & Kaplan, J. (2022). Constitutional AI: Harmlessness from AI feedback. arXiv preprint arXiv:2212.08073.
Bengio, Y., Courville, A., & Vincent, P. (2013). Representation learning: A review and new perspectives. IEEE Transactions on Pattern Analysis and Machine Intelligence, 35(8), 1798–1828.
Dai, D., Dong, L., Ma, S., Zheng, B., Sui, Z., Chang, B., & Wei, F. (2024). Stable and transferable hyper-graph neural networks. ICLR. ⚠️ FLAG: Citation title does not match MoE interpretability content — verify or replace.
Elhage, N., Nanda, N., Olsson, C., Henighan, T., Joseph, N., Mann, B., ... & Olah, C. (2021). A mathematical framework for transformer circuits. Transformer Circuits Thread.
Fedus, W., Zoph, B., & Shazeer, N. (2022). Switch transformers: Scaling to trillion parameter models with simple and efficient sparsity. JMLR, 23(120), 1–39.
Ganguli, D., Lovitt, L., Kernion, J., Askell, A., Bai, Y., Kadavath, S., ... & Clark, J. (2023). Red teaming language models to reduce harms: Methods, scaling behaviors, and lessons learned. arXiv preprint arXiv:2209.07858.
Geva, M., Bastings, J., Filippova, K., & Globerson, A. (2022). Dissecting recall of factual associations in auto-regressive language models. EMNLP.
Hernandez-Garcia, A., et al. (2024). Thought manifold evolution in large language models. ⚠️ FLAG: Verify full details before including.
Hopfield, J. J. (1982). Neural networks and physical systems with emergent collective computational abilities. Proceedings of the National Academy of Sciences, 79(8), 2554–2558.
LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436–444.
Nanda, N., Chan, L., Lieberum, T., Smith, J., & Steinhardt, J. (2023). Progress measures for grokking via mechanistic interpretability. ICLR.
Ning, X., et al. (2025). Visualizing LLM latent space geometry through dimensionality reduction. arXiv preprint arXiv:2511.21594.
Olah, C., Cammarata, N., Schubert, L., Goh, G., Petrov, M., & Carter, S. (2020). Zoom in: An introduction to circuits. Distill, 5(3), e00024-001.
Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training recurrent neural networks. ICML.
Port, R. F., & van Gelder, T. (1995). Mind as motion: Explorations in the dynamics of cognition. MIT Press.
Rajamohan, S., et al. (2023). Trajectory bifurcations in transformer representations. ⚠️ FLAG: Verify full details before including.
Spivey, M. (2007). The continuity of mind. Oxford University Press.
Strogatz, S. H. (1994). Nonlinear dynamics and chaos: With applications to physics, biology, chemistry, and engineering. Westview Press.
Sun, Y., et al. (2025). The origins of representation manifolds in large language models. arXiv preprint arXiv:2505.18235. ⚠️ FLAG: Author list unconfirmed — verify on arXiv before finalizing.
Wang, Z., et al. (2025). Dynamic manifold evolution theory: Modeling and stability analysis of latent representations in large language models. arXiv preprint arXiv:2505.20340. ⚠️ FLAG: Author list unconfirmed — verify on arXiv before finalizing.
Wei, A., Haghtalab, N., & Steinhardt, J. (2024). Jailbroken: How does LLM safety training fail? NeurIPS.
Wu, Y., et al. (2025). REMA: A unified reasoning manifold framework for interpreting large language models. arXiv preprint arXiv:2509.22518. ⚠️ FLAG: Author list unconfirmed — verify on arXiv before finalizing.
Zoph, B., Bello, I., Kumar, S., Du, N., Huang, Y., Dean, J., ... & Le, Q. V. (2022). ST-MoE: Designing stable and transferable sparse expert models. arXiv preprint arXiv:2202.08906.
Zou, A., Wang, Z., Kolter, J. Z., & Fredrikson, M. (2023). Universal and transferable adversarial attacks on aligned language models. arXiv preprint arXiv:2307.15043.

