# Workflow Plugin

End-to-end feature pipeline for Claude Code: **PRD → Plan → Execute**, with TDD enforcement and per-task model escalation.

## Pipeline at a glance

```
/workflow:create-prd       Draft a product requirements document
       │
       ▼
/workflow:create-plan      Translate the PRD into a tagged implementation plan
       │
       ▼
/workflow:execute-plan     Execute all plan tasks → validate → polish
       │
       └─► /workflow:execute-task   (called per task)
                │
                ├─ implement (TDD, 2 commits)
                └─ validate (per-task: tests + plan compliance)

Final stage in /execute-plan:
       ├─ stage-end test+validate (cross-task regressions)
       └─ /workflow:polish (1× or 2× per change-size heuristic)
```

## Quick start

1. **Draft a PRD:** `/workflow:create-prd Add bookmarks feature`
   Saves to `docs/feature/YYYY-MM-DD-bookmarks-prd.md`.

2. **Create the plan:** `/workflow:create-plan docs/feature/YYYY-MM-DD-bookmarks-prd.md`
   Saves to `docs/feature/YYYY-MM-DD-bookmarks-plan.md`. Plan §5 lists tasks tagged `[model: haiku|sonnet|opus]`.

3. **Execute:** `/workflow:execute-plan docs/feature/YYYY-MM-DD-bookmarks-plan.md`
   Runs each task in dependency order, validates, polishes at the end, prints a summary.

To re-run a single task: `/workflow:execute-task` with pipe-delimited arguments.

## Skills

### `/workflow:create-prd`

Draft a Product Requirements Document directly in the main session.

- Clarification dialog (one question at a time via `AskUserQuestion`)
- Drafts the PRD inline using `references/prd-template.md` (8-section lean structure)
- **Single optional critic pass** via `devils-advocate` — no auto re-iteration
- All Required Fixes presented in **one batched** `AskUserQuestion` (multi-select)
- File: `docs/feature/YYYY-MM-DD-<feature>-prd.md`

### `/workflow:create-plan`

Translate a PRD into an implementation plan.

- Locates the PRD (or accepts a path), reads it + CLAUDE.md + relevant codebase
- Drafts the plan inline using `references/plan-template.md` (6 sections: Approach, File-by-file, Types, Test Plan, Tasks, Risks)
- Each task in §5 is tagged `[model: haiku|sonnet|opus]` based on complexity heuristic
- Optional single critic pass via `devils-advocate`
- File: `docs/feature/YYYY-MM-DD-<feature>-plan.md`

### `/workflow:execute-task`

Execute a single task from a plan. Called by `/execute-plan` per task; also user-invocable to re-run one task.

- Two-step flow: **implement → validate**
- Implementer subagent (TDD, mandatory 2 commits: `test:` then `feat:`)
- Validator subagent (sonnet, runs tests + verifies deliverables match plan)
- **Model escalation on validation failure** — see [Model escalation](#model-escalation)
- Max 3 retries, ceiling at opus

### `/workflow:execute-plan`

Orchestrate a full plan execution.

- Parses plan §5 task list, validates dependency DAG
- Reads plan + PRD **once at orchestrator level**, inlines sections into subagent prompts (no per-subagent re-reads)
- Runs tasks sequentially in dependency order via `/execute-task`
- Stage-end test+validate (whole-plan scope — catches cross-task regressions)
- Polish at end: 1× or 2× per heuristic (LOC > 300 OR files > 8 OR tasks > 4 → 2×)
- Summary report

### `/workflow:polish`

Simplify + code-review gated loop on changed files.

- Runs `/simplify` first
- Then `code-reviewer` agent
- If Blocker/Major findings → dispatches a fixer subagent → re-reviews
- Independent retry budget of 2

Called by `/execute-plan` at stage-end. User-invocable for ad-hoc polish.

### `/workflow:wrap`

Session finalization: polish loop, commit, push, mark work done.

## Agent

### `devils-advocate`

The single critic agent. Sonnet model. Used by both `/create-prd` and `/create-plan`.

Scope covers **product** (assumptions, scope, edge cases, UX, analytics, release strategy) **and** **technical** (data model, API design, state management, performance, security, migration, codebase fit, test strategy).

Outputs a structured critique with severity tags (Blocker / Major / Minor / Nit) and a `Required Fixes` list. Does not assign numeric scores.

## Design decisions

### Model escalation

Each task in plan §5 is tagged with a starting model tier. On validation failure, `/execute-task` escalates one tier and retries.

| Initial tag | Retry 1 | Retry 2 | Retry 3 |
|---|---|---|---|
| haiku | sonnet | opus | opus |
| sonnet | opus | opus | opus |
| opus | opus | opus | opus |

The validator stays on sonnet for every attempt — judging is cheaper than doing.

**Tag heuristic** (used by `/create-plan` when authoring):

| Tier | Use when |
|---|---|
| haiku | 1 file, <50 LOC, mechanical (rename, format, simple wire-up) |
| sonnet (default) | 1–3 files, follows existing patterns, well-specified |
| opus | Multi-file design work, debugging, novel pattern, ambiguous scope |

### No auto-iterating critic loops

Both `/create-prd` and `/create-plan` run the critic **once**. Required Fixes go to the user as one batched `AskUserQuestion`; the user picks Accept / Defer / Disagree per issue. No automatic re-critique after revisions — if you want another pass, ask explicitly.

This is the biggest cost reduction over the previous SPEC-based pipeline, where review loops drifted (4+ cycles without converging) instead of converging.

### Polish runs once at stage-end

Polish does NOT run per-task. It runs once at the end of `/execute-plan`, with the option to run twice for big changes (LOC > 300 OR files > 8 OR tasks > 4). This avoids the previous pipeline's per-task polish multiplier.

### Inlined plan + PRD content

`/execute-plan` and `/execute-task` read the plan and PRD **once at orchestrator level** and inline the relevant sections (§1 Approach, §3 Types, §4 Test Plan entries for this task, PRD §4 FRs) directly into subagent prompts. Subagents do not re-read these files. File paths are kept only as a fallback for deep-reads.

This reduces token spend substantially (subagents share the same prompt prefix → cache hits) and prevents subagents from skimming past sections they should have read.

### TDD two-commit rhythm

Implementer subagents produce two commits per task:
1. `test:` — failing tests for the acceptance criteria
2. `feat:` — minimum implementation to pass

Ordering is verified by `/execute-task` Step 3. The two commits are never squashed — the order is what makes TDD verifiable after the fact.

### File naming convention

Flat directory under `docs/feature/`:

```
docs/feature/
  2026-04-28-bookmarks-prd.md
  2026-04-29-bookmarks-plan.md
```

Date prefix is the authoring date. PRD ↔ plan pairs share the `<feature-name>` between the date and the suffix.

## File layout

```
local-plugins/workflow/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── devils-advocate.md
├── skills/
│   ├── create-prd/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── prd-template.md
│   │       └── prd-drafting-guide.md
│   ├── create-plan/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── plan-template.md
│   ├── execute-task/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── implementer-prompt.md
│   ├── execute-plan/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── test-and-validate-prompt.md
│   ├── polish/
│   │   └── SKILL.md
│   └── wrap/
│       └── SKILL.md
└── README.md (this file)
```

## When to use what

| Situation | Skill |
|---|---|
| Brand new feature idea, need to formalize it | `/workflow:create-prd` |
| PRD exists, need the implementation plan | `/workflow:create-plan` |
| Plan exists, ready to build | `/workflow:execute-plan` |
| Re-run one specific task from a plan | `/workflow:execute-task` |
| Ad-hoc cleanup of recent changes | `/workflow:polish` |
| End of session, finalize and push | `/workflow:wrap` |

## Subagent dispatches per typical 5-task plan

| Path | Dispatches |
|---|---|
| Happy path | ~11 (5×2 per-task + 1 stage validate + 1–2 polish runs) |
| One task fails once | ~13 |

For comparison, the previous SPEC-based pipeline averaged ~30+ dispatches for the same workload.
