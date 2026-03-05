---
name: git-skill
description: This skill should be used when the user asks to "create a commit", "commit and push", "make a pull request", "understand branching strategies", "use conventional commits", or needs guidance on git best practices and safe git operations.
allowed-tools: Read, Glob, Grep, Bash(git:*), Bash(gh:*)
user-invocable: true
---

# Git Skill

Git commit, push, and pull request workflows using conventional commits with emoji prefixes.

## Arguments

```
$ARGUMENTS
```

Parse `$ARGUMENTS` into **actions** (`commit`, `push`, `pr`) and **flags** (`-A` for all-changes mode). If no actions given, default to `commit`. Auto-accept is always ON.

## Conventional Commit Format

```
<emoji> <type>(<scope>): <description>
```

| Type | Emoji | Description |
|------|-------|-------------|
| feat | ✨ | New feature |
| fix | 🐛 | Bug fix |
| docs | 📝 | Documentation |
| style | 💄 | Formatting, styling |
| refactor | ♻️ | Code restructuring |
| perf | ⚡️ | Performance improvement |
| test | ✅ | Adding tests |
| chore | 🔧 | Maintenance tasks |
| ci | 👷 | CI/CD changes |
| security | 🔒️ | Security fix |
| deps | ➕/➖ | Add/remove dependencies |
| breaking | 💥 | Breaking changes |

## Commit

1. **Analyze** — run `git status`, `git diff`, `git diff --staged`. Read untracked files with Read tool.
   - Default: only commit files changed during this session
   - `-A`: commit ALL repo changes, grouped into logical commits (verify none left out)
2. **Propose** — show files and commit message(s)
3. **Execute** — stage and commit using heredoc (never `$()` substitution):

```bash
git add <files> && git commit -F - <<'EOF'
<emoji> <type>(<scope>): <description>

<optional body>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
```

4. **Verify** — `git log --oneline -<N>`

## Push

1. Show branch info with `git branch -vv`
2. `git push -u origin <current-branch>`
3. Verify with `git log --oneline -1`

## PR

1. **Analyze** — `git log main..HEAD --oneline`, `git diff main...HEAD`, `git branch -vv`
2. **Propose** — show PR title and description
3. **Execute** — push if needed, then `gh pr create --title "<title>" --body "<body>"`
4. Show PR URL

## Action Chaining

Execute in order: `commit` → `push` → `pr`. Stop on any error.

## Safety

- Never force push to main/master
- Never use `git -C <path>` — always run from project root
- Check for uncommitted changes before checkout/rebase
