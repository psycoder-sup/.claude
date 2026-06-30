---
name: orchestrate
description: >
  Run a milestone as an orchestrator: plan -> partition into file-disjoint waves -> delegate to N
  parallel code-implementer subagents -> integrate, verify, review -> (PR on request). The main
  session orchestrates and NEVER writes implementation code itself. Every wave and run is logged for
  later analysis. Use for non-trivial multi-file features run inside a dedicated worktree.
trigger: /orchestrate
user-invocable: true
argument-hint: "<milestone description or path to a plan file>"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent", "AskUserQuestion", "TaskCreate", "TaskUpdate"]
---

# /orchestrate

Run a milestone end-to-end as an **orchestrator**: you plan and partition the work, delegate the
actual coding to parallel `code-implementer` subagents, integrate and verify their output, get it
reviewed, and (only on request) open a PR. **You never write the implementation yourself.** Every run
is logged so the harness can be analyzed and improved over time.

This is the N-child evolution of the single-child `/tian implement` pattern, built on pure
Claude-Code primitives (worktree + native subagents + skills) — no tian CLI.

## The roles (keep them separate)

- **Orchestrator (you, this session)** — plan, partition, delegate, run commands (build/test/git),
  integrate, decide. You hold the whole milestone in context.
- **`code-implementer` subagent** — implements ONE scoped task inside a fixed file boundary,
  self-verifies, returns a structured report. Spawned N-at-a-time, in parallel.
- **`verifier` subagent (optional)** — independently reproduces build/tests and checks acceptance
  criteria. Read-only.
- **`/code-review`, `/security-review`** — fresh-eyes review of the integrated diff.

## Anti-freelance rule (the one rule that makes this work)

**You do not write or edit implementation code. Ever.** Not for the first task, not for a "just
one-line" fix found during verification, not for review findings. All code changes go through a
`code-implementer`. Your Write/Edit access is only for orchestration artifacts (a plan file,
`status.json`) — never source files. If you catch yourself about to Edit a source file, stop and
delegate it instead. Editing source yourself races the implementers and destroys the parallelism
guarantees.

## Preconditions

Run this **inside a dedicated milestone worktree**, so the whole milestone is isolated from `main`:

**Branch policy — the branch you're on decides everything.** Run `git branch --show-current` at the
start of step 1, then:

- **On `main`/`master`** (you're NOT in a dedicated worktree) → create the milestone branch:
  `git checkout -b feat/<slug>`. **This is the only case where you create a branch.**
- **On any other branch** (the normal `claude --worktree` case) → **never create a branch.** That
  branch already IS your milestone branch.
  - Auto-generated placeholder (e.g. `worktree-polymorphic-seeking-riddle`)? Rename it **in place**
    with `git branch -m feat/<slug>` (e.g. `git branch -m feat/inbox-create-modal-properties`). `-m`
    renames the current branch *without* creating a new one or moving HEAD, so worktree isolation is
    fully preserved while the milestone gets a readable name.
  - Already a meaningful name? Leave it as-is.

`-m` = rename = safe. `checkout -b` while on a non-main branch = a stray branch + a moved HEAD = the
footgun that switches the branch out from under the milestone. Never do it.

## Workflow

### 1. Plan + partition
- **Worth orchestrating? (gate — decide before anything else.)** Estimate the parallel width up
  front: how many *independent* tasks could actually run at once. If the honest answer is ~1
  (sequential work) or just 1–2 small tasks, **don't orchestrate** — the planning + per-agent briefs +
  integration overhead dominates, the orchestrator's own tokens become ~80–90% of the cost, and
  there's no parallelism to bank for it. Say so to the user and either do it in a normal session or
  dispatch a single `code-implementer` without the full wave machinery. Reserve `/orchestrate` for
  genuinely multi-file work with real parallel width (≥2 independent tasks sharing a wave).
- **Branch:** run `git branch --show-current`. On `main`/`master` → `git checkout -b feat/<slug>`.
  On any other branch → never create one: rename an auto-generated placeholder in place with
  `git branch -m feat/<slug>`, or stay if it's already meaningful (see Branch policy above).
- Decompose the milestone into independent **tasks**. If a plan file was passed as the argument,
  start from it; otherwise build the plan with the user (use plan mode for anything non-trivial).
- Build a **file-ownership map**: for each task, the set of files it will create/modify.
- Group tasks into **waves**: tasks with **disjoint** file sets share a wave (they run in parallel);
  tasks that depend on another's output go in a later wave.
- Mint a **run id** now and reuse it for every `orchlog.py` call this milestone:
  ```bash
  run_id="<branch>-$(date +%Y%m%d-%H%M%S)"
  ```
- (Optional) `TaskCreate` one task per work-item to track wave progress.

### 2. Partition rules — deciding N
N is **discovered, not forced** — only split work that is genuinely independent.
- Disjoint file sets → parallel (same wave).
- Two tasks share a file → **conflict**. Resolve by (a) one agent owns that file + both pieces, or
  (b) serialize them into different waves, or (c) make that single shared edit as its own tiny
  delegated task between waves (delegate it — don't edit it yourself).
- **Hotspot files** are conflict magnets — never let two agents touch them in parallel: router/route
  tables, DI containers, barrel `index.ts`, schema/migrations, lockfiles, shared types.
- Sequential dependency (task B needs task A's API) → N=1 for that stretch; don't fake parallelism.
- Default isolation is **same tree** (all agents in this worktree, partitioned by file → trivial
  integration). Give an agent `isolation: worktree` only when its change is large/risky enough to
  want its own checkout. Note: a shared-file conflict is NOT solved by isolation (it just moves to
  merge time) — solve those by serializing / single-owner.

### 3. Dispatch a wave
Spawn the wave's implementers **in a single message, one `Agent` call each**, so they run in
parallel (`subagent_type: "code-implementer"`). Each gets a self-contained brief — implementers
share no memory, so front-load everything:

```
## Task
<the one unit of work>
## Acceptance criteria   (checkable — this is the contract)
- [ ] ...
## File ownership   (modify ONLY these; if you need anything outside, STOP and report it)
- src/foo/**, tests/foo/**
## Context & conventions
<pointers to existing code, the pattern to follow, examples>
## Verification
<the exact build / test / lint commands to run for this scope>
## Output
Return the IMPLEMENTER REPORT block exactly as your agent definition specifies.
```

Under-specified briefs are the #1 cause of bad delegated code. If you can't write crisp acceptance
criteria and a clean file boundary, the task isn't ready — refine the partition first.

### 4. Integrate + verify + log
- Collect each implementer's IMPLEMENTER REPORT. Read `verdict`, `build`, `tests`, `blockers`.
- A `blockers` entry naming a cross-boundary need means your partition was off — handle it (reassign
  ownership, add a serial step), don't ignore it.
- Run the **full** build + test suite yourself (running commands is orchestration, not coding).
- (Optional) spawn a `verifier` subagent against the acceptance criteria for a second opinion.
- Anything red, or any `needs-attention`/`fail` verdict → **re-delegate a fix** to a fresh
  `code-implementer` (never patch inline). Loop back to step 3 until the wave is green.
- **Log one `agent` record per implementer** (map the report → flags):
  ```bash
  python3 ~/.claude/skills/orchestrate/orchlog.py record --type agent --run-id "$run_id" \
    --wave 1 --task "add foo endpoint" --files-owned 3 --files-changed 3 \
    --verdict pass --build pass --tests pass --isolation tree
  # flags to add when true: --deviated (deviations!=none)  --blockers (blockers!=none)
  #                         --boundary-stop (STOPped on a cross-boundary need)
  #                         --rework      (re-delegated after the agent's own work failed self-verify)
  #                         --review-fix  (delegated a /code-review or /security-review finding)
  # rework vs review-fix matters: rework is a quality signal (briefs/partition); review-fix is healthy.
  ```

### 5. Review
Both `/code-review` and `/security-review` spawn their OWN subagents internally, and subagents can't
spawn subagents — so **you (the orchestrator) must run each one yourself, directly in this session;
never delegate a review to a `code-implementer`** (it would fail or silently degrade). Invoking them
is an orchestrator action, like running build/test.

**You judge which of the two this milestone needs, and run each you deem necessary:**
- **`/code-review medium`** — warranted for essentially any milestone with real code changes; run it
  unless the diff is trivial/non-code (docs-only, pure config). **Always pass `medium`** — the no-arg
  default is `xhigh`, which burns far more tokens than a routine review needs; only go higher
  (high/max/ultra) when the user explicitly asks.
- **`/security-review`** — warranted when the diff touches a security-relevant surface: auth/authz,
  crypto, secrets, user-input handling, file/path/network I/O, deserialization, or SQL. Skip it when
  there's no plausible security impact (docs, pure refactors, test-only).

- Route every finding back to a `code-implementer` as a fix task (anti-freelance still applies); log
  each such fix agent with `--review-fix` — it's healthy follow-up, not `--rework`.
- Re-verify after fixes.

### 6. Finish + run log
- **Only if the user explicitly asks**, publish: `gh pr create ...` (and/or commit). Otherwise leave
  the worktree in place and report what was done and verified — publishing is the user's call.
- If the repo uses `project-kit`, update `docs/pm/status.json` (move the milestone to Next/Shipped).
- **Log the run summary** (once per milestone). Token capture is **automatic** — it scans this
  session's subagent + orchestrator transcripts and embeds usage **by agent type** (session
  auto-detected from cwd; pass `--no-auto-tokens` to skip):
  ```bash
  python3 ~/.claude/skills/orchestrate/orchlog.py record --type run --run-id "$run_id" \
    --branch "<branch>" --milestone "<desc>" --waves 2 --agents 5 --fix-iterations 1 \
    --outcome success --build-final pass --tests-final pass --review-findings 2
  # add --pr-created if you opened a PR.
  # Token capture is automatic in a dedicated worktree session (the norm). If you reuse one session
  # across milestones, also pass --since "<milestone-start ISO>" to scope the scan.
  ```

## Management principles
- **Self-contained briefs** — every agent gets all the context it needs; no shared memory.
- **Acceptance criteria are the contract** — verify against them, not against vibes.
- **Verification gate** — nothing is "done" until build + tests are green and criteria are met.
- **Bounded autonomy** — agents have a hard file boundary and a STOP-and-report rule; that is what
  lets them run in parallel safely and keeps humans out of the loop until a real decision is needed.
- **Fixes are always re-delegated** — never inline-patch; the fix gets the same boundary + gate.

## Analyzing the harness (closing the loop)
Periodically review accumulated runs to improve this workflow and the agent definitions:

```bash
python3 ~/.claude/skills/orchestrate/orchlog.py report --recent 20
```

**Quality signals**: high **boundary_stop** rate → partitioning too coarse or boundaries wrong; high
**rework** (re-delegations after a failed self-verify) → briefs under-specified or tasks too big; high
**deviated** → acceptance criteria not tight enough; the **verdict** mix and **fix-iters** show
overall health and parallel utilization. **review_fix** is tracked separately and is *healthy*
(review findings routed to fixes) — it never counts against brief quality.

**Cost signals** (the COST block, captured automatically): **output by type** shows where tokens go —
if `orchestrator` dominates, the orchestration overhead itself is the cost (a sign to delegate more
coarsely, plan more cheaply, or skip orchestration for small jobs — see "Worth orchestrating?" in
step 1); **~rework output** is tokens burned on rework, tying the `rework` quality signal directly to
a dollar-shaped number. For an ad-hoc look at the current session without logging a run:
```bash
python3 ~/.claude/skills/orchestrate/orchlog.py tokens          # output/total by agent type
```

When you change this skill or the agent definitions in response to these signals, bump
`WORKFLOW_VERSION` in `orchlog.py` so before/after runs stay comparable.
