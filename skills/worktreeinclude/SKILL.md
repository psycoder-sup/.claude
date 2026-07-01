---
name: worktreeinclude
description: Generate a .worktreeinclude file for the current git repository so Claude Code copies gitignored local files (env, secrets, certs) into new worktrees.
disable-model-invocation: true
argument-hint: "[path]"
allowed-tools: ["Read", "Write", "Bash", "Glob", "Grep"]
---

# /worktreeinclude

Create a `.worktreeinclude` file at the root of the current repository so that Claude
Code automatically copies the local, gitignored files a checkout needs (e.g. `.env`,
secrets, certificates) into every new git worktree.

## Background (official behavior)

- A git worktree is a fresh checkout, so **untracked/gitignored files are NOT present** in it.
- `.worktreeinclude` lives at the **repository root** and uses **`.gitignore` syntax**.
- Only files that **match a pattern AND are gitignored** get copied. Tracked files are
  never duplicated.
- It applies to `claude --worktree`, subagent worktrees (`isolation: worktree`), and
  desktop parallel sessions.
- ⚠️ Defining a `WorktreeCreate` hook **disables** `.worktreeinclude` (the hook replaces
  default git behavior). Do not combine them — `.worktreeinclude` is the recommended path
  for plain git repos.

## Procedure

1. **Locate the repo root.** If the user passed a path argument, treat it as the target repo;
   otherwise use the current working directory's repo. Run `git rev-parse --show-toplevel`
   to resolve the root. Bail out with a clear message if it is not a git repository.

2. **Enumerate gitignored files that actually exist** (these are the only candidates that can
   ever be copied):
   ```bash
   git -C "<repo-root>" ls-files --others --ignored --exclude-standard
   ```

3. **Classify the candidates.** Include only *non-regenerable local config and secrets*.
   Exclude anything that should be reinstalled/rebuilt instead of copied.

   | Include (local config/secrets needed to run) | Exclude (regenerable / large) |
   |---|---|
   | `.env`, `.env.local`, `.env.*.local` | `node_modules/`, `vendor/` |
   | local secrets/config: `config/secrets.json`, `*.local.json` | build output: `dist/`, `build/`, `.next/`, `target/` |
   | service-account keys / certs: `*.pem`, `serviceAccount*.json` | caches/logs: `.cache/`, `*.log`, `coverage/` |
   | auth-bearing `.npmrc`, `.envrc` | virtualenvs: `.venv/`, `__pycache__/` |

   Principle: copy only what **cannot be regenerated** by a setup command. Dependencies and
   build artifacts should be restored with `npm install` / equivalent inside the worktree,
   not copied (they are large and often contain platform-specific or absolute paths).

4. **Only list files that genuinely exist and are gitignored.** Do not invent patterns for
   files that aren't there. Prefer specific paths over broad globs to avoid copying junk.

5. **Write `.worktreeinclude`** at the repo root using `.gitignore` syntax. Include short
   `#` comments grouping the entries. Example shape:
   ```text
   # Environment variables
   .env
   .env.local
   .env.*.local

   # Local secrets / config
   config/secrets.json
   serviceAccount.json

   # Certificates
   certs/*.pem
   ```

6. **Report back.** Show the final file contents and a one-line rationale per entry (why it
   was included). Note anything you deliberately excluded (e.g. "skipped node_modules —
   reinstall in the worktree instead").

## Verification (offer, don't auto-run)

Suggest the user verify with:
```bash
claude --worktree test-include
```
Then check that the listed files appear in `.claude/worktrees/test-include/`. With no changes,
the test worktree is cleaned up automatically. Also recommend adding `.claude/worktrees/` to
`.gitignore` if it isn't already.

## Notes

- `.worktreeinclude` copies files only; it does **not** run setup commands. Dependency
  installation / env bootstrapping is done per worktree separately (Claude Code does not have
  a dedicated auto-run-setup config for this).
- If the repo already has a `.worktreeinclude`, read it first and update it rather than
  overwriting — preserve entries the user added intentionally.
