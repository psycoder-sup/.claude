## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Subagents
- Subagents can't spawn subagents. The `Agent`/`Task` tool isn't available inside one and can't be enabled.
- Never tell a subagent to "use X agent" — give the underlying command instead. Main session dispatches all agents.

@RTK.md
