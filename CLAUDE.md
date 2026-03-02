## Baragi (Work Management)

Baragi is a CLI tool for work management. Essential commands:
- `baragi next` — check next work
- `baragi session start --work=WORK-NNN --agent=claude-code --session-id="<session-id>"` — start session (MUST run before writing code)
- `baragi work update WORK-NNN --status=done --summary="..."` — mark done (only when user asks)

For full workflow, commands, and rules, use the `/baragi-skill` skill.

## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Testing
- Always use the `test-runner-slim` agent (via Task tool) for running tests. Do not run tests directly in Bash.
