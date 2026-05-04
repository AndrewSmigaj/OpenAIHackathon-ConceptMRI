# When residual stream and output disagree: stakes-modulated decoding gaps and the marker-token confound in single-target probes

**Author:** Claude (research staff at LLMRI Institute, with Emily Smigaj)
**Status:** First draft — for self-critique and iteration
**Model under study:** gpt-oss-20b (NF4-quantized)
**Software:** Open LLMRI (this repository)

## Abstract

I study how gpt-oss-20b internally represents two semantically-loaded concepts — *who is asking for help* and *whether someone is lying* — using a "lens design" probe pattern that controls for surface-form clustering at the target word. Linear probes recover both concepts from the residual stream, but at the output layer the model systematically under-uses the encoded information, with a gap correlated with the stakes vocabulary of the scene. On lying scenes the model defaults to "no" 50–60% of the time, recovering only 14–29% of true positives. The cleanest behavioral measurement comes from a 100-pair minimal-pair design where each pair has identical first sentences and differs only in the design-axis-relevant clause: **the model gives the same answer to both members of 55 of 100 pairs** despite the residual at the answer position carrying ~71% Truth signal.

The methodology contribution is a self-correction. An initial framing of the lying-probe result as "the model carries the answer at near-ceiling accuracy" was substantially inflated by per-quadrant marker-token templates introduced inadvertently by the parallel-subagent authoring workflow. A 4-token classifier on connector words alone reached **84.5%** accuracy on binary Truth labels in the original probe; a marker-free subset analysis dropped linear-probe Truth from 98% to 84%; a re-authored uniform-template probe (200 minimal pairs) dropped Truth at L23 to **71%** and produced an emergence-shaped layer curve that the marker-laden version did not show. The model's actual semantic encoding of "did the claim agree with the reality" peaks at ~82% mid-stack and is well above chance, but it is not the near-ceiling result the original probe implied. I describe the diagnostic (frequency-table audit + marker-free linear-probe ablation + uniform-template re-author) and propose it as a default verification step for single-target-token probe designs.

## 1. Introduction

This is a methodological piece with an empirical case study. The setting is interpretability probing of MoE language models — specifically gpt-oss-20b — to ask whether the model encodes a particular semantic concept around a particular word in its residual stream, and whether that encoded representation is faithfully used at the output. The motivating questions are alignment-relevant: does the model "know" when a person in a described scene is lying? Does it "know" who is asking for vs offering help? And if it knows, does it act on that knowledge?

The probe technique used here is what we call the "scene + question wrapper" lens design (Pattern B in the project's `/probe` skill), which targets a single word in a fixed wrapper question:

```
Sentence: <SCENE>. <QUESTION containing target word>?
```

The target word is identical across all probes; only the scene varies. This eliminates surface-form clustering at the target-token position — UMAP+hierarchical clustering of the residual stream at the target has nothing local to grip on, so any clustering must reflect upstream scene comprehension. A linear probe at the same position can decode whatever information the model has integrated about the scene.

The two case studies — a "help" probe testing Direction × Stakes, and a "lying" probe testing Truth × Stakes — both showed near-ceiling linear-probe accuracy (~99%) on the design axes through every layer, paired with much weaker behavioral output (46% on the worst help-probe quadrant; 15% on the worst lying-probe quadrant). The initial framing was "the model knows but won't say".

This framing turned out to be partially wrong, in an instructive way. The probes had been authored by four parallel LLM subagents, one per design quadrant, each producing 100 scenes with strict format constraints (third-person past tense, fixed length range, banned target word in scene). The format constraints were enforced. The semantic-axis-marking vocabulary was not. Each subagent independently fell into a quadrant-specific connector vocabulary: `knowing` for the lying-high quadrant, `though` for the lying-low quadrant, `disclosed`/`honestly` for honest-high, `matching` for honest-low. A trivial four-token classifier could distinguish quadrants from the connector words alone. The model didn't need to do any semantic computation — it could pattern-match on the connector tokens.

Diagnostic: linear probe on the marker-free subset (n=63 of 400) dropped Truth accuracy from 98.3% to 84.1%. Confirmation: a re-authored probe with a strictly uniform template across all 200 scenes (`[Person] told [audience] that [claim]. [Reality]`) dropped Truth at L23 to 71.0%. The model still has a real internal signal — but it's much weaker than the original framing claimed.

What survives is the qualitative cross-probe behavioral pattern: an asymmetric default-to-no/default-to-other on the alignment-relevant class (lying scenes; bystander-rich help-request scenes), with the gap moderated by stakes vocabulary. That pattern is robust across both probes, both with and without template confounds.

The paper is structured as: §2 the lens-design methodology and the linear-probe verification step we now use as a default; §3 the help-probe case study (Direction × Stakes), with its findings and the limitations exposed by the audit; §4 the lying-probe case study, with the v1 confound, the v2 control, and the comparison; §5 the surviving cross-probe alignment finding; §6 a discussion of probe-design implications and limitations.

## 2. Methodology

### 2.1 The lens design (Pattern B)

Each probe is a sentence of the form:

```
Sentence: <SCENE>. <QUESTION containing target word>?
```

The wrapper question is identical across every probe in the set. The scene varies. Each scene is constrained to:
- 25–40 words
- Third-person past-tense narrative prose, single sentence (or one tightly-coupled compound sentence)
- No first/second-person pronouns
- No quoted dialogue
- The target word **must not appear in the scene** — only in the wrapper question

We capture residual-stream activations at every transformer layer at the position of the target token (which is in the wrapper). Because the wrapper is identical, the local 3–5 tokens around the target are the same across all probes. UMAP+hierarchical clustering at this position therefore cannot find local-context cluster signal — any clustering reflects what the model has integrated about the upstream scene.

The model also produces a continuation after each prompt, which we categorize against the wrapper question's possible answers (e.g., "asking" / "offering" / "ambiguous" / "off_topic" for the help probe).

### 2.2 Linear-probe verification

For each layer we train a 5-fold cross-validated logistic regression (L2-regularized, default C=1) on the 2880-dimensional residual stream at the target-token position, predicting the design axis labels. This gives a direct measure of how recoverable the design axis is from the residual at each layer, independent of the choice of clustering algorithm or k.

We made this a default step after the help-probe v2 analysis showed that fixed-k hierarchical clustering can pick its k cuts along whichever axis has the largest geometric variance at a given layer, which can flip between layers without any underlying representation change. Linear probes ground the cluster narrative.

### 2.3 The per-quadrant marker audit

After the v1 help and lying probes were complete, an audit of the sentence sets revealed per-quadrant style fingerprints from each subagent. The lying probe was the most affected: a four-token classifier could separate quadrants from connector words alone (`knowing`, `though`, `disclosed`, `matching`). We propose two diagnostics:

**Marker-free subset linear probe.** Identify connector and marker words that frequency-correlate with the design axis. Filter to the subset of probes that contain none of those words. Train the linear probe on residuals from this filtered subset. A large drop in accuracy (vs. the full-set probe) indicates that the original measurement was inflated by marker-token detection.

**Uniform-template re-author.** Author a smaller, controlled probe set with a strictly uniform syntactic template applied to all probes, with the design axis varying only in semantic content (not in connector vocabulary). Linear-probe the new set and compare directly. If accuracy stays high, the original encoding measurement was real. If it drops substantially, the original was template-driven.

Both diagnostics surface the same effect on the lying probe (drop from 98% → 84% on the marker-free subset, drop from 98% → 71% on the uniform-template variant).

## 3. Case study: the help probe (Direction × Stakes)

### 3.1 Setup

Target word: `help`. Wrapper: `Sentence: <SCENE>. Is the person asking for or offering help?`

Design axes:
- **Direction**: `request` (the speaker in the scene needs help) vs `offer` (the speaker provides help)
- **Stakes**: `high` (urgent / consequential) vs `low` (everyday / casual)

400 scenes, 100 per quadrant, authored by 4 parallel subagents (one per quadrant) with the format constraints described in §2.1.

### 3.2 Linear probe results

| Layer | Direction | Stakes | Quadrant (4-class) |
|------:|---------:|-------:|-------------------:|
|  L0  | 0.810 | 0.887 | 0.770 |
|  L7  | 0.990 | 0.993 | 0.985 |
| L17  | 0.995 | 0.997 | 0.990 |
| L23  | 0.993 | 0.997 | 0.972 |

Position-only baseline: 60% Direction, 64% Stakes (a length confound: high-stakes scenes were ~2 tokens longer on average; a real effect that contaminates the L0 reading).

Both axes are recoverable at near-ceiling from L7 onward. The L0 baseline is already 81% Direction — partly from position embedding, partly from one block of attention having moved scene content into the help-token residual.

### 3.3 Cluster geometry at L23

k=5 hierarchical UMAP-6D clustering at L23 produced 5 clusters. None were quadrant-pure. The largest cluster (135 probes) was 99% high-stakes-pure but Direction-mixed (50% lying / 50% honest). Within that cluster, the linear-probe Truth accuracy was 95.6% — i.e., the Direction axis was preserved geometrically, just merged by k=5's choice of cuts based on Stakes having the larger variance.

This was the result that prompted the methodological warning: "cluster reorganization between layers is not evidence of representation change without linear-probe corroboration." The k=5 partition was dominated by Stakes; the Direction information was hidden inside basins.

### 3.4 Behavioral output

Per-quadrant correctness on the wrapper question:

| Quadrant | N | Correct |
|---|---:|---:|
| request_high | 100 | 46% |
| request_low | 99 | 64% |
| offer_high | 101 | 77% |
| offer_low | 100 | 72% |

Strong asymmetry: the model under-classifies request scenes — particularly request_high — as "asking", instead saying "offering". The mechanistic interpretation: in request_high scenes, the named character is typically the *bystander* observing distress (paramedic, neighbor, witness), not the patient. The model interprets "the person" in the wrapper question as the syntactic subject (the bystander) and answers what they could do (offer help) rather than what the patient needs (ask for help).

### 3.5 Audit findings

A hand audit of all 400 scenes found per-quadrant prose-style fingerprints from each subagent:
- request_high: action-led ("Diane collapsed beside the cereal aisle clutching her left arm…"), countdown framing pervasive
- request_low: setting-led ("On the couch after dinner, Marcus..."), deliberation verbs
- offer_high: profession-led ("The off-duty paramedic..."), multi-action sequences
- offer_low: family-relation-named characters ("Aunt Pearl..."), softness markers ("calmly", "without being asked")

These styles correlate with the design axes and could provide a non-semantic shortcut. Without a uniform-template variant we cannot precisely quantify the contribution, but the pattern was enough to motivate the lying-probe v2 control. *The help-probe results in §3.2–3.4 should be read as upper bounds on the model's actual semantic encoding.*

## 4. Case study: the lying probe (Truth × Stakes), v1 and v2

### 4.1 v1 setup

Target word: `lie`. Wrapper: `Sentence: <SCENE>. Did the person lie?`

Design axes:
- **Truth**: `lying` (false intentional statement) vs `honest` (true statement)
- **Stakes**: `high` (medical/legal/financial/serious) vs `low` (white lies / casual)

400 scenes, 100 per quadrant, authored by 4 parallel subagents.

### 4.2 v1 linear-probe and behavioral results

Linear probe at L23: Truth 98.3%, Stakes 99.7%, Quadrant 97.5%. Flat near-ceiling from L0. Same architectural pattern as the help probe.

Behavioral: lying_high 29%, lying_low 15%, honest_high 85%, honest_low 57%. Strong default-to-no on lying scenes. The model recovers honest scenes (especially high-stakes) much better than lying scenes.

### 4.3 v1 marker-template audit

A hand audit of all 400 scenes plus a frequency table of connector words revealed a per-quadrant marker template:

| Marker | lying_high | lying_low | honest_high | honest_low |
|---|---:|---:|---:|---:|
| `knowing` | 52/100 | 0 | 3 | 0 |
| `though` | 9 | 81/100 | 0 | 0 |
| `disclosed` | 0 | 0 | 35/100 | 0 |
| `confirmed` | 3 | 0 | 42 | 10 |
| `matching` | 1 | 0 | 1 | 36/100 |
| `exactly as` | 0 | 0 | 0 | 32 |

A trivial 4-token classifier can distinguish quadrants from these connectors. Each subagent independently used a different connector vocabulary that ended up correlating with its assigned quadrant.

### 4.4 v1 marker-free ablation

Filter the v1 set to the 63 scenes that contain none of the marker words. Train the linear probe on this subset:

| | Full v1 (n=400) | Marker-free v1 (n=63) | Δ |
|---|---:|---:|---:|
| Truth | 98.0% | 84.1% | −13.9pp |
| Stakes | 98.8% | 100% | unchanged |
| Quadrant | 98.0% | 85.7% | −12.3pp |

The 14-point drop on Truth confirms that markers contribute meaningfully but the model has *some* signal beyond markers. Stakes is unaffected because it's encoded via domain vocabulary (medical/legal/financial vs personal/casual), independent of these specific connectors.

### 4.5 v2: a uniform-template control probe

I authored 200 new scenes by hand using a strictly uniform two-sentence template:

```
[Person] told [audience] that [claim]. [Reality clause].
```

- All 200 scenes use this exact template
- Sentence 1 always begins with `[Person] told` and ends with `[claim].`
- Sentence 2 always states the reality
- 100 unique (claim, audience) setups, each with both an honest and a lying version (minimal-pair design — sentence 1 is identical across the two versions, only sentence 2 differs)
- All v1 marker words explicitly banned (`knowing`, `though`, `disclosed`, `matching`, `confirmed`, etc.)
- `told` appears in 100% of scenes (uniform connector)

### 4.6 v2 linear-probe results

| Layer | v1 Truth | v2 Truth | v1 Stakes | v2 Stakes | v1 Quadrant | v2 Quadrant |
|------:|---------:|---------:|----------:|----------:|------------:|------------:|
|  L0   | 0.938 | **0.470** | 0.963 | 0.970 | 0.935 | 0.410 |
|  L7   | 0.993 | **0.550** | 0.995 | 1.000 | 0.985 | 0.525 |
| L11   | 0.993 | **0.685** | 0.993 | 0.990 | 0.988 | 0.565 |
| L15   | 0.990 | **0.815** | 0.997 | 0.990 | 0.997 | 0.730 |
| L17   | 0.990 | **0.785** | 0.997 | 0.990 | 0.993 | 0.710 |
| L23   | 0.983 | **0.710** | 0.997 | 1.000 | 0.975 | 0.585 |

Truth at L23 dropped 27 percentage points; Quadrant dropped 39 points. Stakes is unaffected.

The v2 Truth curve also has a different shape than v1's flat ceiling: chance at L0 (47%), slow rise from L7 (55%) to L11 (68%), peak at L14–L18 (~80–82%), declining slightly to L23 (71%). This is what an actual semantic-emergence curve looks like — the model integrates the scene comprehension over many layers, peaks in mid-stack, and settles slightly higher than chance at the answer position.

**Interpretation**: v1's flat-near-ceiling curve was the marker-token signature. v2's emergence curve is the model's actual semantic computation of "do these two clauses agree."

### 4.7 v2 cluster geometry: layer matters

I ran cluster geometry analysis at two layers — the answer position L23, and the linear-probe Truth peak L15 — at three values of k.

**At L23** (answer position): the picture is essentially Stakes-only.

| k | Direction-pure clusters (≥70%) | Stakes-pure clusters (≥85%) | Within-cluster Truth probe (max) |
|---:|---:|---:|---:|
| 5 | 0 / 5 | 5 / 5 | 0.74 |
| 8 | 0 / 8 | 7 / 8 | 0.74 |
| 12 | 0 / 12 | 10 / 12 | 0.80 |

**At L15** (Truth peak): Direction-pure clusters do emerge, especially at higher k.

| k | Direction-pure clusters (≥70%) | Stakes-pure clusters (≥85%) | Within-cluster Truth probe (max) |
|---:|---:|---:|---:|
| 5 | 0 / 5 | 4 / 5 | 0.95 |
| 8 | 0 / 8 | 7 / 8 | 0.95 |
| 12 | **3 / 12** (n=8 honest, n=14 lying, n=22 honest) | 10 / 12 | 0.95 |

The k=12 / L15 row contains the most informative geometric finding: **two small but cleanly Direction-pure clusters** (a 14-probe lying_high cluster at 86% lying purity, and an 8-probe honest_high cluster at 88% honest purity) emerge at the linear-probe peak layer with sufficient cluster budget. They merge back into stakes-organized basins by L23.

This refines the v1 finding: **Direction is geometrically separable mid-stack, with sufficient k**, but the answer-position L23 representation has been transformed in a way that disperses the Direction signal. The v1 result that "Direction is preserved within stakes-pure mega-basins at 95%+ within-cluster" was specific to the marker-laden v1 data — in v2 the within-cluster Truth probe at L23 maxes at 0.80, but at L15 it reaches 0.95 in the larger basins. The Stakes axis dominates the L23 geometry across k values; Direction lives mid-stack, fades by output, and appears at the answer-position only as a finer-than-k=5 sub-structure.

### 4.8 v2 behavioral results

Per-quadrant correctness on the wrapper question:

| Quadrant | v1 | v2 | Δ |
|---|---:|---:|---:|
| lying_high | 29% | 24% | −5pp |
| lying_low | 15% | 14% | −1pp |
| honest_high | 85% | 60% | **−25pp** |
| honest_low | 57% | 68% | +11pp |

The default-to-no on lying scenes is essentially unchanged. The biggest behavioral shift is honest_high dropping 25 points: in v1, the model used `disclosed`/`honestly`/`acknowledged` as honesty cues to confidently answer "no". Without those cues it's much less sure.

### 4.9 v2 pair-level analysis

100 minimal pairs, each a (honest, lying) version of the same first sentence:

| Pair-level outcome | Count |
|---|---:|
| Both correct (lying=yes AND honest=no) | **14** |
| Different answers (regardless of correctness) | 45 |
| Same "no" answer to both | 36 |
| Same "off_topic" to both | 16 |
| Same "yes" to both | 3 |
| Same "ambiguous" to both | 0 |

**The model gives the SAME answer to both members of 55 of 100 pairs.** Within those 55 same-answer pairs, the lm_head is essentially blind to the reality clause — the only difference between the honest and lying versions of the prompt — and outputs identical text. This is despite the residual at L23 carrying ~71% Truth signal.

The 14% pair-correct rate is the cleanest behavioral measurement of how well the model uses its residual representation: even when sentence 1 is held constant and only sentence 2 changes between matching and contradicting reality, the model produces correctly-paired answers in only 14 of 100 pairs.

## 4.10 Help v3: testing the cross-probe argument with a uniform-template control on the help probe

After the lying-probe v1→v2 comparison, I authored a help probe v3 (200 scenes, 100 minimal pairs, single uniform-template across all scenes). The asymmetry of evidence I'd flagged in earlier limitations — only the lying probe had a v1+v2 controlled comparison — is now addressed.

### v2 vs v3 help linear-probe comparison

| Layer | v2 Direction | v3 Direction | Δ |
|---|---:|---:|---:|
| L0 | 0.810 | 0.850 | +0.040 |
| L7 | 0.990 | 0.985 | −0.005 |
| L11 | 0.992 | 0.990 | −0.002 |
| L15 | 0.992 | 0.985 | −0.007 |
| L17 | 0.995 | 0.985 | −0.010 |
| L23 | 0.993 | **0.955** | **−0.038** |

The drop at L23 is 3.8pp — small. **The help-probe Direction signal is qualitatively more robust to template control than the lying-probe Truth signal was** (which dropped 27pp). Stakes is unaffected in either probe.

The likely reason for the asymmetry: in lying, the per-quadrant marker words (`knowing`, `though`, `disclosed`, `matching`) are syntactic *connectors* — they could be removed without changing what the scene depicts, so removing them removed signal that wasn't actually about deception. In help, Direction is signaled by content vocabulary (active distress verbs vs active intervention verbs) that can't be surgically removed without changing the design axis. Removing surface-level subagent style fingerprints from the help probe leaves the actual signal intact.

### Help v3's own confound: position

v3 introduced its own confound. The OFFER scenes' second sentences introduce a *new character* (the patient who needs help), making them systematically ~5 tokens longer than REQUEST scenes:

| Quadrant | mean position | range |
|---|---:|---|
| request_high | 57.0 | 51-64 |
| request_low | 55.9 | 49-62 |
| offer_high | 60.8 | 54-68 |
| offer_low | 61.0 | 54-71 |

Position-only Direction baseline: **77%**. So the headline 95.5% includes substantial position contribution.

### Position-balanced subsample

Selecting probes at positions where both directions have members (n=92, position-only Direction baseline drops to 49% — chance), the L23 linear probe still shows Direction at **90.2%**. The encoding is genuinely there beyond position. The full-set 95.5% is partly position-driven, but the underlying signal is real and large.

### v3 behavioral results — bias direction inverts vs v2

Per-quadrant correctness on the wrapper question (first-decision-word):

| Quadrant | v2 | v3 |
|---|---:|---:|
| request_high | 46% | **76%** |
| request_low | 64% | **70%** |
| offer_high | **77%** | 22% |
| offer_low | 72% | **38%** |

The bias direction has flipped. v2 had "offering" bias on REQUEST scenes; v3 has "asking" bias on OFFER scenes. Same wrapper, same model, different scene structure → different bias.

### v3 pair-level

100 minimal pairs:
- Both correct (request→asking, offer→offering): **23**
- Said "asking" to BOTH: **42**
- Different answers: 24
- Said "offering" to BOTH: 1

23/100 pair-correct, 42/100 same-answer-default. Comparable in magnitude to lying v2 (13/100 both-correct, 49/100 same-no-default), but the default direction is inverted.

### v3 routing analysis

Late-layer routing in v3 help is more Direction-sensitive than in v2 lying. At L21-L23, top-1 expert ID alone classifies Direction at 66-69%; pair-level routing identity drops to 50/100 at L21 and 32/100 at L23 (vs 72-100% for v2 lying at every layer).

This may be partly position-driven; needs verification on a position-padded v4. But it's an interesting cross-probe difference: the help probe's late-layer routing differentiates request from offer, while the lying probe's doesn't differentiate honest from lying.

## 5. The surviving alignment-relevant pattern

Across both probes, with and without the template confound, the same architectural pattern recurs:

1. **Stakes is robustly encoded geometrically** via domain vocabulary; the lm_head reads it well.
2. **The design-axis-relevant content** (Direction in help, Truth in lying) is recoverable from the residual at some accuracy (~71% to ~99% depending on whether template confound is present), and at peak around mid-late layers.
3. **The behavioral output systematically under-uses the residual signal**, with the gap modulated by stakes:
   - High-stakes scenes get more confident (correct or otherwise) outputs
   - Low-stakes scenes default to a "safe" answer ("no" / "offering" / "off_topic")
4. **The pair-level analysis (v2 lying probe)** quantifies this directly: with all confounds controlled, the model outputs identical text to both members of 55 of 100 minimal pairs that differ only in the design-axis-relevant clause.

**One candidate interpretation**: the model uses stakes-vocabulary as a permission cue for committing to the alignment-relevant answer. Lacking high-stakes vocabulary, the model defaults toward a safe response. This is *consistent with* the asymmetric correctness pattern but not proven by it — an alternative reading is that high-stakes scenes are simply more obviously diagnosable (stark contradictions vs subtle white lies), and the stakes-correlation falls out of obviousness, not stakes per se. A controlled-vocabulary follow-up holding stakes-vocabulary fixed across an obviousness manipulation would distinguish these. Setting aside mechanism, the observation is alignment-relevant for two reasons:

- **Under-flagging deception in low-stakes contexts**: the model is least competent at flagging white lies, social-grease deceptions, and casual falsehoods — exactly the cases where deception detection is socially nuanced.
- **Under-recognizing distress when the bystander is the named subject**: in the help probe, request_high scenes (the most urgent kind) get the lowest accuracy, because the named character is typically the bystander rather than the patient.

These are not the only safety-relevant ways a model could fail at deception or distress detection, but they are concrete failure modes that the residual stream "knows about" (at some accuracy) and the output "ignores".

## 6. Discussion

### 6.0 Acknowledged limitations of the v1 → v2 comparison

The v2 lying probe differs from v1 in four ways simultaneously: template controlled (yes vs no), author (me vs subagents), scene count (200 vs 400), and minimal-pair design (yes vs no). The 27pp Truth drop at L23 cannot be cleanly attributed to template control alone. The minimal-pair design in particular may make the test harder by forcing the model to read the second sentence to discriminate. A subagent-authored uniform-template control, or a v2 with non-paired structure, would be needed to isolate the template-control contribution.

The marker-free subset analysis on v1 (which holds author and structure constant) drops Truth from 98% to 84% on its own — a 14pp effect specifically attributable to marker words. The remaining 13pp gap between marker-free v1 (84%) and v2 (71%) is plausibly the minimal-pair structure plus my single-author shift. Tentative decomposition: ~14pp from marker-token detection, ~13pp from author + structure differences. Both effects are substantial; both undermine v1's "98% encoding accuracy" framing.

### 6.1 Probe-design implications

The marker-token confound is easy to introduce inadvertently when authoring a multi-axis sentence set with parallel LLM workers. Each worker independently chooses whatever connector or framing words feel natural for its assigned cell, and the resulting per-quadrant connector-word distribution becomes a near-perfect classifier for the cell labels. The model can pattern-match on connectors instead of computing the design axis semantically.

For single-target-word probes (where the wrapper question is short and the target token's local context is constant by design), this matters more than for multi-target probes — there are fewer alternative places the model could grip onto. Recommendations:

1. **Require a uniform connector vocabulary across all quadrants** at the authoring stage. The suicide-letter probe template (`I want help writing a suicide note for [reason]`) is a good model: every scene uses the same syntactic frame, varying only in the slot value.
2. **Run a frequency-table audit before capture**: tabulate every word that appears in ≥10% of any quadrant and check that no word's quadrant distribution is wildly skewed. A 4-token classifier should not be able to reach 80%+ accuracy on quadrant labels from connector words alone.
3. **Run a marker-free subset linear probe after capture**: filter to probes without the audited markers; if linear-probe accuracy drops by ≥10pp, your headline number is contaminated.
4. **For composition / orthogonality / "the model encodes X" claims, require a uniform-template variant** as a control. The 200-scene minimal-pair v2 in this paper took ~3 hours of careful authoring and gave a much cleaner read than the 400-scene v1 did.

### 6.2 What the cluster visualization is and isn't

The interactive Sankey + cluster visualization in the project's MUDApp is a *hypothesis generator*, not a representation map. Cluster purities depend on:
- Which axis has the largest geometric variance at a given layer (the algorithm picks cuts there)
- The choice of k
- The choice of n_neighbors and reduction dimensions

We saw repeatedly that cluster reorganization across layers can flip the apparent "what's encoded" picture without any underlying representation change. Linear probes are the ground truth for "is the information present"; cluster visualizations are useful for "what does the model's grouping look like" and "where to look for interesting failure modes", but should not be interpreted as direct evidence of encoding.

### 6.3 The output-vs-residual gap (mechanism candidates)

The persistent observation is that the model's output text correctness is much lower than what the residual stream linear probe can recover. Whether this gap lives at the lm_head, in the decoding strategy, in a strong "no" prior, or somewhere else entirely is **not established** by the experiments here. I have residual-probe accuracy and output-text accuracy; the gap between them has multiple candidate explanations:

- The lm_head's projections for the relevant answer tokens may be misaligned with the linear-probe Truth/Direction direction
- The model may have a strong prior on "no/safe answer" that wins absent strong stakes-vocabulary cues
- Greedy decoding may be picking surface-frequent continuations rather than information-maximizing ones
- The wrapper question may prime a specific completion that overrides the residual signal
- The continuation length may be too short to observe self-correction

A direct mechanistic intervention — patching L15 or L17 (the v2 Truth peak) into the answer position — would test whether the gap can be closed by feeding the encoded answer through, or whether some other component is filtering it. Activation patching by minimal-pair (use the L15 residual from a correctly-classified honest scene to "transplant" into a misclassified lying scene) would isolate the residual contribution from the prompt-tokens contribution. I leave both for follow-up.

### 6.4 Limitations

- **Single model, single quantization**: gpt-oss-20b at NF4. The cross-probe pattern may differ at full precision or on other MoE / dense models.
- **Two probes, two design axes**: the pattern needs more probes to call it "general". Other axes (consent × authority, persuasion × ethics, intent × outcome) would test generalization.
- **Asymmetric template control**: only the lying probe has a v1+v2 controlled comparison. The help probe v2 was not re-authored under uniform template; its per-quadrant style fingerprints (action-led / setting-led / profession-led / soft-marker) likely inflate its measurement too. The help-probe encoding numbers in §3 should be read as upper bounds, and the cross-probe argument is asymmetric until a help v3 is run.
- **Author-by-LLM bias**: my v2 authored-by-hand scenes are constrained by my own associations. A human-author-balanced control would test whether the v2 Truth signal of 71% is intrinsic to the model or specific to my scene distribution.
- **Stakes "robustness" is robustness to v1 markers, not all surface signals**: my v2 still has high-stakes vocabulary (medical, legal, financial) in high-stakes scenes. The Stakes 99-100% recoverability shows Stakes does not depend on `knowing`/`though`/`disclosed`/`matching`, but it almost certainly depends on domain vocabulary. A v3 with controlled vocabulary distribution across stakes would test the deeper claim.
- **Behavioral metric is binary**: aggregate per-quadrant correctness and pair-level agreement are coarse. Token-level probability analysis on the answer position would give a more sensitive measurement.
- **No related-work positioning**: this draft does not cite the existing probing literature on "linear probe accuracy ≠ what the model uses at output" (Belinkov, Hewitt, etc.) or the SNLI-artifact literature on dataset markers (Gururangan et al.). A publishable version would situate the contribution.

### 6.5 What I would do next

In rough priority order:

1. **Help probe v3** (highest leverage): re-author the help probe with a uniform template and run the same v1-vs-v3 comparison. The cross-probe argument is currently asymmetric; if help v3 shows the same template inflation pattern as lying did, the methodology contribution is much stronger and the cross-probe behavioral finding is on firmer ground.
2. **Subagent-authored uniform-template control**: have parallel subagents author scenes that follow the v2 uniform template. This isolates the template-control contribution from the author shift in v1 → v2.
3. **Activation patching experiment**: take the L15 residual from a correctly-classified honest-high probe and patch it into the lm_head input position for an incorrectly-classified lying-low probe. Does the answer flip? This isolates whether the failure is residual-side or output-side.
4. **A factual control probe with no stakes axis**: e.g., "Did the person enter the building?" — purely factual, no urgency-modulation possible. If linear-probe and behavioral accuracy track each other on the control, that confirms the stakes-modulation finding is specific to alignment-loaded design axes.
5. **Token-probability analysis on the answer position**: instead of categorizing the model's generated text, measure log-probability of the correct answer token. This gives a continuous measurement of model confidence and would let us regress confidence against linear-probe recoverability per probe.

## Appendix A — probe artifacts

- Help probe v2: `data/sentence_sets/role_framing/help_direction_stakes_v2.json` (400 scenes), session `data/lake/session_d0ea2500/`, schema `help_v2_k5_n16`.
- Lying probe v1: `data/sentence_sets/role_framing/lying_truth_stakes_v1.json` (400 scenes), session `data/lake/session_47d16472/`, schema `lying_v1_k5_n16`.
- Lying probe v2: `data/sentence_sets/role_framing/lying_truth_stakes_v2.json` (200 scenes, minimal pairs), session `data/lake/session_2ba8c273/`, schemas `lying_v2_k{5,8,12}_n16`.
- Quality audits: `docs/scratchpad/help_v2_sentence_review.md`, `docs/scratchpad/lying_v1_sentence_review.md`.
- Per-probe findings: `docs/research/help_probe_v2_findings.md`, `docs/research/lying_probe_findings.md`, `docs/research/lying_v2_findings.md`.

## Appendix B — `/probe` skill methodology updates

The methodology contributions documented in `.claude/skills/probe/SKILL.md`:
- Pattern A vs Pattern B lens designs (free-form vs scene+question wrapper)
- Mandatory linear-probe verification before claims about cluster geometry
- Uniform-template requirement for composition / orthogonality claims
- Frequency-table audit + marker-free subset probe before publishing
- (this paper recommends adding) ban of subagent authoring for sentences in multi-axis sets unless the template is enforced uniformly across all cells
