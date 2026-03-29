# Claude Code Best Practices — Research & Project Audit

*Date: 2026-03-28*

This document audits Concept MRI's Claude Code scaffolding against current best practices (official docs, community resources, and real-world patterns), reviews settings, and researches three additional topics chosen for their potential impact on the project.

---

## Part 1: Claude Code Best Practices Audit

### What We're Doing Right

**1. CLAUDE.md length (130 lines) — GOOD**
Official docs recommend <200 lines. Beyond 200, instruction adherence drops measurably. We're safely under. The "150-200 instruction limit" cited in community research refers to total discrete instructions before compliance degrades — our file has ~40 distinct rules, well within range.

**2. Skills architecture — EXCELLENT**
Our 6 skills (`/server`, `/probe`, `/categorize`, `/analyze`, `/temporal`, `/pipeline`) follow the official pattern exactly: self-contained SKILL.md files with copy-paste-ready commands. Skills load on-demand (not every session), preserving context. This is the recommended approach for domain-specific workflows.

**3. Plan mode for complex tasks — GOOD**
CLAUDE.md Rule 12 (Certainty Protocol) enforces explore-then-plan-then-implement. This matches the official "four-phase workflow": Explore → Plan → Implement → Commit.

**4. Memory system — GOOD**
We use the auto-memory system with typed memories (user, feedback, project, reference). The MEMORY.md index pattern matches what Claude Code expects.

**5. Docs as reference, skills as authority — GOOD**
CLAUDE.md explicitly says "When they conflict, skills win." This is the correct hierarchy.

### What We Could Improve

**1. No `.claude/settings.json` (project-level) — MISSING**
We only have `settings.local.json`. A committed `settings.json` would share permission rules with new clones. Currently, every new session starts with zero permissions and must approve each tool use manually.

**Recommendation:** Create `.claude/settings.json` with commonly-needed permissions (curl, ls, git operations, npm/pip commands). Keep `settings.local.json` for machine-specific overrides.

**2. No hooks — MISSING (HIGH IMPACT)**
Hooks enforce rules at 100% vs CLAUDE.md's ~70-80%. Our most critical rules that Claude sometimes violates are perfect hook candidates:
- **Block bare `python3`**: PreToolUse hook on Bash to reject commands using `python3` without the `.venv/bin/` prefix
- **Block `pkill` for server management**: PreToolUse hook on Bash to reject `pkill -f uvicorn/vite` and suggest `fuser -k`
- **Enforce `generate_output: false` for temporal**: PreToolUse hook on Bash to check temporal-capture curl commands
- **Notification on completion**: Notification hook for WSL2 (powershell.exe toast)
- **Post-compaction context re-injection**: SessionStart hook with `compact` matcher to remind about WSL2 rules, .venv path, and critical project facts

**3. No `.claude/rules/` directory — OPTIONAL**
The rules directory allows path-scoped instructions (e.g., backend-specific rules load only when touching Python files). Our CLAUDE.md is small enough that this isn't urgent, but as the project grows, splitting into `rules/backend.md`, `rules/frontend.md`, `rules/analysis.md` could help.

**4. No custom subagents — USE WHEN IT MAKES SENSE**
Subagents should be used when they genuinely help — primarily for context isolation on heavy-read operations. The analyze-worker gets the full dataset in its own context window and returns the report. This is the right pattern: the subagent sees everything it needs, the main conversation stays clean. See Topic 2 for details.

**5. No compact instructions in CLAUDE.md — MISSING**
When context compacts, critical details (session IDs, schema names, WSL2 rules) can be lost. Adding a compact instruction section ensures the most important context survives:
```
## Compact Instructions
When compacting, always preserve: active session IDs, schema names, the WSL2 environment rules (fuser not pkill, .venv paths), and any in-progress pipeline stage.
```

**6. Accumulated stale permissions in `settings.local.json`**
The current file has 37 permission rules, many highly specific to past sessions (individual PIDs, specific grep patterns, specific Python one-liners). These clutter the file. Should be pruned to general patterns.

---

## Part 2: Settings Review

### `~/.claude/settings.json` (user-level) — GOOD
```json
{
  "model": "claude-opus-4-6",
  "alwaysThinkingEnabled": true,
  "effortLevel": "high"
}
```
This is correct and appropriate for research work. Opus 4.6 is the most capable model, thinking mode enables extended reasoning, high effort prevents shortcuts.

### `.claude/settings.local.json` — NEEDS CLEANUP

**Issues found:**
1. **Stale PID-specific permissions** (lines 27-28): `kill 240345 240949 240950` and `kill 240006 239986` are useless — PIDs change every session
2. **Overly specific Python one-liners** (lines 12-14, 34-35): Permission rules for exact `python -c "import ..."` commands. These were one-time checks and won't match again
3. **Overly specific grep commands** (lines 18-21): Permission for exact grep patterns on specific files
4. **`pkill` permissions** (lines 24-26, 33): `pkill -f uvicorn`, `pkill -f vite`, `pkill -f "node.*dev"` — we've moved to `fuser -k`, so pkill should be in deny, not allow
5. **Missing general permissions**: No `fuser` permission, no `git commit`, no `git diff`, no `git log`
6. **`Bash(python:*)` on line 8**: Allows bare `python`, contradicting our "always use .venv" rule

**Recommended `.claude/settings.json` (project-level, committed):**
```json
{
  "permissions": {
    "allow": [
      "Bash(ls:*)",
      "Bash(curl:*)",
      "Bash(fuser:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(npm install:*)",
      "Bash(npm run dev:*)",
      "Bash(npx tsc:*)",
      "Bash(npx vite:*)",
      "Bash(ps aux:*)",
      "Bash(wc:*)",
      "Bash(.venv/bin/python:*)",
      "Bash(.venv/bin/pip:*)",
      "WebSearch"
    ],
    "deny": [
      "Bash(pkill:*)"
    ]
  }
}
```

**Design decisions:**
- `pkill` in deny — we always use `fuser -k` on WSL2. Deny is absolute and version-independent.
- Bare `python3`/`pip` NOT in deny — deny rules override allow rules, so denying `python3` would block `python3 -m venv .venv` during first-time setup. Instead, bare python/pip are simply not in the allow list, so Claude gets prompted. The user can approve one-off uses (like venv creation) while rejecting lazy bare-python habits. Hooks (Topic 1) provide the active enforcement with a helpful error message.
- No `Bash(cat:*)` — Claude should use the Read tool instead.
- No `Bash(cd:*)` — Claude should use absolute paths; cd is discouraged by the system prompt.

**Recommended `.claude/settings.local.json` (cleaned up, machine-specific):**
```json
{
  "permissions": {
    "allow": [
      "WebFetch(domain:www.builder.io)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:code.claude.com)"
    ],
    "deny": []
  }
}
```

All the stale PID-specific, one-time python check, and overly specific grep permissions are removed. General patterns (curl, git, .venv/bin/python) are in the project-level settings.json where they benefit all clones.

---

## Part 3: Three Additional Research Topics

### Topic 1: Hooks for WSL2 Safety Enforcement

**Why this matters:** Our most common Claude mistakes are WSL2-specific: using `pkill` instead of `fuser`, bare `python3` instead of `.venv/bin/python`, forgetting `generate_output: false` for temporal captures. CLAUDE.md rules work ~70-80% of the time; hooks enforce at 100%.

**Recommended hooks (for `.claude/settings.json`):**

> **Note:** The `if` field requires Claude Code v2.1.85+. If on an older version, omit `if` and use a script that reads the command from stdin JSON and checks it. Or rely on the deny rule for pkill (already in settings.json) and the "not in allow list" prompt for bare python3.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(pkill *)",
            "command": "echo 'Use fuser -k <port>/tcp instead of pkill on WSL2' >&2 && exit 2"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(python3 *)",
            "command": "INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -q '^python3 -m venv'; then exit 0; fi; echo 'Use .venv/bin/python, not bare python3. Exception: python3 -m venv is allowed for setup.' >&2; exit 2"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'REMINDER: WSL2 environment. Use fuser -k (not pkill). Use .venv/bin/python (not python3). Temporal captures always need generate_output: false. Skills are authoritative over docs.'"
          }
        ]
      }
    ]
  }
}
```

**Hook events relevant to our project:**
- `PreToolUse` (Bash matcher) — block dangerous commands
- `PostToolUse` (Edit|Write matcher) — could run linting
- `SessionStart` (compact matcher) — re-inject critical context after compaction
- `Notification` — desktop notification when Claude finishes (useful during long captures)
- `Stop` — could verify analysis reports have element descriptions before Claude considers the task done

### Topic 2: Custom Subagents — Where They'd Actually Help

**Context:** The `/analyze` skill scaffolding already ensures completeness (all clusters labeled, element descriptions generated, etc.), so a "reviewer" subagent would be solving a non-problem. Subagents are most valuable for **context isolation** — keeping heavy reads out of the main window.

**Where subagents would genuinely help:**

**1. Heavy analysis reads as isolated context**
The `/analyze` skill reads hundreds of sentences and large JSON responses. Running the actual analysis in a subagent would keep all that data out of the main context window. Not a separate "reviewer" — just the analysis itself delegated to a subagent:

```yaml
---
name: analyze-worker
description: Runs Concept MRI cluster/route analysis in isolated context. Use when /analyze is invoked.
tools: Read, Grep, Glob, Bash, Write
model: inherit
skills:
  - analyze
---

You run the /analyze workflow in an isolated context window. Load data, read sentences, write reports and element descriptions. Return only the final report summary to the main conversation.
```

**2. Codebase exploration for unfamiliar areas**
The built-in `Explore` subagent already handles this. No custom agent needed.

**3. Probe-validator: LOW PRIORITY**
The `/probe` skill is interactive — the human reviews sentences during co-design. A validator adds little value when the human is already in the loop.

**Verdict:** Only `analyze-worker` has real value — and only because analysis reads are the heaviest context consumers in our pipeline. Everything else is already handled by the scaffolding or built-in agents.

### Topic 3: Context Compaction Strategy for Long Pipeline Sessions

**Why this matters:** A full pipeline run (probe -> capture -> categorize -> schema -> analyze -> temporal) can easily fill the context window. Auto-compaction loses critical state: session IDs, schema names, current pipeline stage.

**Recommended strategy:**

**1. Add Compact Instructions to CLAUDE.md:**
```markdown
## Compact Instructions
When compacting, always preserve:
- Active session IDs and schema names
- Current pipeline stage (which stages are complete)
- WSL2 environment rules (fuser, .venv paths, 0.0.0.0 binding)
- Any probe guide analysis focus areas
- Element description keys format (cluster-{id}-L{layer}, route-{sig})
```

**2. Use SessionStart hook for post-compaction re-injection:**
Already covered in Topic 1. The `compact` matcher fires after every compaction event, re-injecting critical rules.

**3. Pipeline stage tracking:**
Instead of relying on context memory, the `/pipeline` skill already checks state via API calls. After compaction, Claude can re-derive the current stage by running the pipeline checks. This is already well-designed.

**4. Subagent delegation for heavy-read stages:**
Stage 5 (Analysis) reads hundreds of sentences and large JSON responses. Delegating to an analyze-worker subagent keeps that data in an isolated context while the subagent has the full dataset it needs. The main conversation gets only the report summary back.

---

## Implementation Priority

| Action | Impact | Effort | Priority |
|--------|--------|--------|----------|
| Clean up settings.local.json | Medium | Low | Do first |
| Create project-level settings.json with deny rules | High | Low | Do first |
| Add Compact Instructions to CLAUDE.md | Medium | Low | Do first |
| Add PreToolUse hooks (pkill, bare python3) | High | Medium | Do second |
| Add SessionStart compact hook | Medium | Medium | Do second |
| Create analyze-worker subagent (context isolation) | Medium | Medium | Do third |
| Add Notification hook | Low | Low | Nice-to-have |
| Split CLAUDE.md into .claude/rules/ | Low | Medium | Not yet needed |

---

## Sources

- [Best Practices for Claude Code — Official Docs](https://code.claude.com/docs/en/best-practices)
- [Automate workflows with hooks — Official Docs](https://code.claude.com/docs/en/hooks-guide)
- [Create custom subagents — Official Docs](https://code.claude.com/docs/en/sub-agents)
- [How Claude remembers your project — Official Docs](https://code.claude.com/docs/en/memory)
- [CLAUDE.md Best Practices — Arize](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
- [claude-code-best-practice — GitHub (20k+ stars)](https://github.com/shanraisshan/claude-code-best-practice)
- [50 Claude Code Tips — Builder.io](https://www.builder.io/blog/claude-code-tips-best-practices)
- [32 Claude Code Tips — Agentic Coding Substack](https://agenticcoding.substack.com/p/32-claude-code-tips-from-basics-to)
- [Claude Code Rules: Stop Stuffing Everything into One CLAUDE.md](https://medium.com/@richardhightower/claude-code-rules-stop-stuffing-everything-into-one-claude-md-0b3732bca433)
- [CCPM: Claude Code Project Manager](https://github.com/automazeio/ccpm)
- [awesome-claude-code — GitHub](https://github.com/hesreallyhim/awesome-claude-code)
- [awesome-claude-code-subagents — GitHub](https://github.com/VoltAgent/awesome-claude-code-subagents)
