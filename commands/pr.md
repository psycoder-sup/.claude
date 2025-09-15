# Make Pull Request for Github

Make Pull Request Draft to **develop** branch for Github based on code changes. Reference related github issues, use `gh issue list` to search relavent issues.
Use `gh pr create --base develop --draft --title "" --body ""` command to create pr. Before make PR, please push cthe current branch.
Use @git-workflow-manager.

## Find code changes

- Use `git` command to find out code changes compared to develop branch

## Find related Issues

- Use `gh issue list` command to search relavent issues.
- Use `gh issue view {issue_no}` command to view issue detail.

## Pull Request Body

Body should follow the below format.

```text
## Description
Brief summary of what this PR does and why it's needed.

## Related Issues
Fixes #(issue number)
Closes #(issue number)
Related to #(issue number)

## Changes Made
- List the main changes made in this PR
- Be specific about what was added, modified, or removed
- Include any architectural decisions or trade-offs
```
