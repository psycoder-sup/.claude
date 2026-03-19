## Baragi (Work Management)

Baragi is a CLI tool for work management. Essential commands:
- `baragi next` — check next work
- `baragi session attach --session-id="<session-id>" --work=WORK-NNN` — attach session to work (MUST run before writing code). `session start` is handled automatically by the SessionStart hook.
- `baragi work update WORK-NNN --json='{"status":"done","summary":"..."}'` — mark done (only when user asks)
- **Never use the `--human` option** with any baragi command.
- **Always prefer `--json` over individual CLI flags** — `--json` is a global option available on ALL commands. Use `--json='{"key":"value"}'` instead of individual flags. CLI flags override JSON values when both are provided. Examples:
  - `baragi work add --json='{"title":"Fix bug","priority":"high","labels":["backend","api"]}'`
  - `baragi work update WORK-NNN --json='{"status":"done","summary":"Completed implementation"}'`
  - `baragi work list --json='{"status":"todo","all":false,"fields":["title","status","is_blocked"]}'`
  - `baragi next --json='{"all":true,"parent_id":"WORK-NNN","fields":["title","status","priority"]}'`
  - `baragi list list --json='{"status":"active","ndjson":true}'`
  - Array fields use JSON arrays (not CSV): `"labels":["a","b"]`, `"depends_on":["WORK-001"]`
  - Boolean fields use JSON booleans: `"all":true`, `"ndjson":true`, `"blocked":true`
  - Use `"fields":["title","status"]` inside JSON instead of `--fields=title,status`
- **Use `--fields` to filter output** (or `"fields"` inside `--json`) — Always specify only the fields you need to reduce token usage.
  - `id` is always included automatically

For full workflow, commands, and rules, use the `/baragi-skill` skill.

### Parent Work Workflow
When assigned a **parent work** (a work with children):
1. Start session with the parent work ID
2. Work through child works sequentially, updating each to `done` (with summary) as completed
3. Track child work status throughout the session
4. `/wrap` validates all children are done before marking the parent done

## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Testing
- Always use the `test-runner-slim` agent (via Task tool) for running tests. Do not run tests directly in Bash.
