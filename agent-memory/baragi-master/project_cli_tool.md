---
name: CLI Tool feature planning
description: Baragi list and work item structure for the aterm CLI tool feature (LIST-019)
type: project
---

CLI Tool feature is tracked in LIST-019 with 6 sequential phases (WORK-297 through WORK-302).

Phase dependencies: 1 -> 2 -> 3 -> 4,5 -> 6 (Phase 4 and 5 both depend on Phase 3; Phase 6 depends on both 4 and 5).

**Why:** The CLI tool spans IPC foundation, env var injection, CRUD commands, status reporting, notifications, and logging — each phase has real build-order dependencies (can't implement CRUD without the IPC foundation, can't do status without CRUD handler infrastructure).

**How to apply:** When working on this feature, always check which phase parent is unblocked via `baragi next --list-id=LIST-019`. Phase 1 (WORK-297) is the unblocked entry point.

Reference docs:
- PRD: docs/feature/cli-tool/cli-tool-prd.md
- SPEC: docs/feature/cli-tool/cli-tool-spec.md (Section 15 = phases, Section 16 = model changes)
