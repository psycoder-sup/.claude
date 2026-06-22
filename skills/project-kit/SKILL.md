---
name: project-kit
description: >
  Bootstrap a project's agent-facing context system — a small set of living docs
  (live status + decision records) plus the operating rules that keep them current,
  wired into CLAUDE.md. Use when setting up context docs for a new or existing
  project, "set up project docs", "scaffold status/ADRs", or first-time project setup.
  Usage: /project-kit [--minimal | --full] [path]
trigger: /project-kit
user-invocable: true
argument-hint: "[--minimal | --full] [path]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion"]
---

# /project-kit

Bootstrap a project's **agent-facing context system** into any project, on the first
session. It creates a small set of *living* docs and wires the rules that keep them
current into `CLAUDE.md`, so future sessions orient fast and the docs stay true.

The system is four layers separated by how fast they change:

| Layer | File | Role |
|---|---|---|
| Primer (auto-loaded) | `CLAUDE.md` | Always-on orientation + the self-maintaining rule. Points at status, doesn't duplicate it. |
| Live state | `docs/pm/status.md` | Now / Next / Milestones / Blocked / Shipped. The "where are we" source of truth. |
| Decisions | `docs/pm/decisions/NNNN-*.md` | One ADR per direction change. Numbered, fixed once accepted. |
| Thesis & spec *(opt-in)* | `docs/pm/project-summary.md`, `prd.md` | The "why" and the buildable "what". Only with `--full`. |

**Lean by default**: status + ADRs + the `CLAUDE.md` rules. The thesis/spec layer is opt-in.

## Usage

```
/project-kit                 # infer from repo, interview only for gaps, scaffold lean
/project-kit --minimal       # blank templates, no inference, no questions
/project-kit --full          # also scaffold project-summary.md + prd.md
/project-kit <path>          # target a different project root (default: current dir)
/project-kit --help          # print this Usage block and stop
```

If invoked with `--help` / `-h` and no other arguments, print the `## Usage` block
verbatim and stop. Do nothing else.

## What you must do when invoked

The templates live next to this file under `templates/`. Read each one, substitute every
`{{TOKEN}}` (mapping below), and write the result to the target project. **You** (the
agent) do the substitution — the tokens are not a runtime feature.

### Step 0 — Parse arguments
- `--minimal` → skip Steps 2 & 3 entirely (no inference, no questions); write templates with
  light generic placeholders left in place for the user to fill.
- `--full` → in Step 4, also scaffold the optional thesis + spec docs.
- A bare non-flag argument → the **target project root**. Default: the current working directory.
- Resolve the skill's own directory (where `templates/` sits) so you can read the templates —
  e.g. `ls "$(dirname …)"`; if unsure, the templates are at `~/.claude/skills/project-kit/templates/`.

### Step 1 — Detect & protect (always)
Inspect the target root. Use Glob/Read — do **not** assume.
- Is there a `CLAUDE.md`? a `docs/pm/`? a `docs/pm/status.md`? a `docs/pm/decisions/`?
- Build a **create vs. skip** list. **Never overwrite an existing file.** If a target file already
  exists, leave it untouched and report it as *skipped* in Step 6.
- The one exception is the marked block in `CLAUDE.md` (Step 5), which is updated in place.

### Step 2 — Infer from the repo (skip if `--minimal`)
Draft the project's identity from what's already there, so the scaffold ships filled, not empty:
- **README** (`README*`), and any existing `CLAUDE.md` → project name, one-liner, purpose.
- **Manifests** — `package.json`, `pyproject.toml`/`setup.py`, `Cargo.toml`, `go.mod`, `*.xcodeproj`/`project.yml`, `pom.xml`, etc. → name, language/stack, scripts.
- **`git log --oneline -20`** and `git config user.name` → recent direction, current focus, owner.
- **Top-level layout** → what kind of project this is and where the work is.

From these, draft: `PROJECT_NAME`, `ONE_LINER`, a first-pass `NOW` / `NEXT`, any obvious
`MILESTONES`, and a sketch of the `CORE_BET`. Today's date: get it with `date +%F`.

### Step 3 — Interview for gaps only (skip if `--minimal`)
Use **AskUserQuestion** to fill *only* what inference could not resolve confidently. Do not
re-ask what the repo already answered. Typical gaps: the **core bet** (the non-obvious idea),
the **near-term focus** for *Now/Next*, and confirmation of the name/one-liner if ambiguous.
Keep it to 1–3 questions. If everything was inferable, skip this step.

### Step 4 — Fill & write the docs
Substitute tokens (table below) and write to the **target** root:
- `docs/pm/status.md`          ← `templates/status.md`
- `docs/pm/decisions/_template.md`            ← `templates/decisions/_template.md`
- `docs/pm/decisions/0001-initial-direction.md` ← `templates/decisions/0001-initial-direction.md`
- `docs/pm/decisions/README.md` — the decisions index, **generated** (see Step 4a)
- **`--full` only:** `docs/pm/project-summary.md` ← `templates/optional/project-summary.md`,
  and `docs/pm/prd.md` ← `templates/optional/prd.md`.

For any file already present (from Step 1), skip it — never clobber.

**Token map:**

| Token | Source |
|---|---|
| `{{PROJECT_NAME}}` | inferred / confirmed (Steps 2–3) |
| `{{ONE_LINER}}` | inferred / confirmed |
| `{{CORE_BET}}` | interview (Step 3); under `--minimal` leave the bracketed placeholder |
| `{{NOW}}` / `{{NEXT}}` | inferred / interview |
| `{{MILESTONES}}` | inferred; else leave the commented `e.g.` example for the user |
| `{{DATE}}` | `date +%F` |
| `{{OWNER}}` | `git config user.name` (fallback: leave `[name]`) |
| `{{OPTIONAL_LAYOUT_LINES}}` | empty for lean; under `--full`, two bullets for `project-summary.md` + `prd.md` (see Step 5) |

Under `--minimal`, leave the bracketed `[…]` placeholders intact so the user fills real content later.

### Step 4a — Generate the Decisions index (always)
Write `docs/pm/decisions/README.md` — a catalog of the ADRs. **Build it from the files, don't hand-author it:**
1. List every `docs/pm/decisions/NNNN-*.md`, sorted by number — **exclude** `_template.md` and `README.md` itself. (On an existing project this picks up *all* prior ADRs, not just `0001`.)
2. For each: take **number + title** from the file's first `# ` heading, and **status** from its `*Status: …*` line (Accepted / Proposed / Superseded). Link the number to the file.
3. Mark **supersession** by *reading*, not blind matching. When an ADR's body states it supersedes another (search `supersede`), the file you are reading is the **superseder** and the number it names is the **superseded** one — annotate *that* row, e.g. `0002` → `Accepted (part superseded by 0003)`. Do **not** infer supersession from a mere mention of another ADR number; only an explicit "supersedes" claim counts, and get the direction right.
4. Emit the rows into the `templates/decisions/README.md` layout (keep its marker comment + surrounding prose).

This file is a **generated artifact**, so unlike the other docs it is *regenerated*, not skipped, on re-run — but only when it is absent or carries the `<!-- project-kit:decisions-index -->` marker. If a `README.md` exists in that folder **without** the marker, treat it as the user's own file: leave it and report it skipped.

### Step 5 — Merge into `CLAUDE.md` (always)
The block to insert is `templates/CLAUDE.block.md` (with tokens substituted). It is delimited by
`<!-- project-kit:begin … -->` / `<!-- project-kit:end -->`.

- **`--full`:** set `{{OPTIONAL_LAYOUT_LINES}}` to:
  ```
  - `docs/pm/project-summary.md` — the thesis / "why". Read first for full context; changes slowly.
  - `docs/pm/prd.md` — the current version's buildable requirements.
  ```
  Otherwise set it to empty (the line vanishes).
- **No `CLAUDE.md` exists:** create it as `# {{PROJECT_NAME}}`, a blank line, `{{ONE_LINER}}`,
  a blank line, then the substituted block.
- **`CLAUDE.md` exists and already contains `<!-- project-kit:begin -->`:** this is a re-run —
  replace everything between the two markers (inclusive) with the freshly substituted block. Leave
  the rest of the file exactly as-is.
- **`CLAUDE.md` exists with no markers:** append the substituted block at the end of the file. **But**
  if the file already has a `## Status` heading, omit the block's own `## Status` section (keep only
  *Repo layout* + *Keeping the record current*) so you don't create a second Status section — and say
  so in the report.

Never edit any part of an existing `CLAUDE.md` outside the marked region.

### Step 6 — Report
Print a short tree of what was **created** vs. **skipped** (already existed), note how `CLAUDE.md`
was handled (created / block-updated / appended / Status-section-omitted), and end with the next
step: *"Fill the bracketed placeholders in `docs/pm/status.md` and `decisions/0001-…`, then commit."*

## Design rules (hold to these)
- **Idempotent / non-destructive.** Safe to re-run. Never overwrite a user's file. The two *generated*
  artifacts — the `CLAUDE.md` marked region and `decisions/README.md` (its index marker) — are refreshed
  in place; everything else is skip-if-exists.
- **Generalize, don't copy.** These templates carry the *patterns* (layer split, the self-maintaining
  rule, the ADR skeleton, the dated/falsifiable discipline) — never any one project's domain content.
- **Infer-first, interview-for-gaps.** Ship filled content; ask only what the repo can't tell you.
- **Lean by default.** Status + ADRs + CLAUDE rules; thesis/spec are opt-in via `--full`.
- **Keep entries specific and falsifiable** — the docs you scaffold should model the discipline: cite
  dates, link commits/ADRs, snapshot-not-journal.
