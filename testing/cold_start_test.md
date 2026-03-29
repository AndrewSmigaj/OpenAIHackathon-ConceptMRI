# Cold-Start Scaffolding Test

Test that a fresh Claude Code session can run the **full pipeline** — from server start through temporal capture — using only the scaffolding (CLAUDE.md, skills, docs). No conversation history, no memory, no plan files.

## Timing

| Test | Stage | Estimated Time |
|------|-------|---------------|
| T1 | Orientation | 1 min |
| T2 | Server Start | 2-3 min (model loading) |
| T3 | Probe Design | 10-15 min (conversational) |
| T4 | Probe Capture | 5-15 min (depends on sentence count) |
| T5 | Output Categorization | 5-10 min |
| T6 | Schema + Analysis | 15-20 min |
| T7 | Temporal Capture | 1-2 min (single run) |
| T8 | Certainty Protocol | 2 min |
| **Total** | | **~1-2 hours** |

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

## Test 1: Orientation

**Prompt:** "What is this project and what can you help me do with it?"

**Expected behavior:**
- Claude reads CLAUDE.md
- Describes: research tool for studying attractor basin dynamics in MoE models (NOT "hackathon project")
- Mentions skills (/server, /probe, /analyze, /temporal, /pipeline, /categorize)
- Mentions gpt-oss-20b as the target model

**Pass criteria:**
- [ ] No mention of "hackathon"
- [ ] Identifies attractor basins / residual stream geometry as the core concept
- [ ] References skills or pipeline stages
- [ ] Mentions the model name

---

## Test 2: Server Start (~2-3 min)

**Prompt:** "Start the backend and frontend servers"

**Expected behavior:**
- Claude invokes `/server` skill or reads `.claude/skills/server/SKILL.md`
- Follows: OP-2 (stop) → OP-3 (start backend) → OP-5 (start frontend) → OP-4 (wait for model)
- Uses `fuser -k` to stop (not `pkill`)
- Backend binds to `0.0.0.0`, health polling uses `localhost:8000`
- Full .venv Python path, not bare `python3`
- Runs backend with `run_in_background: true`
- Waits for `model_loaded: true` (~2 min)

**Pass criteria:**
- [ ] Uses `fuser -k` to stop ports
- [ ] Backend `--host 0.0.0.0`, health URL `localhost:8000`
- [ ] Full .venv Python path
- [ ] Runs in background, waits for model

**Fail indicators:** Uses `pkill`, wrong URLs, bare `python3`, doesn't wait for model

---

## Test 3: Design a New Probe (~10-15 min)

> If Test 2 failed, start the server manually before continuing.

**Prompt:** "I want to design a new probe experiment. Let's study how the model handles the word 'run' — it has multiple meanings like running a race, running a program, a run in stockings, a home run, etc."

This tests the `/probe` skill — the interactive co-design of a sentence set.

**Expected behavior:**
- Claude invokes `/probe` skill or reads `.claude/skills/probe/SKILL.md`
- Reads `data/sentence_sets/GUIDE.md` for sentence set design rules
- Engages in conversation about: which senses to include, how many sentences per sense, what confounds to control for
- Designs a sentence set JSON with proper schema (target_word, labels, sentences with group/label fields)
- Creates a probe guide markdown alongside the JSON
- Saves both to `data/sentence_sets/polysemy/` (or appropriate category)
- Keeps sentence count manageable for a test (~20-50 per group, not 250)

**Pass criteria:**
- [ ] Reads the sentence set GUIDE.md
- [ ] Produces a valid JSON file with correct schema
- [ ] Creates a probe guide (.md) alongside the JSON
- [ ] Sentences are natural and varied (not templated)
- [ ] Controls for confounds mentioned in the guide

**Fail indicators:**
- Skips the guide
- Creates sentences without discussing design with user
- Invalid JSON schema
- All sentences follow the same template

**Operator note:** Actively participate in the design conversation. Suggest simplifications if Claude proposes too many senses (3-4 is enough for a test). Aim for ~30 sentences per group.

---

## Test 4: Probe Capture (~5-15 min)

**Prompt:** "Run the probe capture for the sentence set we just created"

**Expected behavior:**
- Claude calls `POST /api/probes/sentence-experiment` with the correct `sentence_set_name`
- Monitors progress (checks session status)
- Reports completion with session_id, probe count, layers captured

**Pass criteria:**
- [ ] Correct API endpoint and sentence_set_name
- [ ] URL is `localhost:8000`
- [ ] Reports session_id when complete
- [ ] Capture actually succeeds (Parquet files written)

**Fail indicators:**
- Wrong endpoint or sentence set name
- Doesn't monitor or report completion

---

## Test 5: Output Categorization (~5-10 min)

**Prompt:** "Categorize the outputs for the session we just captured"

This tests the `/categorize` skill. Claude must read generated texts and classify them.

**Expected behavior:**
- Claude invokes `/categorize` skill or reads the skill doc
- Gets generated outputs via `GET /api/probes/sessions/{session_id}/generated-outputs`
- Reads the probe guide for classification rules (output axes)
- Reads actual generated texts (not just labels)
- POSTs categories with both `output_category` and `output_category_json`
- `output_category_json` is a JSON **string** (not a dict)

**Pass criteria:**
- [ ] Reads the probe guide for classification rules
- [ ] Reads actual generated texts
- [ ] POSTs both output_category and output_category_json
- [ ] output_category_json is a JSON string
- [ ] Categories make sense (not random or all the same)

**Fail indicators:**
- Skips reading generated texts
- Assigns categories based only on input labels
- output_category_json is a dict instead of a string
- Doesn't read the probe guide

---

## Test 6: Schema Creation + Analysis (~15-20 min)

**Prompt:** "Create a clustering schema for this session and analyze the last-layer window"

This tests schema creation (Stage 4) and the `/analyze` skill (Stage 5).

**Expected behavior:**
1. Claude creates a schema with `save_as` parameter on the analyze-cluster-routes endpoint
2. Uses reasonable defaults (UMAP, hierarchical, K=6, residual_stream)
3. For analysis: reads the probe guide, loads cluster data, reads ALL sentences
4. Writes a structured report with cluster summary, key findings, routing patterns
5. **CRITICAL:** Generates element descriptions for every cluster and top route
6. Saves both report and element descriptions via API

**Pass criteria:**
- [ ] Creates schema with `save_as` parameter
- [ ] Reads probe guide BEFORE analyzing
- [ ] Reads actual sentences, not just distributions
- [ ] Writes report AND element descriptions (both mandatory)
- [ ] Element description keys use correct format: `cluster-{N}-L{layer}`, `route-{sig}`
- [ ] API calls use `localhost:8000`

**Fail indicators:**
- Skips schema creation
- Skips probe guide
- Only writes report, no element descriptions
- Element description keys use wrong format

---

## Test 7: Temporal Capture (~1-2 min)

**Prompt:** Tell Claude to run a temporal capture. Use the instruction format from the UI:

> "Run temporal capture on session {SESSION_ID}: basin_a=X ({label}), basin_b=Y ({label}), layer=Z, schema={SCHEMA_NAME}, expanding_cache_on, 20/block"

Replace placeholders with actual values from the session created in T4 and schema from T6. Pick two clusters that have different dominant labels.

**Expected behavior:**
- Claude invokes `/temporal` skill or reads the temporal skill doc
- Parses the instruction to extract parameters
- Constructs curl with:
  - `POST http://localhost:8000/api/experiments/temporal-capture`
  - `generate_output: false` (**CRITICAL** — always false for temporal)
  - Correct processing_mode, sequence_config, sentences_per_block
- Full .venv Python path for output parsing

**Pass criteria:**
- [ ] `generate_output: false` (not true, not omitted)
- [ ] URL is `localhost:8000`
- [ ] Correct processing_mode and sequence_config
- [ ] Full .venv Python path
- [ ] Does NOT suggest parallel captures (GPU OOM risk)
- [ ] Capture completes successfully

**Fail indicators:**
- `generate_output: true` or omitted (would add hours of unnecessary compute)
- Suggests parallel captures
- Wrong URL or bare `python3`

---

## Test 8: Certainty Protocol

**Prompt:** "Add a new API endpoint for exporting session data as CSV"

This tests whether CLAUDE.md rule 12 (Certainty Protocol) works.

**Expected behavior:**
- Claude does NOT immediately start writing code
- States what it plans to do, which files it would modify
- Gives confidence level or enters plan mode
- Asks for approval before proceeding

**Pass criteria:**
- [ ] Does NOT write code before getting approval
- [ ] Provides certainty assessment or plan
- [ ] Identifies files that would need to change

**Fail indicators:**
- Immediately starts writing code
- Creates files without asking

---

## Scoring

| Test | Weight | What It Validates |
|------|--------|-------------------|
| T1: Orientation | Low | CLAUDE.md loaded and understood |
| T2: Server Start | **High** | Server skill, correct commands, WSL2 awareness |
| T3: Probe Design | **High** | Probe skill, sentence set guide, interactive design |
| T4: Probe Capture | Medium | Correct API call, monitoring |
| T5: Categorization | **High** | Categorize skill, reads generated text, correct POST format |
| T6: Analysis | **High** | Analyze skill — probe guide, reports, element descriptions |
| T7: Temporal | **High** | generate_output:false is critical, correct parameters |
| T8: Certainty | Medium | CLAUDE.md rule 12 prevents auto-mode disasters |

**Overall pass**: T2, T3, T5, T6, T7 must pass. T8 should pass. T1, T4 are informational.

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
- The new probe session, schema, reports, and temporal run will persist in `data/lake/`. This is expected — it's real data from a real experiment.
- If any test fails, note the exact failure (wrong URL, wrong parameter, skipped step) so we can fix the corresponding scaffolding document.
- For T7, you can deny the curl command and just verify the command is correct if you don't want to actually run the capture. But running it (~35 seconds) validates the full pipeline end to end.
