---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
model: claude-3-5-haiku-20241022
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes, create one or more commits.
Follow the commit message rules below

## Commit messages rules

### Format

```
<type>(<scope>): <description>
```

Or without scope:

```
<type>: <description>
```

### Types

| Type       | Description                                      |
|------------|--------------------------------------------------|
| `feat`     | New feature or functionality                     |
| `fix`      | Bug fix                                          |
| `refactor` | Code restructuring without changing behavior     |
| `chore`    | Maintenance tasks (dependencies, configs, etc.)  |
| `docs`     | Documentation changes                            |
| `release`  | Version releases                                 |
| `rollback` | Reverting previous changes                       |

### Scope

The scope is optional and should be a domain or component name:

- **Domain scopes**: `home`, `listing`, `rental`, `chat`, `auth`, `navigation`, `payment`, `profile`
- **Component scopes**: `LandingScreen`, `HomeScreen`, `ProductCarousel`, etc.
- **Feature scopes**: `referral`, `location`, `category`

Use lowercase for general domains (e.g., `home`, `auth`) and PascalCase when referencing specific components (e.g., `LandingScreen`, `ChatRoute`).

### Description

- Start with a verb (add, update, fix, remove, integrate, etc.)
- Use present tense ("add feature" not "added feature")
- Keep it concise (under 72 characters)
- No period at the end

### Examples

```bash
# Features
feat(home): Unify HomeScreen for both authenticated and public access
feat(navigation): add unread message count indicator to tab layout
feat(auth): Add hooks for managing return URL after login

# Bug fixes
fix(navigation): Fix type-safe routing and state update during render
fix(location): Improve location fetching speed and reliability
fix(LandingScreen): Fix logo disappearing in Scene 3

# Refactoring
refactor(HomeScreen): streamline layout and spacing in CuratedSection
refactor: Migrate to carousel intro and remove old intro screens

# Maintenance
chore: update app version to 25.34.0
chore(doc): remove unecessary doc
chore: add react-native-qrcode-svg dependency in package.json

# Documentation
docs: Add backend request for public listing access API changes
docs: Add tools and services documentation (#325)

# Release
release: 25.31.16

# Rollback
rollback: stripe
```

### PR References

When a commit is associated with a PR, append the PR number at the end:

```
feat: Add unified Save Photos screen for rental transactions (#319)
docs: Add tools and services documentation (#325)
```

### Breaking Changes

For breaking changes, add `BREAKING CHANGE:` in the commit body or use '!' after the type:

```
feat(auth)!: Remove legacy authentication flow
```
