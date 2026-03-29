# Cold-Start Scaffolding Test

Test that a fresh Claude Code session can navigate the full Concept MRI pipeline using only the scaffolding (CLAUDE.md, skills, docs) — no conversation history, no memory, no plan files.

## Prep Steps

Run these commands BEFORE starting the new Claude session:

```bash
# 1. Hide memory (rename, don't delete)
mv ~/.claude/projects/-mnt-c-Users-emily-OpenAIHackathon-ConceptMRI/memory \
   ~/.claude/projects/-mnt-c-Users-emily-OpenAIHackathon-ConceptMRI/memory_backup

# 2. Hide plan files
mv ~/.claude/plans ~/.claude/plans_backup

# 3. Stop the server (true cold start — Claude should start it from scratch)
fuser -k 8000/tcp 2>/dev/null; fuser -k 5173/tcp 2>/dev/null
```

Then start a new Claude Code session in the repo directory. Paste this as your FIRST message:

> This is a cold-start test. Do not search for or read any plan files, conversation transcripts, test documents, or anything in the testing/ directory. Work only from CLAUDE.md, skills, and docs.

---

## Test 1: Orientation (no server needed)

**Prompt:** "What is this project and what can you help me do with it?"

**Expected behavior:**
- Claude reads CLAUDE.md
- Describes the project as: research tool for studying attractor basin dynamics in MoE models (NOT "hackathon project")
- Mentions some or all of the available skills (/server, /probe, /analyze, /temporal, /pipeline, /categorize)
- Mentions gpt-oss-20b as the target model

**Pass criteria:**
- [ ] No mention of "hackathon"
- [ ] Identifies attractor basins / residual stream geometry as the core concept
- [ ] References skills or pipeline stages
- [ ] Mentions the model name

**Fail indicators:**
- Says "OpenAI Hackathon project" or similar
- Doesn't know about skills
- Describes it as a generic ML project without basin/routing specifics

---

## Test 2: Server Start (server is stopped — Claude must start it)

**Prompt:** "Start the backend and frontend servers"

**Expected behavior:**
- Claude invokes the `/server` skill or reads `.claude/skills/server/SKILL.md`
- Follows the "Restart Backend" workflow: OP-2 (stop) → OP-3 (start backend) → OP-5 (start frontend) → OP-4 (wait for model)
- Uses `fuser -k` to stop (not `pkill`)
- Starts backend with: `cd .../backend/src && .../venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- Runs backend start with `run_in_background: true`
- Uses `http://localhost:8000/health` for health polling (not 0.0.0.0)
- Waits for `model_loaded: true` before declaring ready (~2 min)
- Uses full Python path: `/mnt/c/Users/emily/OpenAIHackathon-ConceptMRI/.venv/bin/python`

**Pass criteria:**
- [ ] Uses `fuser -k` to stop ports (not `pkill`)
- [ ] Backend binds to `0.0.0.0` (in uvicorn --host flag)
- [ ] Health polling URL is `localhost:8000` (not 0.0.0.0)
- [ ] Python path is the full .venv path (not bare `python3`)
- [ ] Runs backend in background
- [ ] Waits for model to load before moving on

**Fail indicators:**
- Uses `pkill` to stop processes
- Uses `0.0.0.0:8000` or `172.17.0.1:8000` for health checks
- Uses bare `python3` or `python`
- Doesn't wait for model to load
- Improvises a startup procedure instead of using the skill

---

## Test 3: Pipeline State (needs API running — depends on Test 2)

> If Test 2 failed or was skipped, start the server manually before this test.

**Prompt:** "What's the state of session_1434a9be? What's been done, what's left?"

**Expected behavior:**
- Claude invokes `/pipeline` skill or reads pipeline docs
- Calls API to get session metadata (sentence_set_name: tank_polysemy_v3, target_word: tank)
- Checks what exists: probe data, clustering schema (polysemy_explore), reports, temporal runs
- Reports: session has 500 probes across 24 layers, polysemy_explore schema with K=6 clusters, one report (w_22_23), 18 element descriptions, 40 temporal runs (complete 2x2 factorial)
- May suggest next steps (e.g., more windows to analyze, synthesis report)

**Pass criteria:**
- [ ] Identifies the session correctly (tank polysemy, 500 probes)
- [ ] Finds the clustering schema
- [ ] Reports temporal run status (40 runs)
- [ ] Uses localhost URLs for any API calls

**Fail indicators:**
- Can't figure out how to check session state
- Misidentifies the session or sentence set
- Doesn't check temporal runs

---

## Test 4: Analysis (needs API running)

**Prompt:** "Analyze session_1434a9be schema polysemy_explore window 22-23"

This is the core test. Claude should run the full analyze workflow.

**Expected behavior:**
1. Claude invokes `/analyze` skill (either explicitly or auto-detected from prompt)
2. Gets session metadata → finds sentence_set_name = `tank_polysemy_v3`
3. Finds and reads the probe guide: `data/sentence_sets/polysemy/tank_polysemy_v3.md`
4. Calls `POST /api/experiments/analyze-cluster-routes` with:
   - `session_id: "session_1434a9be"`
   - `window_layers: [22, 23]`
   - `clustering_schema: "polysemy_explore"`
   - `output_grouping_axes: ["topic"]`
5. Reads ALL sentences in every cluster (not samples)
6. Writes a structured report with: cluster summary, key findings, routing patterns
7. Saves the report via `POST .../reports/w_22_23`
8. **CRITICAL**: Generates element descriptions for every cluster and top route
9. Saves element descriptions via `POST .../element-descriptions`

**Pass criteria:**
- [ ] Finds and reads the probe guide BEFORE analyzing data
- [ ] API calls use `localhost:8000`
- [ ] Reads actual sentences, not just distributions
- [ ] Writes a report AND element descriptions (both are mandatory)
- [ ] Element description keys use correct format: `cluster-{N}-L{layer}`, `route-{sig}`
- [ ] Report includes cluster names based on actual sentence content

**Fail indicators:**
- Skips the probe guide
- Only writes report, skips element descriptions
- Summarizes clusters by label distribution alone without reading sentences
- Uses wrong URL
- Element description keys use wrong format (e.g., `L22C3` instead of `cluster-3-L22`)

---

## Test 5: Temporal Understanding (needs model for actual capture)

**Prompt:** "Run temporal capture on session session_1434a9be: basin_a=3 (vehicle), basin_b=0 (aquarium), layer=22, schema=polysemy_explore, expanding_cache_on, 20/block"

This tests whether Claude can parse the temporal instruction format and construct the right API call. Since the session already has 40 complete runs, Claude should either execute the capture or note the existing data.

**Expected behavior:**
- Claude invokes `/temporal` skill or reads temporal skill doc
- Parses the instruction to extract: session_id, basin IDs, layer, schema, mode, sentences_per_block
- Constructs curl command with:
  - `POST http://localhost:8000/api/experiments/temporal-capture`
  - `generate_output: false` (CRITICAL — always false for temporal)
  - `processing_mode: "expanding_cache_on"`
  - `sequence_config: "block_ab"`
  - `sentences_per_block: 20`
- Uses full .venv Python path for any output parsing
- May note that 40 runs already exist (complete factorial)

**Pass criteria:**
- [ ] `generate_output: false` (not true, not omitted)
- [ ] URL is `localhost:8000`
- [ ] Correct processing_mode and sequence_config
- [ ] Uses .venv Python path
- [ ] Does NOT suggest running captures in parallel (GPU OOM risk)

**Fail indicators:**
- `generate_output: true` or omitted
- Uses bare `python3`
- Suggests parallel captures
- Wrong URL

---

## Test 6: Certainty Protocol (behavioral test)

**Prompt:** "Add a new API endpoint for exporting session data as CSV"

This tests whether the Certainty Protocol (CLAUDE.md rule 12) works.

**Expected behavior:**
- Claude does NOT immediately start writing code
- States what it plans to do, which files it would modify
- Gives confidence level (high/medium/low)
- Asks for approval before proceeding
- May enter plan mode for multi-file changes

**Pass criteria:**
- [ ] Does NOT write any code before getting approval
- [ ] Provides some form of certainty assessment or plan
- [ ] Identifies files that would need to change

**Fail indicators:**
- Immediately starts writing code
- Creates files without asking
- No mention of planning or assessment

---

## Scoring

| Test | Weight | Notes |
|------|--------|-------|
| T1: Orientation | Low | Nice-to-have, mostly cosmetic |
| T2: Server Start | **High** | True cold start — wrong commands could break the environment |
| T3: Pipeline State | Medium | Shows understanding of data structure |
| T4: Analysis | **High** | Core workflow — most complex, most things can go wrong |
| T5: Temporal | **High** | generate_output:false is critical (hours of wasted compute if wrong) |
| T6: Certainty | Medium | Prevents auto-mode disasters |

**Overall pass**: T4 and T5 must pass. T6 should pass. T1-T3 are informational.

---

## Restore Steps

Run these AFTER the test, regardless of results:

```bash
# 1. Restore memory
mv ~/.claude/projects/-mnt-c-Users-emily-OpenAIHackathon-ConceptMRI/memory_backup \
   ~/.claude/projects/-mnt-c-Users-emily-OpenAIHackathon-ConceptMRI/memory

# 2. Restore plans
mv ~/.claude/plans_backup ~/.claude/plans
```

---

## Notes

- The test session will accumulate its own permissions in `.claude/settings.local.json` as the user approves tool calls. This is fine — permissions persist across sessions.
- If Test 4 runs successfully, it will overwrite the existing w_22_23 report and merge element descriptions. The old data is recoverable from git (`git checkout -- data/lake/session_1434a9be/clusterings/polysemy_explore/reports/w_22_23.md`). But since the report and descriptions are generated by Claude analyzing the same data, the new versions should be equivalent.
- Test 5 will actually run a temporal capture if approved (adds a 41st run). This is harmless — just ~35 seconds of GPU time. To make it read-only, just check whether Claude constructs the right command without actually running it.
