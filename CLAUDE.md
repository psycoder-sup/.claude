## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Worktrees
- When on the `main` branch and the user's request requires any code or file changes, use `EnterWorktree` to move into a dedicated worktree before making edits. Do this before writing any changes so `main` stays clean.

## Agents
- When spawning the default `Explore` agent, always pass `model: "sonnet"` — exploration/search work does not need a larger model.


@RTK.md
