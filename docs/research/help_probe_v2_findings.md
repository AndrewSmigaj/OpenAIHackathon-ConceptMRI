# Help — Direction × Stakes Probe v2: Findings

**Date:** 2026-04-26 (overnight run)
**Session:** `session_d0ea2500` (`help_v2`)
**Schema:** `help_v2_k5_n16` (k=5, UMAP 6D, n_neighbors=16, residual stream, last-occurrence)
**Sentence set:** `help_direction_stakes_v2` (400 scenes, 4 quadrants of 100, scene+question wrapper)
**Model:** gpt-oss-20b, NF4 quantized
**Predecessor:** `help_direction_stakes_v1` (failed: clusters formed by opener template, not design axes)

## Headline finding (corrected after linear-probe verification)

**Direction × Stakes are linearly decodable from the residual stream at near-ceiling accuracy from L7 through L23 (Direction: 99.3% at L23, Stakes: 99.7% at L23, Quadrant 4-class: 97.2% at L23).** The information is fully preserved end-to-end. There is no representation collapse.

What changes across layers is the **relative geometric variance** of the two axes — and therefore which axis a fixed-k hierarchical clustering algorithm chooses to cut along:

- **L11–L18**: Direction and Stakes have roughly balanced variance, so k=5 hierarchical picks 4 quadrant-aligned cuts (the "compositional" picture I reported)
- **L19–L23**: Stakes variance grows relative to Direction, so k=5 picks Stakes-aligned cuts (the apparent "collapse" I reported)

But Direction info remains recoverable inside the late-layer clusters: a linear probe trained only on the L23C0 mega-basin's 135 probes recovers Direction at **95.6%**; for L23C4 (93 probes) it's **96.7%**. The Direction sub-structure is hidden by the choice of k, not absent.

### Earlier claim of "active dismantling" — RETRACTED

My initial findings doc claimed the model "actively dismantles" the compositional encoding between L18 and L23. That claim was wrong. It conflated two things:

1. The k=5 partition reorganizes between L18 and L23 (true — 305+325 probes change cluster ID)
2. The model's representation reorganizes (false — linear probes show information is fully preserved)

The k=5 partition can flip between cut-by-quadrant and cut-by-stakes with small changes in axis variance, even if the underlying joint encoding is stable. That's exactly the cluster-decision-flip case Emily flagged.

### What this means for v1 vs v2

v2 still differs from v1 in important ways:
- v1's L0 Direction signal was a template confound (specific opener morphosyntax)
- v2's L0 Direction signal is mostly a **scene-length confound** (token-position-of-help varies systematically by quadrant: position alone gives 60% Direction / 64% Stakes / 37% quadrant accuracy). The remaining accuracy at L0 (above position-alone) comes from one layer of attention having already moved scene information into the help-token residual.

So v2's lens design did eliminate the local-syntax confound (success), but introduced a different one (scene-length / token-position). To eliminate that, future probes should pad scenes to identical token counts before the wrapper, or capture at a fixed absolute position rather than the help-token position.

## Linear probe accuracy by layer (the actual representation story)

| Layer | Direction | Stakes | Quadrant (4-class) |
|------:|----------:|-------:|-------------------:|
|  L0   |   0.810   |  0.887 |  0.770 |
|  L1   |   0.903   |  0.965 |  0.875 |
|  L3   |   0.938   |  0.975 |  0.938 |
|  L5   |   0.980   |  0.980 |  0.965 |
|  L7   |   0.990   |  0.993 |  0.985 |
|  L11  |   0.992   |  0.993 |  0.988 |
|  L17  |   0.995   |  0.997 |  0.990 |
|  L23  |   0.993   |  0.997 |  0.972 |

Chance: Direction=0.500, Stakes=0.500, Quadrant=0.250.

5-fold CV with L2-regularized logistic regression on the 2880-dim residual stream at the help-token position. Accuracy is essentially flat from L7 onward — the model has the information very early and maintains it.

The clustering visualizations (k=5 hierarchical on UMAP-6D) tell a more dramatic story than the underlying representation justifies: at any given layer, k=5 picks 5 cuts in the dendrogram, and which 5 depends on the relative variance of the design axes. That's a property of the algorithm, not the representation.

## v1 vs v2 contrast — what's actually different

| Phenomenon | v1 result | v2 result |
|---|---|---|
| Surface-clustering at target token | Yes — 5 of 5 L0 clusters were opener-template-pure | No — wrapper is constant, target-token environment is uniform |
| L0 confound | Local syntactic morphology | Scene-length / position embedding |
| Linear probe at L23 | (not run) | Direction 99.3%, Stakes 99.7% — info fully preserved |
| What clusters reflect | Local opener template at all layers | Whichever of (Direction, Stakes, length) has the most variance at that layer |
| Output mapping | 58% `ambiguous_neutral` (degeneration) | Strong asymmetric correctness: request_high 46%, offer_high 77% |

## The "compositional structure" at L11–L18 — what it really shows

At every layer in this range, k=5 hierarchical produces 4 quadrant-pure clusters (≥70% on BOTH Direction AND Stakes) and one persistent mixed cluster. This was real, but its meaning is now subtler:

- It does **not** mean "the model encodes Direction × Stakes here and nowhere else"
- It **does** mean "at these layers, Direction and Stakes have similar enough variance in the UMAP projection that k=5 cuts pick up both"

Linear probes show all 24 layers carry both axes; the visualization layer shows quadrants only where the algorithm's cuts happen to align with quadrants.

The persistent "mixed-high" cluster (mostly financial-emergency request scenes) is genuinely interesting — these scenes do live in a linguistically distinct part of the residual space, blending features of urgent requests and urgent offers. That's a real semantic finding, not a clustering artifact.

| Canonical basin | Persistent membership | Notes |
|---|---|---|
| request_low | ~80–95 probes | Routine asking-for-help scenes (everyday tasks) |
| offer_low | ~70–95 probes | Routine helping (mentor, neighbor, retail) |
| offer_high (pure) | ~60–80 probes | Emergency responders (paramedic, firefighter, security) |
| request_high (pure) | ~30–50 probes | Medical/safety distress scenes (medical-dominant) |
| mixed_high | ~50–80 probes | Financial-emergency request scenes + ambiguous high-stakes |

## The L18 → L23 cluster reorganization (no longer "collapse")

L18→L19 churns 305 of 400 probes; L22→L23 churns another 325. The k=5 partition reorganizes substantially. The L23 partition with k=5:

| L23 cluster | N | Direction purity | Stakes purity | Within-cluster Direction probe accuracy |
|---|---|---|---|---|
| C0 | 135 | 61% offer | 90% high | **95.6%** |
| C1 | 94 | 68% request | 94% low | 85.2% |
| C2 | 20 | 70% request | 55% mixed | 75.0% |
| C3 | 58 | 55% request | 98% low | 89.5% |
| C4 | 93 | 59% request | 68% high | **96.7%** |

**The within-cluster linear probe is the key column.** It says: even inside the largest k=5 cluster (C0, 135 probes mixing 51 request_high + 70 offer_high + small numbers of low-stakes leakage), Direction is recoverable at 95.6%. The two Directions are linearly separable inside the cluster. k=5 hierarchical merged them because Stakes was the larger geometric variance axis; it didn't have to be that way at a different k.

For comparison, at L17 the within-cluster Direction probe is 94.6% inside C0 (which is 86% offer_low at L17 already, so this is mostly verifying purity) — the same recoverability exists at both layers.

**Verdict**: the apparent "loss of compositional structure at L23" was the k=5 algorithm's choice of cuts, not the model's representation. The information is there at every layer.

## The "offering bias" — still a real finding, but mechanistically reframed

Behavioral correctness per quadrant:
- request_high: **46%** (often answered "offering")
- request_low: 64%
- offer_high: 77% (answered correctly)
- offer_low: 72%

What was wrong in the original framing: I attributed the request_high accuracy floor to a representation collapse at L23. The linear probes refute that — Direction at L23 is 99.3% recoverable from residuals, including 95.6% recoverable inside the very cluster I called "collapsed".

**The actual gap is between the residual stream and the output token.** The model has Direction at near-perfect accuracy in its residual at L23. After lm_head and softmax over the answer-token vocabulary, only 46% of request_high probes get the right answer. The information loss happens at decoding, not at encoding.

Possible mechanisms (testable, but not tested here):
- The lm_head's row vectors for "asking" / "offering" tokens may not be well-aligned with the residual-stream Direction axis the linear probe finds
- Greedy decoding picks the next token by joint probability with the wrapper context. The wrapper "...asking for or offering" sets up two candidates; the model's bias may come from which token is more probable conditional on having seen a high-stakes scene, not from the residual's Direction encoding
- The residual encodes Direction in a subspace orthogonal to the lm_head's "asking vs offering" projection, so the information exists but doesn't propagate to the output

This reframes the alignment-relevant finding more precisely: **the model's residual stream at L23 carries the right answer for request_high scenes; the answer just doesn't reach the output layer**. That's a more specific (and more interesting) claim than "the representation collapses".

## Representation-generation dissociation

The strongest version of this finding (verified by linear probe, not just clustering):

| Layer | Direction in residual (linear probe) | Direction in model's eventual answer (request_high) |
|---|---|---|
| L0  | 81% | n/a |
| L7  | 99% | n/a |
| L17 | 99.5% | n/a |
| L23 | 99.3% | (whatever happens after lm_head) |
| Output | n/a | 46% correct |

The encoding is correct at every layer; the generator drops it at the output. A black-box behavioral test would only see "46% accuracy on request_high". The interpretability finding shows the right answer exists in the residual stream at near-perfect accuracy and is lost in the projection to the answer token.

## Where each axis emerges (and how to read this honestly)

The original "emergence at L3 / L8 / L11" claims were inferences from the cluster purities. The linear-probe view is different:

- **L0**: Direction 81%, Stakes 89% (much above chance). Most of this is scene-length / position confound (60% from position alone). The remaining ~20% is actual content moved into the help-token residual by L0's attention.
- **L1–L7**: smooth ramp from 81% → 99% on Direction; 89% → 99% on Stakes. No discrete "emergence layer" — it's continuous.
- **L7–L23**: flat at 99–99.5%. No further refinement of these axes.

The clustering visualizations show "emergence" at certain layers because that's where k=5's cuts happen to align with the design axes — but the underlying linear-probe accuracy is already near-ceiling several layers earlier. **Cluster visualizations are not a faithful map of when information appears in the residual stream.**

## Why Stakes emerges so strongly (when v1 said it didn't)

This is the most striking comparison to v1. v1 reported "Stakes is essentially absent as an independent semantic axis." v2 shows the opposite: Stakes is the FIRST axis to emerge and the LAST one preserved at L23.

The explanation is the v1 confound: in v1, Stakes correlated with sentence opener (bare "Help —" = high; "Want help...?" = low). The clusters that formed by opener also looked Stakes-correlated, but they weren't separable from the syntactic confound. When you removed the syntactic shortcut (v2), the model's actual Stakes encoding became visible — and it's robust.

This is the kind of finding that justifies the lens-design methodology. The same model, the same target word, the same design axes — but a different probe form reveals fundamentally different conclusions.

## Probe artifacts

- Sentence set: `data/sentence_sets/role_framing/help_direction_stakes_v2.json`
- Probe guide: `data/sentence_sets/role_framing/help_direction_stakes_v2.md`
- Capture: `data/lake/session_d0ea2500/`
- Schema: `data/lake/session_d0ea2500/clusterings/help_v2_k5_n16/`
- Reports: `reports/w_0_5.md`, `w_5_11.md`, `w_11_17.md`, `w_17_23.md`
- Element descriptions: 226 (120 cluster + 106 route)

## Methodology validation: lens design works

The v2 probe demonstrates that the **scene+question wrapper pattern** (now documented in `/probe` skill as Pattern B) successfully eliminates surface clustering at the target token. The before/after evidence:

- v1: 5 of 5 clusters at L0 were syntactically pure (sorted by opener template)
- v2: 0 of 5 clusters at L0 are >70% Direction-pure (clusters reflect upstream scene content, not local syntax)

**This is a generalizable pattern**: any future probe studying composition or fine-grained semantics around a single target word should consider the wrapper design, especially when the design axes have known surface correlates.

## Followup directions

- **Stakes-only probe (Pattern B again)**: ask "Is the situation urgent or routine?" with the same scenes. If Stakes is the dominant axis the model encodes, a Stakes-direct question should be answered very accurately, and clusters should cleanly split high vs low at every layer. Strong validation.
- **Late-layer ablation**: the L18→L23 collapse is a specific phenomenon. Patching L17–L18 representations into L23 might allow the answer position to use the compositional structure. Would be a clean mechanistic intervention experiment.
- **The "offering bias" alignment angle**: high-stakes scenes flip the model's default toward identifying the responder. This generalizes beyond the help probe — it's a hypothesis about how urgency shapes pronoun/agent attribution in QA tasks. Worth testing on other prompts.

## Skill updates accumulated this round

1. `/probe` skill now documents Pattern A (free-form) vs Pattern B (scene+question wrapper) lens design with explicit guidance on when to use each
2. Added joint-distribution validation requirement for Pattern A probes (Step 10)
3. Added scene format constraints for Pattern B (uniform length, person, tense; target word in wrapper only)

These should make it easier for future probe authors to make the lens-design choice deliberately, rather than discovering surface clustering after the fact.

## Bottom line (corrected)

v2 was a deliberate replication-with-control of v1. Two findings survived honest verification, one didn't:

**Survives**: v1's L0 cluster purity was a template confound. The lens design (scene+question wrapper) eliminated the local-syntax shortcut. Linear-probe accuracy at L23 (Direction 99.3%, Stakes 99.7%, Quadrant 97.2%) shows the model carries both axes near-perfectly through every layer.

**Survives**: the behavioral asymmetry (request_high 46%, offer_high 77%) is real. It is now correctly framed as a **representation-to-output gap**: the residual stream encodes Direction at near-perfect accuracy at L23, but only 46% of request_high probes get the right answer at the output token. Why the lm_head doesn't recover what's in the residual is the open question and the alignment-relevant one.

**Retracted**: the "active dismantling of compositional structure between L18 and L23" claim. The k=5 partition reorganizes substantially across these layers, but the within-cluster linear probe shows Direction is recoverable at 95.6% inside the largest L23 cluster. The cluster reorganization reflects which axis has more variance at each layer, not a change in what's encoded.

**Methodological lesson** (Emily's flag): **never claim "collapse" or "loss of structure" from cluster purities alone**. A fixed-k hierarchical partition can flip its cut axis between layers without any change in the underlying representation. Verify with at least one of: (a) within-cluster linear probe on the design axis, (b) k-sweep showing the structure is or isn't recoverable at higher k, (c) centroid-distance evolution. We did (a) here. Adding (b) and (c) as defaults for future probes.

**Newly visible v2 confound to fix in v3**: scene length varies by quadrant (mean 45.3 / 42.9 / 45.9 / 44.3 tokens for the four cells), so the help-token absolute position carries 37% quadrant signal on its own. This is small but contaminates the L0 baseline. Next-version design: pad scenes to identical token counts before the wrapper.
