---
name: orchestrate-cleanup
description: >
  Ship a completed /orchestrate milestone: open a PR for the worktree branch, poll CI until
  conclusive (never cancel — self-hosted runners can be slow), auto-merge when every check is green
  and the PR is MERGEABLE/CLEAN, then clean up the worktree + branches, and (project-kit repos)
  move the milestone now->shipped in status.json via a direct push to main. Run AFTER a successful
  /orchestrate when the branch's work is committed and verified. It ships what's there — it never
  writes or fixes code; a red CI or required review ends the skill with a report, not a patch.
trigger: /orchestrate-cleanup
user-invocable: true
argument-hint: "[branch or PR-title override] — usually none; infers the current worktree branch"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion"]
---

# /orchestrate-cleanup

The tail end of an `/orchestrate` run, automated: **PR → poll CI → auto-merge on green → clean up →
(project-kit) status.json now→shipped**. You are the orchestrator finishing a milestone whose code
is already written, committed, and locally verified. **You do not write or fix implementation code
here.** If CI goes red or a review is required, you STOP and report — remediation is a fresh
`/orchestrate` or a manual pass.

## When to use
Right after a successful `/orchestrate`: the milestone branch lives in a dedicated worktree, its
build/tests are green locally, and you're ready to ship it to `main`. Not for unverified work.

## Preconditions
- Run from (or knowing) the **milestone worktree branch**. If `git branch --show-current` is
  `main`/`master`, STOP — there's nothing to ship.
- Work is committed and already green locally (that was `/orchestrate`'s job). If there are
  uncommitted changes, commit them with a real message first; if you can't tell they're finished,
  STOP and report rather than guessing.
- The **milestone lands via PR, never a direct push** (`main` is typically protected for code). The
  lone exception is the step-5 `status.json` bump — a trivial one-file doc edit pushed straight to `main`.

## Workflow

### 1. Rebase, push, open PR
- `branch=$(git branch --show-current)` — the milestone branch. Abort if it's the default branch.
- Commit anything pending (real message; end with the repo's commit footer convention if it has one).
- **Rebase onto the latest default branch first** — parallel sessions may have advanced it, and this
  is the #1 source of a PR opening as CONFLICTING:
  `git fetch origin main && git rebase origin/main`.
  Resolve conflicts — most often **shared-docs collisions**: two ADRs grabbing the same number, or a
  decisions `README.md` / `status.json` both edited. If your ADR number was taken, renumber to the
  next free one and fix every reference (file name, `"number"`, index row, code comments, status).
- Push: `git push -u origin "$branch"` (add `--force-with-lease` if you rebased).
- `gh pr create --base main --head "$branch" --title "…" --body-file …` — body = what shipped + how
  it was verified; end with the repo's PR footer convention. Capture the PR number.

### 2. Poll CI — never cancel
Poll until **every check is conclusive** (no PENDING/IN_PROGRESS/QUEUED) **and** the PR head ==
your pushed SHA. Use the bundled poller in the background so you're notified on completion:

```
python3 ~/.claude/skills/orchestrate-cleanup/pollci.py <PR#> <pushed-sha7>
```
(run it with `run_in_background: true`; it exits 0 when conclusive, 2 on timeout.)

- **Slow ≠ hung.** Self-hosted runners can sit `in_progress` for many minutes (slow `setup-node`,
  queueing). Do NOT cancel — cancelling + rerunning just re-hits the same slow step. Let it finish.
- Right after a push, GitHub briefly reports a **stale head / `mergeable=UNKNOWN`** — keep polling
  until `headRefOid` matches your SHA.
- A **paths-filtered** PR (e.g. docs-only) may register **zero checks** — the poller treats
  "head matches + no checks after a short grace" as conclusive.

### 3. Merge when green (automatic)
Merge **iff** every check is `SUCCESS`, `mergeable=MERGEABLE`, and `mergeStateStatus=CLEAN`:
`gh pr merge <PR#> --merge` (match the repo's merge style — this repo uses merge commits).

- **STOP and report, do NOT merge, when:**
  - any check `FAILURE` → link the run + name the failing step;
  - `DIRTY`/`CONFLICTING` → rebase onto `main`, resolve, push, and go back to step 2;
  - `BLOCKED` (required review/approval) → tell the user; it's their gate.
- **Gotcha:** don't pass `--delete-branch`. From inside a worktree it errors
  (`fatal: 'main' is already used by worktree …`). Delete branches in step 4.

### 4. Clean up worktree + branches
- Do this **from the main repo dir, never from inside the worktree you're removing** — that dir is
  your cwd, and removing it breaks the shell (you'll get "working directory was deleted").
- Sync: `git checkout main` (in the main dir) → `git fetch origin main` → `git merge --ff-only origin/main`.
- Remove the milestone worktree: `git worktree remove --force <path>` → `git worktree prune`.
- Delete the branch: `git push origin --delete "$branch"` (remote) + `git branch -D "$branch"` (local).
- **Only the milestone's worktree/branch.** `git worktree list` will show **other sessions'**
  worktrees — leave those completely alone.
- Clean any throwaway artifacts this milestone created (e.g. purge thrashed CI caches with
  `gh cache delete`, remove scratch containers), but nothing shared.

### 5. (project-kit) status.json now→shipped
If the repo uses project-kit (`docs/pm/status.json`), record the shipped milestone. It's a one-file
docs bump — do it **directly on `main`, no branch and no PR**:
- Confirm you're on a freshly-synced `main` (step 4 left you there).
- **Surgically** edit `status.json` (not a full reserialize — surgical edits merge cleanly alongside
  parallel sessions' concurrent status edits): remove the milestone from `now`; prepend a `shipped`
  entry (`date`, `commit`=merge SHA, `link`=PR URL, one-line summary + verification); trim `shipped`
  to the latest ~3; bump `lastUpdated`. Validate: `python3 -c "import json;json.load(open('docs/pm/status.json'))"`.
- Commit → `git push origin main`. If the push is rejected because `main` advanced meanwhile,
  `git pull --rebase origin main` and push again (the surgical edit rebases cleanly).

## Constraints & lessons (from real runs)
- **PR-only for the milestone** — `main` is protected; the code never direct-pushes. The step-5
  `status.json` bump is the one direct push.
- **Parallel sessions churn shared docs** (ADR numbers, decisions README, status.json). Rebase right
  before pushing; resolve number/index collisions; expect to re-rebase if `main` moves again before
  the merge lands.
- **Slow ≠ hung** on self-hosted runners — poll, don't cancel.
- **Clean up from the parent dir; never delete sibling worktrees.**
- **Report, don't fix** — a red gate or required review ends the skill with a clear status; fixing is
  a separate pass.
