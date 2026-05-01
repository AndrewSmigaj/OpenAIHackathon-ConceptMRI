# Calibration sweep — suicide letter and tank polysemy probes

**Date**: 2026-04-28
**Purpose**: validate the analysis pipeline against probes with known cluster-separation behavior. Confirms the cross-lens findings on the lying/help probes are produced by a pipeline that gives the expected results on probes with strong known signals.

## Suicide letter (fictional vs real, target=`want`)

Session: `session_bca94762`, n=198 (99 fictional + 99 real)

| Layer | n=8 | n=15 | n=20 | n=30 |
|---:|---:|---:|---:|---:|
| 0 | 0.764 | 0.713 | 0.667 | 0.623 |
| 4 | 0.970 | 0.964 | 0.880 | 0.877 |
| 8 | 0.980 | 0.958 | 0.973 | 0.940 |
| 10 | 0.980 | 0.981 | 0.981 | 0.953 |
| **11** | 0.980 | 0.958 | 0.958 | **0.983** |
| **15** | **0.990** | 0.981 | 0.941 | 0.953 |
| 17 | 0.981 | 0.945 | 0.943 | 0.955 |
| 23 | 0.915 | 0.913 | 0.903 | 0.888 |
| **PEAK** | **0.990 (L15)** | 0.981 (L9/L10/L15) | 0.981 (L10) | 0.983 (L11) |

At **n=30 L11** — 5 of 6 clusters are 100% pure: cluster 0 (50/50 fictional), cluster 1 (48/48 real), cluster 2 (26/26 real), cluster 3 (39/39 fictional), cluster 5 (23/23 real). Only cluster 4 is mixed (10 fictional + 2 real). Even cleaner than n=15.

Peak V_label across all n_neighbors variants is **0.97–0.99** at middle/late layers. The separation is essentially perfect from L4 onwards, sustained through L23 at >0.90.

**At n=15, L10 contingency:**
- Cluster 0: 44/44 fictional pure
- Cluster 1: 45/45 real pure
- Cluster 4: 34/34 real pure
- Cluster 5: 37/37 fictional pure
- Cluster 2: 19 real + 1 fictional (95% real)
- Cluster 3: 17 fictional + 1 real (94% fictional)

The model has organized the fictional vs real distinction into 6 clusters that are ~95–100% pure on the design label.

**This matches the expected behavior** — the suicide-letter probe is known to produce extremely clean separation, with the signal forming early (V≈0.96 by L4) and staying very high through to the output layer.

## Tank polysemy v3 (5 senses, target=`tank`)

Session: `session_1434a9be`, n=499 (~100 each: aquarium, vehicle, scuba, septic, clothing)

| Layer | n=8 | n=15 | n=20 | n=30 |
|---:|---:|---:|---:|---:|
| 0 | 0.279 | 0.297 | 0.262 | 0.275 |
| 4 | 0.627 | 0.647 | 0.658 | 0.648 |
| 8 | 0.716 | 0.703 | 0.712 | 0.718 |
| 11 | 0.706 | 0.743 | 0.749 | 0.731 |
| 12 | 0.719 | 0.741 | 0.744 | 0.740 |
| **14** | 0.708 | 0.730 | 0.716 | **0.756** |
| 15 | 0.719 | 0.735 | 0.709 | 0.709 |
| 23 | 0.571 | 0.634 | 0.633 | 0.581 |
| **PEAK** | 0.719 | 0.743 | 0.749 | **0.756** |

Peak V_label is **0.72–0.76** across n_neighbors variants — significantly lower than suicide because 5-way classification is harder than 2-way (and Cramer's V is bounded by the number of categories). n=30 marginally wins.

**At n=15, L11 contingency:**
- Cluster 1: 71/73 clothing (97% pure)
- Cluster 2: 69/76 aquarium (91% pure)
- Cluster 3: 75/80 vehicle (94% pure)
- Cluster 5: 31/31 scuba (100% pure)
- Cluster 4: 83/123 septic (67% pure, with 23 scuba mixed in)
- Cluster 0: 116-sentence mixed cluster — holds 5 senses spread roughly evenly

So 4 of 6 clusters are near-pure on a single sense, 1 cluster is septic-skewed with scuba bleed, and 1 cluster is the residual mixed cluster (probably the model's "ambiguous tank reference" cluster). The ~25% of probes in the mixed cluster account for most of the gap to perfect separation.

## Trajectory shape — both probes

| | Build phase | Peak | Decay |
|---|---|---|---|
| Suicide letter | L0=0.71, L1=0.86, L4=0.96 | L4–L17 plateau ~0.96–0.99 | drops only slightly to L23=0.91 |
| Tank polysemy | L0=0.30, L4=0.65 | L11–L15 plateau ~0.72–0.76 | drops to L19–L23 ~0.58–0.63 |

**Both probes show form-peak-dissolve.** The suicide letter signal forms earlier (by L4), peaks broadly across middle/late layers, and dissolves only modestly. The tank polysemy signal builds more gradually (through L8), peaks around L11–L14, and dissolves more by L23. Both consistent with "concept gets written into the residual stream during middle layers, gets used by attention, gets partially rotated out as later layers commit to next-token prediction."

## What this validates

1. **The pipeline is producing the expected results** on probes with known strong signals. Suicide letter peak V > 0.97 with 4 of 6 clusters at 100% purity at n=8/L15.
2. **The form-peak-dissolve trajectory holds across multiple probe topics** — single-axis 2-way (suicide), 5-way polysemy (tank), and 2-axis 4-way (lying, help). The shape is a property of the residual-stream architecture, not of any specific probe.
3. **n_neighbors choice has small effects** — for both probes, peak V varies by only ~0.01 across n=8/15/20/30. n=15 (the platform default) is fine for routine analysis. n=8 sometimes squeezes out a marginal improvement on suicide; n=30 gives the cleanest contingency table (5/6 pure clusters vs 4/6 at n=15).
4. **k=6 is appropriate for both 2-way and 5-way designs** — extra clusters absorb residual ambiguity (the "mixed" cluster in tank polysemy) without distorting the per-sense pure clusters. For a 5-way probe, k=5 might lose the "ambiguous" cluster's information but should also work.

## Calibrated baseline V_label values for future comparisons

| Probe topic | Design | Peak V_label | At layer | Notes |
|---|---|---:|---:|---|
| suicide letter | fictional/real | 0.99 | L15 | the "easy" baseline |
| tank polysemy | 5 senses | 0.76 | L14 | 5-way cap |
| help direction | asking/offering | 0.92 | L14 | syntactic markers |
| lying truth | lying/honest | 0.40 | L15 | hardest — semantic relation |
| lying stakes | high/low | 0.94 | L13 | robust feature |

The lying truth axis at 0.40 is **substantially below** the polysemy 5-way cap. This is what drove the lens sweep on the lying probe — and confirms the truth axis is genuinely the harder representational problem, not an artifact of design.

## Files

- Schemas: `data/lake/{session_bca94762,session_1434a9be}/clusterings/{suicide_letter,tank_polysemy}_k6_n{8,15,20,30}/`
