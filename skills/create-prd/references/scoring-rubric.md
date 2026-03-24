# PRD Scoring Rubric

Detailed criteria for the devils-advocate agent to score each PRD section. The overall score is a weighted average.

## Section Weights

| Section | Weight | Rationale |
|---------|--------|-----------|
| 1. Overview | 5% | Sets context but lightweight |
| 2. Problem Statement | 12% | Must justify why we're building |
| 3. Goals & Non-Goals | 12% | Scope clarity prevents creep |
| 4. User Stories | 12% | Validates user-centric thinking |
| 5. Functional Requirements | 22% | Core of the PRD — must be testable |
| 6. UX & Design | 17% | User flow completeness is critical |
| 7. Permissions & Privacy | 5% | Compliance is pass/fail |
| 8. Analytics & Instrumentation | 5% | Must have measurable success |
| 9. Release Strategy | 5% | Rollout plan prevents chaos |
| 10. Open Questions | 3% | Honesty about unknowns |
| 11. Appendix | 2% | Nice-to-have context |

## Per-Section Scoring Criteria

### 1. Overview (5%)
- **1.0**: Clear feature name, concise summary, compelling "what and why"
- **0.7**: Summary present but vague on motivation
- **0.4**: Missing key context or poorly scoped summary
- **0.0**: Missing or placeholder

### 2. Problem Statement (10%)
- **1.0**: Specific pain point, evidence or data cited, clear business opportunity, current workaround described
- **0.7**: Pain point described but generic, no data, business case weak
- **0.4**: Vague problem, no evidence, sounds like solution-hunting
- **0.0**: Missing or just restates the feature

### 3. Goals & Non-Goals (10%)
- **1.0**: Goals are specific and measurable, non-goals explicitly bound scope, non-goals prevent likely scope creep
- **0.7**: Goals present but not measurable, non-goals exist but are obvious
- **0.4**: Only goals listed, non-goals missing or trivial
- **0.0**: Missing or just a feature list

### 4. User Stories (10%)
- **1.0**: Covers all user types, each story has clear value, stories map to functional requirements
- **0.7**: Main user type covered, some stories lack clear value
- **0.4**: Only happy-path user, stories are rephrased requirements
- **0.0**: Missing or template placeholders

### 5. Functional Requirements (20%)
- **1.0**: Every requirement is testable, numbered, covers happy path + edge cases, rules and logic are explicit, no ambiguous language ("should", "might", "could")
- **0.7**: Requirements present and numbered but some are vague or untestable
- **0.4**: Requirements are high-level descriptions, not testable, missing edge cases
- **0.0**: Missing or just bullet points without specificity

### 6. UX & Design (15%)
- **1.0**: Complete user flow (happy + alternate + error + empty + loading), platform differences noted, references design system components by name
- **0.7**: User flow present but missing error/empty states, no platform differences
- **0.4**: Only happy path described, no states considered
- **0.0**: Missing or just "see Figma"

### 7. Permissions & Privacy (5%)
- **1.0**: All device permissions listed with when they're requested, data lifecycle clear, compliance requirements identified
- **0.7**: Permissions listed but no context on when requested
- **0.4**: Generic "standard permissions"
- **0.0**: Missing

### 8. Analytics & Instrumentation (5%)
- **1.0**: Specific GA4 events with parameters, success metrics with targets and timeframes, A/B test design if applicable
- **0.7**: Events listed but parameters vague, metrics without targets
- **0.4**: "We'll track usage" — no specifics
- **0.0**: Missing

### 9. Release Strategy (5%)
- **1.0**: Feature flag plan, target segment defined, update requirements specified, rollout stages clear
- **0.7**: Basic rollout mentioned, missing staging
- **0.4**: "Ship to everyone" — no strategy
- **0.0**: Missing

### 10. Open Questions (3%)
- **1.0**: Real unresolved questions with owners and due dates, questions are specific and actionable
- **0.7**: Questions listed but no owners or dates
- **0.4**: Filler questions that should have been answered during planning
- **0.0**: "None" or missing (suspicious — there are always open questions)

### 11. Appendix (2%)
- **1.0**: Relevant research, competitive analysis, or prior discussion links
- **0.5**: Present but minimal
- **0.0**: Missing (acceptable if truly nothing to add)

## Score Thresholds

| Range | Verdict | Action |
|-------|---------|--------|
| 0.9 - 1.0 | Exceptional | Ready to build |
| 0.8 - 0.89 | Strong | Minor polish, ready to build |
| 0.7 - 0.79 | Decent | Address Major issues before building |
| 0.6 - 0.69 | Weak | Fix Blockers, significant revision needed |
| < 0.6 | Poor | Needs fundamental rethink |

## Common Deductions

These patterns frequently lower scores:

- **Vague functional requirements** (-0.1 to -0.2): "The system should handle errors gracefully" is not testable
- **Missing non-goals** (-0.05 to -0.1): Scope creep risk when boundaries aren't set
- **No error/empty states** (-0.1): Suggests the happy path hasn't been stress-tested
- **Placeholder analytics** (-0.05): "Track engagement" without specific events
- **No platform UX differences** (-0.05): iOS and Android often have UX differences worth noting
- **"TBD" in requirements** (-0.1 per instance): Unresolved requirements are not requirements
- **Weak problem statement** (-0.1 to -0.15): No evidence the problem is real, or solution doesn't address the stated problem
