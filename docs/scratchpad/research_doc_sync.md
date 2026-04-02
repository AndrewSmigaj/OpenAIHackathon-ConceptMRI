# Research: Document Cross-References & Sync Mechanisms

Created: 2026-03-30
Agent: Document Sync Patterns Research

---

## What We Planned

Deliverable 3: `Related:` headers on each doc + a behavioral rule in CLAUDE.md telling Claude to check cross-references after editing docs.

---

## What Works Elsewhere

**The Related: header pattern has precedent** in multiple forms:
- **Sphinx** uses `:ref:`, `:doc:`, and `toctree` with *validated* cross-references (warns on broken links)
- **YAML frontmatter** in static site generators (Hugo, Jekyll, MyST) uses structured `related:` / `depends_on:` fields
- **"See also" sections** (Wikipedia/MDN pattern) serve reader navigation, not writer sync reminders

Our plan's freeform `Related:` line at the top is directionally correct. Placing it at the top (vs. bottom "See also") correctly orients it toward the *writer*, not the reader. The gap: ours has no automated validation, which is fine at ~20 docs.

---

## The Big Finding: Behavioral Rule Alone Will Fail

**Root cause of doc drift in our project:** Context window attrition. By message 30 of a long conversation, CLAUDE.md rules have been pushed out of active context. Claude forgets related docs exist. Research confirms this -- MemU found "context drift causes 65% of enterprise AI agent failures." The documentation quality literature is also clear: "rules alone fail; automated enforcement at the moment of writing is essential."

**The behavioral rule does not survive long conversations.** This is the exact scenario that caused the original drift with `architecturemud.md`.

---

## Key Recommendation: Add a PostToolUse Hook

Claude Code's hook system supports a **PostToolUse hook that injects `additionalContext`** back into Claude's context after every tool use. Concrete design:

The hook would:
1. Match on `Write|Edit` only (not Bash, Read, etc.)
2. Check if the edited file path contains `docs/`, `LLMud/`, or `CLAUDE.md`
3. If yes, read the first 5 lines looking for a `Related:` header
4. Inject the Related: line as `additionalContext` (e.g., "DOC SYNC REMINDER: Related: VISION.md, CLAUDE.md, PIPELINE.md")
5. For non-doc files, exit silently

This is **not noisy** (only fires for doc edits) and **not fragile** (it's `head -5 | grep`). The plan's concern about hooks being "noisy and fragile" was valid for a naive hook but doesn't apply to a path-filtered one.

**Use BOTH the behavioral rule AND the hook.** The behavioral rule sets intent (Claude understands *why*). The hook provides the reminder at the exact moment of edit, surviving context window attrition. Together they cover each other's weaknesses.

---

## On the Scratchpad Pattern

- **Keep `docs/scratchpad/`** -- don't move to `.claude/scratchpad/`. The `.claude/` directory is for config, not content. Files in `.claude/` can get auto-loaded, which would be bad for working notes.
- **Claude Code's built-in `SCRATCHPAD_DIR`** is ephemeral (session-scoped). Ours is persistent (cross-conversation). Different purposes, no conflict.
- **No YAML frontmatter needed yet.** Add structured metadata only when there's tooling to consume it. Lightweight text headers are sufficient.

---

## Alternatives Evaluated

| Alternative | Verdict | Certainty |
|------------|---------|-----------|
| **MANIFEST.md** (central relationship map) | Don't do. Creates meta-drift. Distributed headers are better. | High against |
| **/doc-sync-check skill** (validation on demand) | Good complement, build later. Catches inter-conversation drift. | Medium for |
| **Inline "see also" links** | Complementary. Helps readers, not writers. Use alongside headers. | High |
| **Git hooks** | Wrong timing. Fires at commit, too late. Need reminders during editing. | High against |

---

## One Addition to the Behavioral Rule

The rule should explicitly state: **"Updating related docs after a doc edit is always in scope -- you do not need separate permission."** This addresses the tertiary cause of drift (Claude avoids "scope creep" by not touching files it wasn't asked about).

---

## Impact on the Plan

Deliverable 3 should gain a **Component C: PostToolUse hook** (~10 lines of JSON in `.claude/settings.json`). The plan's "Why not a hook?" rationale should be revised to acknowledge that a path-filtered hook avoids the noise/fragility concerns.

**Certainty: HIGH** that Related: headers are correct. **HIGH** that behavioral rule alone is insufficient. **HIGH** that adding a PostToolUse hook solves the root cause.
