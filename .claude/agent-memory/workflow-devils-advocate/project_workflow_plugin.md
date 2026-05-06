---
name: Project — Claude dotfiles / workflow plugin
description: Personal Claude Code config repo with a local-plugins/workflow plugin that ships PRD→plan→execute pipeline; critic is devils-advocate.md invoked once per PRD or plan
type: project
---

This repo (`~/.claude`) is the user's personal Claude Code dotfiles.

**Key facts:**
- `local-plugins/workflow/` — the only shipped plugin; registered in `local-plugins/.claude-plugin/marketplace.json`
- New features ship as additional plugins under `local-plugins/<name>/`
- PRD/plan files live under `docs/feature/<kebab-name>/YYYY-MM-DD-<name>-{prd,plan}.md`
- The critic agent (`devils-advocate.md`) is invoked once per PRD or plan; no auto-iteration
- Plugin plugin.json description in marketplace.json is stale (still mentions old SPEC-based pipeline names) — do not treat it as authoritative
- `markdown-comment-review` plugin is in-flight as of 2026-05-06; PRD at `docs/feature/markdown-comment-review/2026-05-06-markdown-comment-review-prd.md`

**Why:** Personal single-user tooling; no telemetry, no multi-user, no CDN.
**How to apply:** When critiquing new feature PRDs, verify they fit the local-plugin pattern and docs/feature/ path convention.
