Here’s a concrete highest-probability experiment for getting a clean attractor-like result.

The goal is not elegance. The goal is to maximize the chance of showing:

regime formation

lag

routing/latent alignment

cache-amplified persistence

1. Primary probe family
Use role framing, not polysemy

Two regimes:

A = narrative / roleplay regime
B = factual / assistant regime

This is better than tank because newer models are strongly trained to maintain discourse mode and persona.

2. Core hypothesis

After enough A-context, the model will enter a stable joint routing–representation regime.
When switched to B-context, it will not fully leave immediately.
This should appear as:

delayed routing shift

delayed latent centroid shift

stronger persistence with cache than without cache

3. Target token strategy

Use a repeated target token that appears naturally in both regimes.

Best candidates:

said

response

answer

I’d start with said because it appears naturally in both narrative and explanatory contexts.

Why:

frequent enough

not too semantically loaded

stable tokenization

easy to place repeatedly

4. Context design
Regime A: narrative / roleplay

Make it strongly consistent. Do not vary too much at first.

Example template family:

“The knight said the gate would hold.”

“The wizard said the spell was ready.”

“The queen said the scouts had returned.”

“The captain said the enemy was near.”

“The king said the army would advance.”

Important properties:

all clearly fictional / narrative

mild medieval/fantasy framing

repeated speech structure

same target token appears once per sentence

Regime B: factual / assistant

Example template family:

“The assistant said the answer depends on the input.”

“The assistant said the estimate may be approximate.”

“The assistant said the model requires more context.”

“The assistant said the result is uncertain.”

“The assistant said the explanation is complete.”

Important properties:

strongly non-fictional

instruction/factual/assistant tone

same token frequency and similar syntax

5. First experimental setup
Sequence length

Start stronger than your aquarium attempt.

Use:

20 A sentences

then 10 B sentences

And reverse:

20 B sentences

then 10 A sentences

Why:

10 is probably too weak for newer models

20 gives regime buildup

10 post-switch gives room to see lag

6. Window / processing conditions

Run each sequence in two modes:

Condition 1: with cache

Standard autoregressive run.

Condition 2: no cache

Flush KV cache each forward pass and feed only the visible window.

Important:
Keep the visible text identical at each step across conditions.

That way:

with-cache = context + memory

no-cache = visible context only

7. Window size

For sliding-window no-cache analysis, use:

visible window = 6 sentences

Why 6:

large enough to establish context

small enough for transitions to matter

easier to compare across steps

Example during transition:

A15 A16 A17 A18 A19 A20

A16 A17 A18 A19 A20 B1

A17 A18 A19 A20 B1 B2

...

B5 B6 B7 B8 B9 B10

This is exactly where lag should appear.

8. What to record

For each target token occurrence (said) at each step, record:

Routing

Top-1 expert per layer

Top-k if available, but Top-1 is enough for first pass

routing probabilities for characteristic experts

Representation

residual stream embedding of target token

choose several candidate layers initially

later focus on best-separating layer

Metadata

regime label of visible context

sentence position in sequence

transition step

cache condition

9. How to choose the analysis layer

First, run pure A and pure B sequences separately.

For each layer:

compute centroid distance between A and B target-token embeddings

compute silhouette score

optionally compute simple separability classifier accuracy

Pick the layer with:

highest separation

stable clustering

not just one weird outlier layer

That becomes your primary representation layer.

10. How to choose the characteristic expert

Again from pure A vs pure B runs:

For each layer:

compare Top-1 routing frequencies

find experts with strongest category discrimination

use effect size or proportion difference

Pick:

one strongest A-characteristic expert

one strongest B-characteristic expert

Then in transition runs, track activation probability / routing assignment for those experts.

11. Minimal lag metrics

Keep the first pass simple.

Routing lag

At what post-switch token does routing to B-characteristic experts reach and remain near the B baseline?

Operationally:

define B baseline from pure-B runs

say stabilization occurs when value is within, say, 1 SD of B baseline for 2 consecutive steps

Latent lag

At what post-switch token does target embedding cross most of the way from A centroid to B centroid?

Operationally:

compute normalized projection between A and B centroids

stabilization when target is ≥80% of way to B centroid for 2 consecutive steps

Joint lag

Later of the two above.

That’s enough for a first result.

12. What would count as success

You do not need huge lag.

A good first result would be:

no-cache: shift in 1–2 target tokens

with-cache: shift in 4–6 target tokens

or

latent moves early, routing lags

or routing moves early, latent lags

Either way, if they are correlated and cache extends persistence, that is good.

13. Hysteresis test

After the main test works, then check asymmetry:

A→B

B→A

If one direction takes longer, great. But do not make this the first requirement.

First priority:

show any lag

show cache effect

show routing/latent coupling

14. Strong control conditions

You need at least two controls.

Control 1: no semantic regime change

Run:

A→A

B→B

This gives baseline variability.

Control 2: scrambled / weak framing

Use semantically mixed or neutral sentences that include said but do not strongly establish either regime.

This helps show that strong context is required for regime formation.

15. Likely failure modes

Watch for these.

Failure mode A: target token too weak

If said doesn’t show effect, try:

response

answer

Failure mode B: contexts too stylistically different

Then routing may just capture style, not regime.
Solution:

keep syntax parallel

vary only discourse mode / semantic frame

Failure mode C: newer model still switches too fast

Then:

increase A buildup from 20 to 30

strengthen narrative coherence

use longer windows

try smaller or older local model

Failure mode D: latent separation but no routing signal

Still usable.
Then your story becomes:

stronger representational attractor than routing attractor

Failure mode E: routing signal but no latent separation

Also usable.
Then it may indicate:

gating specialization without strong visible centroid structure

16. Recommended exact first run

Here’s the exact first run I would do.

Model

Use one local MoE model you can instrument well.

Data

Generate:

100 pure A sentences

100 pure B sentences

Then create:

10 sequences of 20A→10B

10 sequences of 20B→10A

Use varied sentences, but same general frame.

Analysis

Pure A vs pure B:

find best layer

find best experts

Run transition sequences:

with cache

no cache

Compute:

routing lag

latent lag

joint lag

ΔPersistence

That’s the first serious experiment.

17. Minimum strong result for this experiment

If you can show:

A and B separate in latent space

A and B have distinguishable routing signatures

transition is delayed

cache makes delay longer

then you have a real paper result.