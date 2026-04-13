# PRD Template

Use this structure when writing a PRD. Fill all 11 sections. Be specific and testable in functional requirements. Do not include technical implementation details (schemas, API design, code).

```markdown
# PRD: [Feature Name]

**Author:** [Author name or team name]
**Date:** [Today's date in YYYY-MM-DD]
**Version:** 1.0
**Status:** Draft

---

## 1. Overview
[What this feature is and why we're building it.]

## 2. Problem Statement
**User Pain Point:** [Frustration or unmet need. Back with data if available.]
**Current Workaround:** [How users solve this today.]
**Business Opportunity:** [Why this matters for growth, retention, or engagement.]

## 3. Goals & Non-Goals
**Goals:** [Specific, measurable where possible]
**Non-Goals:** [What this explicitly will NOT do in v1]

## 4. User Stories
| # | As a... | I want to... | So that... |
|---|---------|--------------|------------|
| 1 | [user type] | [action] | [value/outcome] |

## 5. Functional Requirements
[Numbered, testable requirements.]
**FR-01:** [Requirement]
**FR-02:** [Requirement]

## 6. UX & Design
### User Flow
```
User Flow: [Feature Name]

Precondition: [Starting state]

Happy Path:
1. [Screen/State] -> User does [action]
2. [Screen/State] -> System responds with [behavior]
...
N. [End state]

Alternate Flows:
- [Trigger] -> [Diverging path]

Error States:
- [Error condition] -> [What user sees]

Empty States:
- [When content is empty] -> [What user sees]

Loading States:
- [During async operation] -> [What user sees]
```

### Wireframes / Mockups
[Figma links or written descriptions]

### Empty States / Error States / Loading States
[What the user sees in each]

### Platform-Specific Behavior
| Behavior | iOS | Android |
|----------|-----|---------|

## 7. Permissions & Privacy
**Device Permissions:** [What's needed and when]
**Data Collected / Stored / Shared:** [What user data this creates or uses]
**Compliance:** [GDPR, COPPA, FERPA, etc.]

## 8. Analytics & Instrumentation
**Events to Log:**
| Event Name | Trigger | Parameters |
|------------|---------|------------|

**Success Metrics & Targets:** [Metric: Target by timeframe]
**A/B Test Design:** [If applicable]

## 9. Release Strategy
**Feature Flag / Gradual Rollout:** [How it rolls out]
**Target User Segment:** [Who gets access first]
**Update Requirements:** [Force update? OTA sufficient?]

## 10. Open Questions
| # | Question | Owner | Due Date |
|---|----------|-------|----------|

## 11. Appendix
[Research, competitive analysis, links]
```

**Filename convention:** `docs/feature/{feature-name}/{feature-name}-prd.md` (kebab-case).
