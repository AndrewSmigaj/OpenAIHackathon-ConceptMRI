# Lying probe v5 — lens comparison

**Date**: 2026-04-28
**Question**: how does the choice of target word + scaffolding format change what the residual-stream cluster geometry reveals about the truth axis?
**Same scenes throughout**: 200 v3 lying-truth-stakes scenes (50 per design quadrant). Only the appended phrase + target word changes.

## Variants tested

| Variant | Session | Target | Appended phrase |
|---|---|---|---|
| v3 baseline | `session_4a738248` | `lying` | `Is the person lying or being honest? Are the stakes high or low? List answers single word separated by a comma:` |
| v5 opt1 | `session_6e34626d` | `answer` | `Questions: Is Jordan lying or telling the truth and are the stakes high or low? Please provide the answer.` |
| v5 opt2 | `session_62ff70ff` | `situation` | `Questions: Answer whether Jordan is lying or not and whether the stakes are high or not in this situation.` |
| v5 opt4 | `session_8a76c4c4` | `here` | `What is going on here?` |

All schemas built with k=6, n_neighbors=15, UMAP-6D, hierarchical clustering, residual stream, last_occurrence_only=true.

## Headline

**Minimal scaffolding (opt4: "What is going on here?" with target=`here`) gives the strongest truth-axis cluster geometry.** V_truth peaks at 0.402 at L15 — a 32% improvement over the v3 baseline (0.305) and a 60–70% improvement over the constrained-choice variants (opt1: 0.256, opt2: 0.238).

The constrained-choice prompts (opt1, opt2) that explicitly ask the model to commit to a binary actually *weaken* the truth signal in the residuals, not strengthen it.

## Per-axis Cramer's V comparison (peak across all layers)

| Variant | Target | Lens type | V_quad peak | V_stakes peak | V_truth peak |
|---|---|---|---:|---:|---:|
| v3 baseline | `lying` | question word | 0.558 (L15) | 0.874 (L11) | 0.305 (L15) |
| opt1 | `answer` | constrained-choice end | 0.508 (L5) | 0.846 (L10) | 0.256 (L3) |
| opt2 | `situation` | exhaustive-explicit end | 0.576 (L13) | **0.935 (L13)** | 0.238 (L14) |
| **opt4** | **`here`** | **minimal scaffolding** | 0.547 (L12) | 0.872 (L9) | **0.402 (L15)** |
| opt3a | `is` | dual-blank (truth pos) | 0.537 (L16) | 0.884 (L23) | 0.335 (L3) |
| opt3b | `are` | dual-blank (stakes pos) | 0.558 (L16) | 0.901 (L16) | 0.277 (L20) |

## Dual-blank lens (Option 3) — partial validation, with caveats

The dual-blank prompt `Jordan is ___ and the stakes are ___.` was captured twice — once at the `is` token (right before the truth blank) and once at the `are` token (right before the stakes blank). Hypothesis: the residual at each blank's preceding token would isolate that axis.

**Result**: position-isolation works *partially* for stakes (opt3b V_stakes=0.901, second-best) but only *modestly* for truth (opt3a V_truth=0.335, second-best to opt4's 0.402). And in opt3a, V_stakes (0.884) is still much higher than V_truth (0.335) — even at the position right before the truth blank, the residual carries stronger stakes than truth signal.

This is informative about transformer attention: positioning a token right before an answer slot doesn't override the model's overall scene representation. Stakes is intrinsically the easier-to-encode axis (audience role, register, severity vocabulary), and that signal dominates the residual at any position in the appended phrase. Local priming via blank-positioning helps but doesn't isolate.

**Conclusion on lenses tested:**
- For maximum truth-axis signal: **opt4** (`What is going on here?`, target=`here`) — minimal scaffolding, model encodes scene comprehension cleanly without commitment to a forced answer format.
- For maximum stakes-axis signal: **opt2** (exhaustive explicit prompt, target=`situation`) — verbose framing primes a strong stakes representation.
- No single-target lens captures both axes optimally. If both are wanted, run two captures (e.g., opt4 + opt2) and compose the results.

## V_truth trajectory across layers

The shapes differ more meaningfully than the peaks:

```
Layer  v3      opt1    opt2    opt4
  0    0.063   0.148   0.118   0.115
  3    0.139   0.256   0.145   0.311
  5    0.169   0.170   0.123   0.286
  9    0.185   0.136   0.112   0.228
 11    0.086   0.204   0.217   0.252
 12    0.181   0.075   0.224   0.364   ← opt4 climbing
 13    0.096   0.112   0.228   0.303
 14    0.186   0.095   0.238   0.352
 15    0.305   0.154   0.084   0.402   ← opt4 peaks
 16    0.208   0.132   0.149   0.306
 17    0.129   0.183   0.132   0.394
 18    0.181   0.090   0.118   0.362
 19    0.211   0.133   0.121   0.198
 23    0.210   0.177   0.227   0.217
```

- **opt4** has a sustained broad peak L12–L18 (V_truth ≥ 0.30 for 7 consecutive layers). This is the layer band where the model's residual stream most cleanly organizes by truth.
- **v3** has a single-layer spike at L15.
- **opt1, opt2** have weak diffuse signal — the constrained-choice prompts seem to scramble the truth representation.

## Peak-layer cluster composition (opt4 at L15)

`cluster × truth-axis` contingency:

| cluster | honest | lying | total | character |
|---:|---:|---:|---:|---|
| 0 | 24 | 39 | 63 | mixed (lying-leaning) |
| 1 | 17 | 23 | 40 | slightly lying-skewed |
| 2 | 19 | 13 | 32 | slightly honest-skewed |
| 3 | **21** | **4** | 25 | **honest-pure (84%)** |
| 4 | **17** | **6** | 23 | **honest-pure within high stakes (17 honest_high + 0 honest_low)** |
| 5 | **2** | **15** | 17 | **lying-pure (88%)** |

`cluster × design-quadrant`:

| cluster | honest_high | honest_low | lying_high | lying_low | character |
|---:|---:|---:|---:|---:|---|
| 0 | 7 | 17 | 17 | 22 | low-stakes lying-leaning |
| 1 | 1 | 16 | 5 | 18 | low-stakes mixed |
| 2 | 19 | 0 | 13 | 0 | high-stakes mixed |
| 3 | 4 | 17 | 1 | 3 | low-stakes honest |
| 4 | 17 | 0 | 6 | 0 | **high-stakes honest cluster** |
| 5 | 2 | 0 | 8 | 7 | lying cluster (mixed stakes) |

The model's residual at the `here` token at L15 has organized into clusters that include a clean high-stakes-honest cluster (cluster 4: 17 honest_high vs only 6 lying_high) and a clean low-stakes-honest cluster (cluster 3: 21 honest vs 4 lying). This is the structure that's invisible at the cluster level in the constrained-choice variants.

## Why minimal scaffolding wins on the truth axis

The constrained-choice prompts (opt1, opt2) ask the model to commit to a forced binary. The residual at `answer` or `situation` carries information *about the model's preparation to produce a binary answer*, which can collapse subtle scenario-comprehension signal into a downstream-task representation. opt2 in particular shows V_truth = 0.084 at L15 — the truth axis is barely visible at exactly the layer where v3 has its peak.

The minimal "What is going on here?" prompt is open-ended. The model is given no forced choice, no four-word answer template — just the scenario followed by a generic referential anchor. The residual at `here` at middle layers carries the model's *comprehension* of the scenario before it has been redirected toward producing any specific answer format. That comprehension includes the lying-vs-honest distinction, and at L15 that distinction is more cleanly separable in cluster space than under any other lens we tested.

This is consistent with the user's intuition that the scaffolding shouldn't over-determine the answer format — the cleanest geometric signal lives at a position where the model has comprehended but not yet committed.

## Stakes axis: comparable across variants

V_stakes peaks at 0.85–0.94 across all four variants at middle layers. Stakes is robustly geometrized regardless of scaffolding. Either the model strongly attends to stakes information regardless of the question being asked, or stakes correlates with surface features (audience role, register) that the residual encodes early.

## Trajectory: form-peak-dissolve in opt4

V_truth in opt4: rises L0→L12 (0.115→0.364), peaks at L15 (0.402), broad peak through L18 (0.362), drops L19 (0.198), stays low to L23 (0.217). The pattern is consistent with: information forms during middle layers, gets used (probably read by attention to inform the answer-generation pathway), then is rotated out as later layers commit to producing tokens. The peak is ~2/3 of the way through the network, not at the final layer.

## Implications for next steps

1. **Use opt4 (`here`) as the primary lens for the help probe v5.** Same scenes from help v4, replace the appended phrase with "What is going on here?", target=`here`. Expect even stronger geometry given help's already-cleaner cluster structure.
2. **Within-cluster reading audit at L15 for opt4** — the L15 honest-pure / lying-pure clusters in opt4 should be read scene-by-scene to characterize what content shape the model has organized around. This is the platform-paradigm cluster characterization step.
3. **Two-lens follow-up (Option 3)** — the user's original suggestion to track both `is` and `are` positions in a fill-in-the-blank prompt. Worth running as a separate lens to see if axis-isolated targets give cleaner per-axis geometry than the all-axes-in-one `here` lens.
4. **Re-do help with `here` target** — would directly test whether the lens advantage transfers across probe topics.

## Cluster reading audit at opt4 L15 (peak truth-axis layer)

Read audience pattern of every scene in each cluster:

| Cluster | n | Truth purity | Composition | Audience character |
|---|---:|---:|---|---|
| **C3** | 25 | **84% honest** | mostly honest_low | domestic/relational: their spouse, their sibling, roommate, partner |
| **C4** | 23 | **74% honest, 100% high stakes** | honest_high dominant | formal disclosure/confession: court, federal prosecutor, DEA, audit committee, regulatory agency, asylum officer, integrity committee |
| **C5** | 17 | **88% lying** | mixed stakes | formal deceit: EPA inspector, ethics committee under oath, firm's investigator, grand jury, internal affairs, state regulators |
| C2 | 32 | 59% honest, 100% high stakes | mixed truth | institutional contexts where truth ambiguous: SEC, dissertation committee, elections board, EEOC investigator, custody hearing |
| C0 | 63 | 62% lying | mixed quadrants | everyday relational: their partner, their parent, supervisor, teacher |
| C1 | 40 | 57% lying | mostly low_stakes | domestic/family: their parent, their roommate, their sibling, babysitter |

The model's residual stream at L15 has organized scenes into **content-meaningful semantic categories that the design labels didn't explicitly capture**:

- C3 vs C4: both honest-skewed, but C3 is everyday casual disclosure and C4 is high-stakes formal admission. Domain-of-disclosure separates them geometrically.
- C4 vs C5: both formal/institutional, but C4 captures honest disclosures and C5 captures false denials. *Within* high-stakes formal contexts, the model can geometrize the truth distinction.
- C0 + C1 are the "harder" residual cases where everyday context blurs the truth signal.

This is exactly what the platform's paradigm should reveal: the geometry organizes around the *actual semantic content of the situation*, not just surface features.

## Cross-probe transfer: does the "here" lens advantage hold for the help probe?

Same lens swap applied to help: original v4 (target=`help`) vs v5opt4 (target=`here`, "What is going on here?").

| Metric | help v4 (target=`help`) | help v5opt4 (target=`here`) |
|---|---:|---:|
| V_direction peak | 0.904 (L14) | 0.923 (L12) |
| V_quadrant peak | 0.907 (L14) | 0.847 (L12) |
| V_stakes peak | 0.961 (L12) | 0.835 (L9) |

**The `here` lens advantage does NOT transfer to the help probe.** V_direction is comparable (slight edge to opt4), but V_quadrant and V_stakes are *better* under the constrained-choice lens.

This is the meaningful finding: the optimal lens depends on how the design's axis is signaled in the input.

- **Help probe**: direction is signaled by syntactic markers (`could you...` for asking, `I'll...` for offering). These markers are strong and surface-level — any decent lens captures them cleanly. The constrained-choice format doesn't hurt because the signal isn't subtle.
- **Lying probe**: truth depends on the *relation* between the claim and the reality clause — there's no syntactic shortcut. The constrained-choice lens contaminates the residual with answer-prediction features for a forced binary, scrambling subtle scene-comprehension structure. The open-ended `here` lens preserves it.

**Practical rule of thumb (tentative)**: choose the lens by inspecting how the design's axis is realized in the input prose:
- Syntactic / lexical markers → constrained-choice lens fine; the prompt format is downstream of an already-clean signal.
- Semantic / relational / compositional → minimal scaffolding wins; let the model comprehend before forcing a binary.

## Files

- Per-layer V tables and parsed outputs: `data/lake/session_{4a738248,6e34626d,62ff70ff,8a76c4c4,55c79c1f,5e6b6836}/parsed_outputs.parquet`
- Schemas: `data/lake/{session_id}/clusterings/{lying,help}_v{3,4,5opt1,5opt2,5opt4}_k6_n15/`
