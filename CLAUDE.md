## Baragi (Work Management)

Baragi is a CLI tool for work and project management. When the user mentions a baragi work item, asks to check works, or starts work on a task, refer to the reference file for workflow and commands.

See `~/.claude/references/baragi.md` for workflow and commands.

## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Testing
- Always use the `test-runner-slim` agent (via Task tool) for running tests. Do not run tests directly in Bash.
