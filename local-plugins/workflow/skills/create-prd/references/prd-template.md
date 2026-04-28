# PRD Template

Use this structure when writing a PRD. Be specific and testable in functional requirements. Do not include technical implementation details (schemas, API design, code) — those belong in the plan.

```markdown
# PRD: <feature>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved | Shipped

---

## 1. Why
One paragraph. The user pain point + the business reason. If you can't write
this without filler, the feature isn't ready.

## 2. Goals & Non-Goals
**Goals**
- Specific, measurable where possible. ≤4 bullets.

**Non-Goals**
- What this explicitly will NOT do in v1. The boundary that prevents scope
  creep. ≥2 bullets (if you can't think of any, you haven't bounded scope).

## 3. User Stories
1. As a <user>, I want to <action> so that <outcome>.
2. ...

Skip if there's only one obvious user type and the goal already implies the
action — don't pad.

## 4. Functional Requirements
Numbered, testable, no "should/might/could". Each FR maps to ≥1 test later.

- **FR-01:** <requirement>
- **FR-02:** <requirement>

Edge cases as their own FRs:
- **FR-0X:** When <condition>, system <behavior>.

## 5. UX & Flow
**Happy path:**
1. <screen> → user <action>
2. <screen> → system <response>

**Alternate / error / empty / loading states:**
- Empty: <what user sees>
- Error: <what user sees>
- Loading: <what user sees>

**Mockups:** <figma link or "n/a — derives from existing components">

## 6. Permissions, Privacy, Analytics  *(omit any that don't apply)*
**Permissions:** <what's needed, when prompted>
**Data:** <what's collected / stored / shared>
**Events:**
| Event | Trigger | Parameters |
|-------|---------|------------|

**Success metric:** <metric : target by timeframe>

## 7. Release
- Feature flag: <yes/no, name>
- Rollout: <staged segments, or "ship to all">
- Update required: <OTA / force update / n/a>

## 8. Open Questions
- [ ] <question>
- [ ] <question>

If empty, write "None known" — empty section is suspicious.
```

**Filename convention:** `docs/feature/YYYY-MM-DD-<feature-name>-prd.md` (kebab-case feature name; date is the day the PRD was authored).
