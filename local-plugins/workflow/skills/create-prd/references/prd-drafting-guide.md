# PRD Drafting Guide

Behavioral guidance when drafting a PRD directly (not via the `feature-planner` subagent).

## Scope

- Product planning only — user problems, user flows, functional requirements, UX, analytics, and release strategy.
- Technical implementation (architecture, database schema, API design, code patterns) is **out of scope** — that belongs in the SPEC.
- If a concern is half-product, half-technical (e.g., "we need offline support"), phrase it as the *user requirement* ("users can view X while offline"), not the technical mechanism.

## Clarification Dialog

When gathering requirements before drafting:

- Ask **one question per message**. Do NOT batch 3-5 questions.
- Prefer **multiple-choice questions** when the option space is bounded. Use open-ended only when you genuinely need free text.
- Focus each question on the 1-2 biggest unknowns:
  - User goal / pain point
  - Scope boundaries (what's out of scope for v1)
  - Key user flows and edge cases
  - Success metrics
  - Constraints or dependencies
- Stop asking once you have enough to draft. If the user gave a detailed prompt up front, skip clarification entirely.
- Be flexible — if an answer invalidates an earlier assumption, back up and reconsider.

## Project Context (Read Before Drafting)

1. `CLAUDE.md` at project root — tech stack, conventions, references to key docs.
2. The project's main PRD if one exists — existing features and product direction.
3. The project's design system doc if referenced — available components, tokens, patterns.
4. Glob/Grep over existing screens and features — avoid duplication, ensure consistency.

Keep exploration proportionate — a PRD doesn't need a full codebase audit.

## Drafting Rules

- **Fill every section.** Empty sections are PRD failures.
- **Testable requirements.** Every FR must be a statement you could write a test for. "The system should handle errors gracefully" is not testable. "On network failure, display banner X with retry button" is.
- **No implementation details.** No schemas, no API routes, no code, no library names. Phrase everything in user-observable or product terms.
- **Reference design system components by name** when applicable ("uses `BottomSheet` from the design system"), not structural CSS.
- **Flag open questions explicitly.** Section 10 is for real unresolved questions with owners and dates, not filler.
- **Date awareness.** Use the current date in YYYY-MM-DD when authoring.
- **Be concise.** Thorough but not padded — every sentence should carry information.

## Common Failure Modes

- **Vague FRs** (-quality): "should work well", "handle errors appropriately".
- **Missing non-goals**: scope will creep during spec/implementation.
- **Only happy-path flows**: no empty, error, or loading states defined.
- **Placeholder analytics**: "track engagement" without specific events or parameters.
- **"TBD" anywhere**: unresolved items aren't requirements.
- **Restating the feature as the problem**: the problem should describe a user pain, not the feature you want to build.

## When the Scope is Too Large

If the feature request spans multiple independent subsystems (chat + billing + analytics + file storage), stop and decompose before drafting. Each sub-project gets its own PRD. Writing one mega-PRD for a platform leads to a document nobody can ship from.
