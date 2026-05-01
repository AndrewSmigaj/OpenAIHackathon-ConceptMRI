# Lens choice and layer trajectory in residual-stream cluster geometry

**Working draft, 2026-04-29.** Studies conducted on Open LLMRI targeting `gpt-oss-20b` (NF4-quantized 20B-parameter MoE language model).

## Abstract

We report two studies of residual-stream cluster geometry on a 20B-parameter MoE language model, conducted to characterize how design choices in probe construction shape what cluster analysis reveals about model representations.

**Study 1 (calibration)** validates the platform pipeline against two probes designed to elicit known-clean separation: a binary fictional-vs-real-context "suicide letter" probe (V_label = 0.99 at peak layer; signal stable from L4 onwards), and a 5-way polysemous-word "tank" probe (V_label = 0.76, near the natural ceiling for a 5-way design). The two probes show different layer-trajectory shapes: the easy binary signal is established early and persists; the harder 5-way signal builds through middle layers and partially dissolves toward the output.

**Study 2 (lens choice)** holds 200 hand-authored scenes constant across six different appended-phrase scaffolds and target-word choices ("lenses"), and measures how the cluster-membership signal V_truth varies for the same scenes under different lenses. We find: V_truth ranges from **0.238 to 0.402** across the six lenses on identical scenes. The minimum-vs-maximum ratio is 1.69. A complementary cross-probe finding on a "help" probe with strong syntactic markers shows V_direction is comparable across lenses (0.876 → 0.923), suggesting lens-sensitivity is concentrated on semantically subtle axes that lack surface markers.

The two studies together show that **(a) the platform pipeline detects known-clean structure with expected magnitudes**, and **(b) for semantically subtle axes, lens choice substantially shapes the geometry the analyst recovers**. Methodologically, single-lens single-V analyses on subtle axes should be reported with explicit lens specification and ideally compared against multiple lens variants.

## 1. Introduction

The Open LLMRI platform performs interpretability research on Mixture-of-Experts (MoE) language models by capturing residual-stream activations at a designated target token position, applying UMAP-based dimensionality reduction (typically to 6 dimensions), then performing hierarchical clustering at that layer. The result is a per-layer cluster assignment for each probe in a designed sentence set. Repeated across all model layers, the platform produces a layer-by-layer trajectory of how the model's hidden state organizes across probes.

The standard analysis associates cluster membership with design-axis labels using a contingency-table statistic such as Cramer's V. High V is taken as evidence that the model encodes the design axis at this layer. Two questions immediately arise:

1. **Does the pipeline produce expected V values on probes designed for known-clean separation?** Without calibration, individual V values are uninterpretable.
2. **How sensitive is V to the specific scaffolding around the target word?** Different appended phrases ask the model to do different things; the residual at the target token reflects whatever upstream context exists. If V varies substantially with scaffolding choice, lens specification becomes a load-bearing methodological detail.

We address each question with a separate study. Both use the same model, pipeline, and analysis machinery; the manipulations are at the probe-design level.

## 2. Methods

### 2.1 Platform and model

All studies use `gpt-oss-20b` (the open-source 20B-parameter MoE model from OpenAI's GPT-OSS series), quantized to 4-bit NF4 to fit a single consumer GPU. The model has 24 transformer layers and 32 MoE experts per layer with top-1 expert selection. Per-layer residual stream activations are captured at the designated target token position for each probe.

### 2.2 Cluster pipeline

For each captured session, the platform:
1. Captures 24 per-layer 2880-dim residual vectors per probe (one per layer).
2. Reduces to 6 dimensions per layer using UMAP (`n_neighbors=15` standard, swept where noted in §3).
3. Applies hierarchical clustering with `k=6` clusters per layer (also swept where noted).
4. Records each probe's cluster assignment at each layer.

The standard analysis is then a contingency table between cluster assignment and a design label, summarized by Cramer's V or by reading the contingency table directly.

### 2.3 Probe construction

Each probe is a hand-authored prompt fed to the model. The platform uses the residual at a `target_word` position; where multiple occurrences exist, `last_occurrence_only=true` selects the final occurrence. Generation is enabled and the generated text is stored alongside the residuals for behavioral observation.

For Study 2, we author multiple "lens variants" applied to the same set of scenes to test how scaffold choice affects geometry, holding content constant.

## 3. Study 1: Calibration on known-clean probes

**Question.** Does the pipeline detect known-clean cluster structure when it should?

**Probes.**
- `suicide_letter_framing_v1` — 198 prompts (99 fictional-creative-work framings, 99 real-life-context framings) with target word `want`. Each prompt is of the form "In the [story/novel/D&D campaign/...] I want to write a suicide note for [reason]" or analogously framed in a real-life context. The fictional-vs-real-life-context distinction is known to produce strong residual-stream separation in this kind of scaffold.
- `tank_polysemy_v3` — 499 prompts (≈100 each across 5 senses: aquarium, vehicle, scuba, septic, clothing) with target word `tank`. Polysemous-word probes are a standard test bed for distributional representation.

**Setup.** Schemas built at `k=6` and `n_neighbors ∈ {8, 15, 20, 30}` for both probes. V_label computed at each layer.

### 3.1 Suicide letter — V_label = 0.99 at peak

Across all `n_neighbors` settings, V_label peaks at 0.98–0.99 in the L4–L17 region. Best result: V = 0.990 at L15 with n=8. At n=30 L11, 5 of 6 clusters are 100% pure on the fictional/real-life label (50/50 fictional, 48/48 real, 26/26 real, 39/39 fictional, 23/23 real); only one cluster is mixed (10 fictional + 2 real). The model encodes this binary distinction nearly perfectly across most of the network.

### 3.2 Tank polysemy — V_label = 0.76 at peak (near 5-way ceiling)

V_label peaks at **0.756** at L14 (n=30) — close to the natural ceiling for a 5-way classification with balanced classes. At n=15 L11, 4 of 6 clusters are near-pure on a single sense (clothing 97%, aquarium 91%, vehicle 94%, scuba 100%); one cluster is septic-skewed with scuba bleed; one is a residual mixed cluster. n_neighbors choice has small effects (peak V varies 0.72–0.76 across n=8/15/20/30).

### 3.3 Trajectory shapes differ by signal-difficulty

| Probe | V at L0 | Peak V (layer) | V at L23 | Trajectory shape |
|---|---:|---:|---:|---|
| Suicide letter | 0.71 | **0.99 (L15)** | 0.91 | early-and-stable: settled by L4, modest dissolve |
| Tank polysemy | 0.30 | **0.76 (L14)** | 0.63 | form-peak-dissolve: gradual build, mid-layer peak, ~17% drop by L23 |

The easy binary signal is essentially settled in early-to-middle layers. The harder 5-way signal requires more layers to crystallize and partially dissolves at the output, consistent with the residual rotating toward next-token prediction.

### 3.4 Calibration baselines for §4 and beyond

- V_label ≈ 0.99 is "as good as it gets" on a binary design.
- V_label ≈ 0.76 is the practical ceiling on a 5-way design.
- Trajectory shape varies by signal-difficulty.
- `n_neighbors` choice has small effects (V varies by ~0.01–0.04 across {8, 15, 20, 30}); `n=15` is a reasonable default for routine analysis.

These baselines situate the lens-comparison study results in §4.

## 4. Study 2: Lens choice on lying and help probes

**Question.** Holding scenes constant, how much does cluster geometry depend on the appended-phrase scaffolding and target-word choice for inspection?

### 4.1 Probe construction

We hand-authored 200 scenes for a "lying probe" (50 per quadrant of Truth × Stakes design: lying-high, lying-low, honest-high, honest-low) and a separate 200-scene "help probe" (50 per quadrant of Direction × Stakes: asking-high, asking-low, offering-high, offering-low). Each scene is a short naturalistic prose vignette using a single named character ("Jordan") and following a constant template structure (`Jordan told [audience], "[claim]." The [evidence] showed [reality].`).

For the lying probe, we then applied **six different lenses** — different appended phrases and target words — to the same 200 scenes. The lying probe captures with each lens are independent sessions; the scenes are byte-identical across lens variants.

### 4.2 Lenses tested (lying probe)

| Variant | Target | Appended phrase example |
|---|---|---|
| v3 baseline | `lying` | `Is the person lying or being honest? Are the stakes high or low? List answers single word separated by a comma:` |
| v5 opt1 | `answer` | `Questions: Is Jordan lying or telling the truth and are the stakes high or low? Please provide the answer.` |
| v5 opt2 | `situation` | `Questions: Answer whether Jordan is lying or not and whether the stakes are high or not in this situation.` |
| v5 opt3a | `is` | `Questions: Fill in the blanks. Jordan is ___ and the stakes are ___.` (target: last `is`) |
| v5 opt3b | `are` | (same prompt as opt3a) (target: last `are`) |
| v5 opt4 | `here` | `What is going on here?` |

### 4.3 Results: V_truth varies substantially across lenses; V_stakes does not

| Variant | V_quadrant peak | V_stakes peak | V_truth peak |
|---|---:|---:|---:|
| v3 baseline (`lying`) | 0.558 (L15) | 0.874 (L11) | 0.305 (L15) |
| opt1 (`answer`) | 0.508 (L5) | 0.846 (L10) | 0.256 (L3) |
| opt2 (`situation`) | 0.576 (L13) | **0.935** (L13) | 0.238 (L14) |
| opt3a (`is`) | 0.537 (L16) | 0.884 (L23) | 0.335 (L3) |
| opt3b (`are`) | 0.558 (L16) | 0.901 (L16) | 0.277 (L20) |
| opt4 (`here`) | 0.547 (L12) | 0.872 (L9) | **0.402** (L15) |

V_stakes is uniformly high (0.85–0.94) across all six lenses. V_truth varies more substantially: from **0.238** (constrained-choice opt2) to **0.402** (minimal-scaffolding opt4). Absolute spread is 0.164 V-units; the higher V is 69% larger than the lower. Both extremes are on the same 200 scenes — the only thing that differs is the scaffolding wrapped around them.

The minimum-scaffolding lens (opt4, `What is going on here?` with target=`here`) gives the strongest truth-axis signal. The constrained-choice lenses (opt1, opt2 — which explicitly ask the model to commit to a binary) give the weakest. The dual-blank lens (opt3a/3b — `Jordan is ___ and the stakes are ___`) sits in between, with each blank-position target giving a moderate signal for its corresponding axis.

### 4.4 Cross-probe replication on the help probe

The same lens-swap was applied to a separate 200-scene "help" probe (Direction = asking vs offering × Stakes = high vs low). V_direction is comparable across lenses:

| Variant | V_quadrant peak | V_direction peak | V_stakes peak |
|---|---:|---:|---:|
| help v4 baseline (`help`) | 0.907 (L14) | 0.904 (L14) | 0.961 (L12) |
| help v5 opt4 (`here`) | 0.847 (L12) | 0.923 (L12) | 0.835 (L9) |

V_direction differs by only 0.019 across these two lens variants. **The help probe's direction axis is robust to lens choice, while the lying probe's truth axis is not.**

### 4.5 Why lenses matter for some axes but not others

The likely explanation is the difference between **syntactic** and **semantic** signal:

- **Help direction (asking vs offering)** is signaled by syntactic markers in English: `Could you...` for asking, `I'll...` / `Let me...` for offering. These markers appear in the scene prose and their representations propagate to the target token regardless of the lens. The signal is already strong; the lens doesn't have much to add or subtract.

- **Lying truth (lying vs honest)** depends on a *relation* between the claim asserted and the reality clause that follows. There's no comparable syntactic shortcut; the model must integrate the two clauses to determine truth value. Lens choice affects how the model integrates that information at the target position.

Constrained-choice lenses (asking the model to commit to a binary "lying or honest") may contaminate the residual with answer-prediction features that scramble subtle scene-comprehension structure. Open-ended lenses (`What is going on here?`) leave the residual as a "comprehension" representation before the model has been pushed toward any particular answer format.

### 4.6 Cluster characterization at the best-truth lens (opt4 L15)

At the layer where V_truth peaks (L15 in opt4), the cluster geometry recovers content-meaningful semantic categories:

| Cluster | n | Truth purity | Character |
|---:|---:|---:|---|
| C3 | 25 | 84% honest | low-stakes domestic admissions ("their spouse", "their sibling", roommate) |
| C4 | 23 | 74% honest, all high stakes | formal disclosures / whistleblowing (court, federal prosecutor, DEA, asylum officer) |
| C5 | 17 | 88% lying | formal deceit (EPA inspector, ethics committee, internal affairs, grand jury) |
| C2 | 32 | 59% honest, all high stakes | institutional contexts where truth is ambiguous (SEC, dissertation committee, elections board) |
| C0 | 63 | 62% lying | everyday relational, lying-leaning |
| C1 | 40 | 57% lying | mostly low_stakes, mixed |

The model's residual stream at L15 has organized scenes into content-meaningful semantic categories that the design didn't explicitly label: domestic-honest disclosure (C3) is geometrically distinct from formal-honest disclosure (C4), and from formal deceit (C5). The geometric partition lines up with intuitive content categories the analyst can read off the scenes themselves.

## 5. Discussion

### 5.1 Implications for analytical practice

Three implications follow:

1. **Calibration is necessary.** Without baseline V values from known-clean probes, individual V scores are uninterpretable. A V of 0.30 is "weak" against the suicide-letter calibration but "in the same range as truth-axis signal" against the lying-probe calibration — it depends on what "good" looks like for the design at hand.

2. **Lens choice matters where signal is semantically subtle.** For axes signaled by surface syntactic markers (asking-vs-offering with `Could you...` / `I'll...`), the residual at the target token has substantial signal regardless of scaffolding. For axes signaled by *relations* between scene elements (lying-vs-honest depending on claim-vs-reality alignment), the model has to integrate, and the integration is shaped by what the model thinks it's being asked to do at the target position. Lens choice is load-bearing.

3. **Open-ended scaffolding is often better for subtle axes.** Constrained-choice prompts ("answer X or Y") seem to contaminate the residual with answer-prediction structure that interferes with concept representation. Open-ended prompts (`What is going on here?`) preserve the model's "comprehension" representation. This was unexpected; it suggests that for studies where one wants to probe what the model has *understood*, less scaffolding is sometimes more.

### 5.2 Implications for layer-trajectory interpretation

The two probes in §3 plus the lying-probe results in §4 together suggest a working taxonomy of trajectory shapes:

- **Early-and-stable**: easy binary signal, settled by L1–L4, persists through L23. (Suicide letter.)
- **Form-peak-dissolve, modest**: moderate-difficulty signal, builds through middle layers, peaks somewhere in L11–L17, partial dissolve at output. (Tank polysemy, help direction, lying stakes.)
- **Form-peak-dissolve, sharp**: harder signal, similar shape but more pronounced dissolve. (Lying truth.)

These shapes are consistent with the residual stream first integrating concept information through the middle layers and then rotating toward output-token prediction in late layers. Concepts that are "settled" early (because they're surface-recognizable) stay throughout; concepts that require relational integration crystallize mid-depth and partially dissolve.

### 5.3 What the studies do not establish

- **Single-lens results are not necessarily wrong**, but they should be reported with explicit lens specification. A V of 0.40 on the truth axis at one lens is a meaningful finding under that lens; it shouldn't be generalized to "the model encodes lying-vs-honest at strength 0.40."
- **Lens-sweeps are not free**: each lens is a separate capture. For studies with limited compute, choosing one or two thoughtful lenses is reasonable; lens-sweeps are most valuable when the substantive question depends on the lens choice.
- **The trajectory taxonomy is preliminary.** Three trajectory categories from a handful of probes is not a typology; it's a starting hypothesis worth testing against more probes.

## 6. Limitations

- **Single model.** All studies use `gpt-oss-20b` NF4-quantized. Findings about lens-sensitivity and trajectory shape may not transfer to other model families, sizes, or architectures.
- **Single position per study.** All captures use the residual at one specific target-word position. The lens-comparison varies the position, but each capture is at its single chosen target. Multi-position capture per probe is a natural follow-up.
- **The lens-comparison results are descriptive.** We don't have a causal account of *why* opt4 wins on truth axis. Activation-patching experiments could test specific hypotheses (e.g., is constrained-choice scaffolding contaminating the residual with answer-prediction features?).
- **Behavioral output was not the focus** of these two studies. The §4 lens-comparison shows generation degeneracy under constrained-choice prompts (the model meta-reasons about format rather than answering); we noted this as descriptive context but did not analyze it systematically.
- **The 200-scenes-per-quadrant designs in §4 give moderate statistical power.** Effect sizes are large enough that the conclusions are not threatened, but precision-bound estimates would benefit from N in the thousands.

## 7. Future work

- **Multi-position capture** per probe: capture residuals at multiple positions within each prompt to localize where the lens effect lives.
- **Activation patching** to test specific mechanistic hypotheses (e.g., does patching the opt2 residual's "answer-prediction features" into an opt4 forward pass collapse the truth signal?).
- **Cross-model replication** on a different model family / size to test whether the lens-sensitivity of subtle axes generalizes.
- **Trajectory typology expansion**: more probes covering different signal-difficulties to test the early-and-stable / form-peak-dissolve taxonomy.
- **Statistical-power expansion**: scale the lens-comparison to ~1000 scenes per lens for tighter V estimates.

## Appendix A: Per-layer V tables

Per-layer Cramer's V values for both probes and all lens variants are recorded in:
- `docs/scratchpad/lying_v3_per_layer_contingency.csv`
- `docs/scratchpad/help_v4_per_layer_contingency.csv`
- (Tank polysemy and suicide letter per-layer V tabulated in §3.)

## Appendix B: File pointers

Sentence sets:
- `data/sentence_sets/role_framing/lying_truth_stakes_v3.json` (the 200 lying-probe scenes; reused across all six lenses)
- `data/sentence_sets/role_framing/lying_truth_stakes_v5opt{1,2,3a,3b,4}.json` (lens variants of lying probe)
- `data/sentence_sets/role_framing/help_direction_stakes_v4.json` and `help_direction_stakes_v5opt4.json`
- `data/sentence_sets/role_framing/suicide_letter_framing_v1.json`
- `data/sentence_sets/polysemy/tank_polysemy_v3.json`

Findings docs (longer-form work products):
- `docs/research/calibration_sweep_suicide_polysemy.md`
- `docs/research/lying_v5_lens_comparison.md`
- `docs/research/lying_v3_help_v4_findings.md`
