## Baragi (Work Management)

Baragi is a CLI tool for work management. Essential commands:
- `baragi next` — check next work
- `baragi session attach --session-id="<session-id>" --work=WORK-NNN` — attach session to work (MUST run before writing code). `session start` is handled automatically by the SessionStart hook.
- `baragi work update WORK-NNN --status=done --summary="..."` — mark done (only when user asks)
- **Never use the `--human` option** with any baragi command.

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
