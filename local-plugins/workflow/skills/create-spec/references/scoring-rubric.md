# SPEC Scoring Rubric

Detailed criteria for the spec-reviewer agent to score each SPEC section. The overall score is a weighted average.

## Section Weights

| Section | Weight | Rationale |
|---------|--------|-----------|
| 1. Overview | 3% | Sets context but lightweight |
| 2. Database Schema | 15% | Data model errors are the hardest to fix later |
| 3. API Layer | 12% | Contract correctness drives integration quality |
| 4. State Management | 8% | Cache/state bugs are subtle and painful |
| 5. Component Architecture | 8% | Structure must match codebase conventions |
| 6. Navigation | 4% | Must integrate with existing routing |
| 7. Type Definitions | 5% | Type safety prevents downstream bugs |
| 8. Analytics Implementation | 3% | Must match PRD instrumentation requirements |
| 9. Permissions & Security | 10% | Security gaps are blockers |
| 10. Performance Considerations | 7% | Must address real bottlenecks, not generic advice |
| 11. Migration & Deployment | 8% | Irreversible migrations are catastrophic |
| 12. Implementation Phases | 7% | Phases must be independently shippable |
| 13. Test Strategy | 1% | PRD→test mapping tables (detailed scenarios live in 13.5) |
| 13.5. Test Skeletons | 4% | Concrete failing-test outlines — implementer's starting code |
| 14. Technical Risks & Mitigations | 3% | Honest risk assessment prevents surprises |
| 15. Open Technical Questions | 2% | Honesty about unknowns |

## Per-Section Scoring Criteria

### 1. Overview (3%)
- **1.0**: Clear summary of what the spec covers, how it fits into existing architecture, explicit reference to the PRD it implements
- **0.7**: Summary present but vague on architectural fit
- **0.4**: Generic overview, doesn't reference existing architecture
- **0.0**: Missing or placeholder

### 2. Database Schema (15%)
- **1.0**: All tables/columns defined with types, constraints, defaults, and descriptions. Indexes specified with justification. Access policies cover all CRUD operations with conditions. Table modifications are safe (additive or backward-compatible). Data flow is clear end-to-end. References real existing tables by name.
- **0.7**: Tables defined but missing some constraints or defaults. Indexes listed without justification. Access policies present but incomplete.
- **0.4**: Only new tables described, no modifications to existing tables considered. Missing indexes or access policies. No data flow.
- **0.0**: Missing, placeholder, or describes tables that don't match the codebase

### 3. API Layer (12%)
- **1.0**: Every query/mutation defined with operation, tables, filters, return type, and calling component. Server functions have clear trigger, input, output, and logic. Error responses specified. Pagination strategy defined where needed. Follows existing API conventions.
- **0.7**: Queries listed but missing some details (filters, error responses). Server functions present but logic is vague.
- **0.4**: Only happy-path queries described. No error handling. Doesn't reference existing API patterns.
- **0.0**: Missing or generic ("standard REST endpoints")

### 4. State Management (8%)
- **1.0**: Cache keys follow existing conventions. Stale time and invalidation strategy specified per query. Optimistic updates defined where UX requires them. Local state justified (why server state isn't sufficient). Race conditions addressed.
- **0.7**: Cache hooks listed but stale time or invalidation vague. No optimistic updates considered.
- **0.4**: Only "use React Query" or equivalent — no specifics on keys, invalidation, or local state.
- **0.0**: Missing

### 5. Component Architecture (8%)
- **1.0**: Directory layout follows project conventions. Every screen has route, params, layout, states (loading/error/empty/populated), and design system components referenced by name. Reusable components have props and behavior defined.
- **0.7**: Directory structure present. Screens listed but states incomplete. Some components lack prop definitions.
- **0.4**: Only a component list — no structure, no states, no design system references.
- **0.0**: Missing

### 6. Navigation (4%)
- **1.0**: Route table with name, screen, stack/navigator, and params. Navigation flow describes entry/exit points. Deep linking considered if applicable. No route conflicts with existing navigation.
- **0.7**: Routes listed but missing params or stack assignment. No conflict check.
- **0.4**: Only "add a new screen" — no routing details.
- **0.0**: Missing

### 7. Type Definitions (5%)
- **1.0**: Every type has field, type, and description in table format. Types align with database schema. Reuses existing types where appropriate. Discriminated unions for state variants.
- **0.7**: Types listed but some fields lack descriptions or don't match schema.
- **0.4**: Only interface names — no field definitions.
- **0.0**: Missing

### 8. Analytics Implementation (3%)
- **1.0**: Event table with name, trigger point, and instrumentation location. Maps directly to PRD analytics requirements. Follows existing event naming conventions.
- **0.7**: Events listed but trigger points vague or don't map to PRD.
- **0.4**: "Track key events" — no specifics.
- **0.0**: Missing

### 9. Permissions & Security (10%)
- **1.0**: Access policies defined for every data operation with conditions. Client-side guards specified (permission checks, auth guards, feature flags). Input validation defined at system boundaries. Data exposure risks addressed.
- **0.7**: Access policies present but conditions incomplete. Client-side guards mentioned but not specified per screen.
- **0.4**: Only "check if user is authenticated" — no granular policies.
- **0.0**: Missing (automatic blocker for any feature touching user data)

### 10. Performance Considerations (7%)
- **1.0**: Specific pagination strategy with page sizes. Caching strategy with TTLs. Optimistic updates for latency-sensitive operations. Lazy loading for heavy components. Bundle impact estimated. Addresses real bottlenecks specific to this feature, not generic advice.
- **0.7**: Pagination and caching mentioned but no specifics. Some generic performance advice mixed in.
- **0.4**: "Use pagination and caching" — no strategy specific to this feature.
- **0.0**: Missing

### 11. Migration & Deployment (8%)
- **1.0**: Migration files listed with specific operations. Migrations are reversible (or explicitly noted as irreversible with justification). Feature flag strategy defined. Rollback plan specified. Deployment order accounts for dependencies. Zero-downtime path described.
- **0.7**: Migrations listed but reversibility not addressed. Feature flag mentioned but no rollback plan.
- **0.4**: "Run migrations then deploy" — no details on reversibility or ordering.
- **0.0**: Missing (automatic blocker for any feature with schema changes)

### 12. Implementation Phases (7%)
- **1.0**: Each phase is independently shippable and testable. Phase boundaries are clean (no half-finished features). Dependencies between phases are explicit. First phase delivers core user-facing value. Phases align with PRD priorities.
- **0.7**: Phases listed but some aren't independently shippable. Dependencies unclear.
- **0.4**: Only "Phase 1: Backend, Phase 2: Frontend" — not user-value-oriented.
- **0.0**: Missing or single monolithic phase

### 13. Test Strategy (1%)
- **1.0**: PRD success metrics mapped to verification methods. PRD functional requirements (FR-XX) mapped to specific test cases. Unit, integration, e2e, and edge-case test types specified. Follows existing test patterns. (Concrete test code lives in Section 13.5.)
- **0.7**: Mapping tables present but incomplete coverage.
- **0.4**: "Write unit and integration tests" — no specifics or PRD traceability.
- **0.0**: Missing

### 13.5. Test Skeletons (4%)
- **1.0**: Every FR in the PRD has at least one failing-test skeleton. Each skeleton has a real test name, a setup line, and real `expect(...)` / assertion calls in the project's test framework. Skeletons match the type signatures from Section 7.
- **0.7**: Skeletons exist for most FRs but some are missing or use generic `expect(true).toBe(true)` placeholders.
- **0.4**: Only a few skeletons, or skeletons don't match the real test framework, or assertions are placeholder-only.
- **0.0**: Missing (automatic blocker — implementer has no TDD starting point)

### 14. Technical Risks & Mitigations (3%)
- **1.0**: Real risks with impact, likelihood, and concrete mitigations. Risks are specific to this feature (not generic "server might go down"). At least one risk per major architectural decision.
- **0.7**: Risks listed but mitigations are vague or generic.
- **0.4**: Only one or two obvious risks. No impact assessment.
- **0.0**: "No significant risks" (suspicious — there are always risks)

### 15. Open Technical Questions (2%)
- **1.0**: Real unresolved questions with context and impact if unresolved. Questions are specific and actionable. Honest about what hasn't been decided yet.
- **0.7**: Questions listed but missing context or impact.
- **0.4**: Filler questions that should have been answered during spec writing.
- **0.0**: "None" (suspicious — there are always open questions)

## Score Thresholds

| Range | Verdict | Action |
|-------|---------|--------|
| 0.9 - 1.0 | Exceptional | Ready to implement |
| 0.8 - 0.89 | Strong | Minor refinements, ready to implement |
| 0.7 - 0.79 | Decent | Address Major issues before implementing |
| 0.6 - 0.69 | Weak | Fix Blockers, significant revision needed |
| < 0.6 | Poor | Needs architectural rethink |

## Common Deductions

These patterns frequently lower scores:

- **Codebase mismatch** (-0.15 to -0.2): Spec references files, patterns, or conventions that don't exist in the actual codebase
- **Missing access policies** (-0.1 to -0.15): Any feature touching user data without granular access policies
- **Irreversible migration without justification** (-0.1): Schema changes that can't be rolled back
- **No cache invalidation strategy** (-0.05 to -0.1): Defining cache hooks without specifying when they invalidate
- **Generic performance advice** (-0.05): "Use pagination" without page sizes, "use caching" without TTLs
- **No PRD traceability in tests** (-0.1): Test strategy that doesn't map back to PRD requirements
- **Monolithic implementation phases** (-0.05 to -0.1): Phases that aren't independently shippable
- **Missing error handling in API layer** (-0.1): Queries/mutations without error response definitions
- **"TBD" in critical sections** (-0.1 per instance): Unresolved items in schema, API, or security sections
