## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Testing
- Main session: use `test-runner-slim` (via Task tool) for tests, not raw Bash.
- Subagent: run tests via Bash directly (subagents can't dispatch other subagents).

## Subagents
- Subagents can't spawn subagents. The `Agent`/`Task` tool isn't available inside one and can't be enabled.
- Never tell a subagent to "use X agent" — give the underlying command instead. Main session dispatches all agents.
