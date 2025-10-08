# Git Commit

Create commits with changed files. Follow commit rules below.

## Commit Message Structure

A good commit message has three parts:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Note:** The scope is optional but recommended for larger projects.

### Subject Line (Required)
- **50 characters or less**
- Start with a capital letter
- Use imperative mood ("Add feature" not "Added feature")
- No period at the end
- Clear and concise summary

### Body (Optional)
- Wrap at 72 characters
- Explain **what** and **why**, not how
- Separate from subject with a blank line
- Use bullet points for multiple points

### Footer (Optional)
- Reference issue numbers
- Note breaking changes
- Add co-authors

## Commit Types (Conventional Commits)

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add user authentication` |
| `fix` | Bug fix | `fix: resolve memory leak in cache` |
| `docs` | Documentation only | `docs: update API documentation` |
| `style` | Code style/formatting | `style: fix indentation in auth module` |
| `refactor` | Code restructuring | `refactor: simplify user validation logic` |
| `test` | Add or update tests | `test: add unit tests for login` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `perf` | Performance improvement | `perf: optimize database queries` |

## Commit Scope

The scope provides additional context about which part of the codebase is affected by the commit. It appears in parentheses after the type.

### Format
```
<type>(<scope>): <subject>
```

### What is a Scope?

A scope identifies the section, module, component, or area of the codebase that was changed. It helps team members quickly understand where changes were made without reading the full commit.

### Common Scope Examples

**By Feature/Module:**
```
feat(auth): add two-factor authentication
fix(payment): resolve stripe webhook timeout
docs(api): document rate limiting
```

**By Component (Frontend):**
```
fix(navbar): correct mobile menu alignment
style(button): update primary button colors
feat(modal): add close animation
```

**By Layer/Service (Backend):**
```
fix(database): resolve connection pool leak
refactor(api): simplify error handling
perf(cache): implement Redis caching
```

**By File/Area:**
```
docs(readme): add Docker setup instructions
test(user-service): add integration tests
chore(deps): update security packages
```

### Defining Scopes for Your Project

Different projects need different scopes. Here are approaches:

#### Small Project
```
feat(ui): ...
feat(api): ...
feat(db): ...
```

#### Medium Project (by feature area)
```
feat(auth): ...
feat(orders): ...
feat(inventory): ...
feat(reports): ...
```

#### Large Project (by component)
```
feat(user-dashboard): ...
feat(admin-panel): ...
feat(mobile-app): ...
feat(email-service): ...
```

#### Monorepo (by package)
```
feat(web-app): ...
feat(mobile-app): ...
feat(shared-utils): ...
feat(api-gateway): ...
```

### Scope Best Practices

**DO ✅**
- Use consistent, agreed-upon scopes across the team
- Keep scopes short (one or two words)
- Use lowercase for scopes
- Document your project's scopes in CONTRIBUTING.md
- Use existing scopes rather than creating new ones
- Be specific enough to be useful

**DON'T ❌**
- Make up scopes on the fly without team agreement
- Use overly broad scopes like `code` or `files`
- Use different names for the same scope (`auth` vs `authentication`)
- Create too many scopes (becomes meaningless)
- Mix different scope systems

### When to Skip the Scope

Scope is optional. Skip it when:
- The change affects multiple areas equally
- Your project is small and doesn't need scopes
- The change is project-wide (like dependency updates)
- The type already provides enough context

Examples without scope:
```
chore: update all dependencies
docs: fix typos throughout codebase
ci: add GitHub Actions workflow
```

### Multiple Scopes

If a change affects multiple scopes, you need to split it into multiple commits

**Split into multiple commits** 
```
feat(auth): add OAuth provider
feat(profile): integrate OAuth login
```

### Real-World Scope Examples

**E-commerce Application:**
```
fix(cart): prevent duplicate items
feat(checkout): add PayPal payment option
perf(search): implement Elasticsearch
refactor(inventory): simplify stock tracking
test(orders): add e2e checkout tests
```

**SaaS Dashboard:**
```
feat(analytics): add custom date ranges
fix(billing): correct invoice calculation
docs(api): document webhook events
style(dashboard): improve responsive layout
```

**Mobile App:**
```
feat(camera): add photo filters
fix(offline): resolve sync conflicts
perf(images): implement lazy loading
test(auth): add biometric auth tests
```

## Examples

### Simple Commit
```
fix(login): correct typo in welcome message
```

### With Scope
```
feat(api): add user profile endpoint

Implement GET /api/users/:id endpoint with:
- User profile data retrieval
- Avatar URL generation
- Privacy settings filtering

Closes #123
```

### Detailed Commit
```
feat(auth): implement password reset functionality

Add email-based password reset flow:
- Generate secure reset tokens
- Send reset emails via SendGrid
- Validate tokens with 1-hour expiration
- Update password securely

Closes #123
```

### Breaking Change
```
feat(api)!: change authentication to OAuth 2.0

BREAKING CHANGE: API now requires OAuth 2.0 tokens instead of API keys.
Users must migrate to the new authentication flow.

Migration guide: docs/oauth-migration.md
```

### Multiple Components
```
fix(checkout): resolve payment processing issues

- Fix race condition in order creation
- Add validation for coupon codes
- Improve error messages for failed payments

Fixes #456, #789
```

## Best Practices

### DO ✅
- Write in the imperative mood: "Fix bug" not "Fixed bug"
- Keep the subject line under 50 characters
- Separate subject from body with a blank line
- Focus on why the change was made
- Reference issues and PRs
- Make atomic commits (one logical change)
- Test before committing

### DON'T ❌
- Use generic messages like "fix stuff" or "WIP"
- Commit commented-out code
- Mix unrelated changes
- Commit broken code
- Include sensitive information
- Use vague descriptions

## Common Git Commands

### Basic Workflow
```bash
# Check status
git status

# Stage specific files
git add file1.js file2.js

# Stage all changes
git add .

# Commit with message
git commit -m "feat: add new feature"
```

## Writing Good Commit Messages

### Template
```
# <type>(<scope>): <subject> (max 50 chars)
# |<----  Using a max of 50 characters  ---->|

# Explain why this change is being made
# |<----   Try to limit to 72 characters   ---->|

# Provide links to related issues, tickets, or PRs
# Resolves: #123
# See also: #456, #789
```

### Real-World Examples

**Good:**
```
fix(orders): prevent race condition in processing

Orders were occasionally processed twice when users
clicked the submit button multiple times. Added
debouncing and request deduplication to prevent this.

Fixes #1234
```

**Also Good (without scope):**
```
docs: update installation instructions

Added Docker setup steps and troubleshooting section
for common installation issues.
```

**Bad:**
```
fixed some bugs and updated code
```

**Remember:** Good commits make code review easier, debugging faster, and collaboration smoother!
