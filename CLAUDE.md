## Planning
- Non-trivial tasks should always start with a plan before implementing. Use the built-in plan agent (`EnterPlanMode`) to design the approach and get user approval first.

## Worktrees
- When on the `main` branch and the user's request requires any code or file changes, use `EnterWorktree` to move into a dedicated worktree before making edits. Do this before writing any changes so `main` stays clean.


@RTK.md
