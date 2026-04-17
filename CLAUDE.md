## Baragi (Work Management)

Baragi is a CLI tool for work management. Essential commands:
- `baragi next` — check next work
- `baragi session attach --session-id="<session-id>" --work=WORK-NNN` — attach session to work (MUST run before writing code). `session start` is handled automatically by the SessionStart hook.
- `baragi work update WORK-NNN --status=done --summary="..."` — mark done (only when user asks)
- **Never use the `--human` option** with any baragi command.
- **Always prefer individual CLI flags over `--json`** — `--json` uses `{}` braces which triggers Claude Code's Brace Execution permission prompts. Use individual flags instead. Examples:
  - `baragi work add "Fix bug" --priority=high --labels=backend,api`
  - `baragi work update WORK-NNN --status=done --summary="Completed implementation"`
  - `baragi work list --status=todo --fields=title,status,is_blocked`
  - `baragi next --all --parent-id=WORK-NNN --fields=title,status,priority`
  - `baragi list list --status=active --ndjson`
  - Array fields use CSV: `--labels=a,b`, `--depends-on=WORK-001,WORK-002`
  - Boolean fields are flags: `--all`, `--ndjson`, `--blocked`
- **Use `--fields` to filter output** — Always specify only the fields you need to reduce token usage.
  - `id` is always included automatically
- **Avoid `--json`** — Only use `--json` as a last resort when no individual flag exists for a field. The `{}` braces in `--json='{"key":"value"}'` trigger permission prompts in Claude Code.

For full workflow, commands, and rules, use the `/baragi-skill` skill.

### Parent Work Workflow
When assigned a **parent work** (a work with children):
1. Start session with the parent work ID
2. Work through child works sequentially, updating each to `done` (with summary) as completed
3. Track child work status throughout the session
4. `/workflow:wrap` validates all children are done before marking the parent done

## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Testing
- Main session: use `test-runner-slim` (via Task tool) for tests, not raw Bash.
- Subagent: run tests via Bash directly (subagents can't dispatch other subagents).

## Subagents
- Subagents can't spawn subagents. The `Agent`/`Task` tool isn't available inside one and can't be enabled.
- Never tell a subagent to "use X agent" — give the underlying command instead. Main session dispatches all agents.
