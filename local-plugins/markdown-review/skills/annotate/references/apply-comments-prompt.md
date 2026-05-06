# Apply Comments Prompt

This template is read by Claude in a follow-up turn to apply user-written comments from a sidecar JSON file to its source markdown. **Do not run this in the same turn as `/markdown-review:annotate`** — it is a separate, user-initiated turn (FR-31).

## Inputs you receive
- `<MD_PATH>` — absolute or relative path to the source markdown file (e.g. `docs/feature/foo/2026-05-06-foo-prd.md`).
- `<MD_PATH>.comments.json` — the sidecar with comments left by the user.

## What to do

1. **Read the source markdown** at `<MD_PATH>` using the `Read` tool.

2. **Read the sidecar** at `<MD_PATH>.comments.json`. Parse JSON. Confirm `version == 1`. If you see warnings or a `version` you don't recognize, surface them in your final summary but continue best-effort.

3. **For each comment in `comments` where `applied == false`:**

   a. **Locate the target block in the markdown.** Use the comment's `anchor` to find it:
      - First try matching by `anchor.heading_path` (the chain of ancestor headings) + `anchor.preview` (first 100 chars of the block's plain text). Find the heading section, then look for a block whose plain-text starts with `anchor.preview` (allow whitespace differences).
      - If exact match fails, fall back to matching `anchor.preview` alone anywhere in the document.
      - If you still can't find it, mark the comment as **orphaned** — leave `applied = false` and note it in the summary at the end.

   b. **Apply the user's instruction** in the body of the comment. Use the `Edit` tool to modify the source markdown. The user's comment is in plain English ("rephrase this", "delete this section", "add an example", etc.) — interpret it the way a careful human collaborator would. Make the smallest edit that satisfies the instruction.

   c. **Update the comment in the sidecar:** set `applied = true` and `applied_at` to the current ISO-8601 UTC timestamp. Use `Edit` (or rewrite the JSON) to update only that one comment.

   d. **Save your work** — both the source markdown edit AND the sidecar update happen in lockstep per comment. Don't batch all sidecar updates to the end; if you crash mid-way, the sidecar should reflect what's already applied.

4. **At the end, write a one-paragraph summary to the user:**
   - How many comments were applied.
   - How many were orphaned (couldn't find a target block) — list each by anchor preview + body text.
   - Any sidecar warnings encountered.

5. **Do NOT delete applied comments** from the sidecar. They stay in the file with `applied = true` so the user has a record of what changed and where.

## Important rules

- Always edit via `Edit` (not `Write`) on the source markdown — preserve every other byte. Don't rewrite the file from scratch.
- Don't apply a comment that already has `applied == true` — skip it silently.
- Don't apply a comment whose `anchor` you can't locate — flag it as orphaned in the summary.
- If the user's instruction is ambiguous or you'd guess wrong, leave the comment unapplied and note it in the summary as "needs clarification: <preview> — <body>".
- Process comments in the order they appear in the sidecar (creation order — FR-20).

## Sidecar JSON shape

```json
{
  "version": 1,
  "source_file": "/abs/path/to/doc.md",
  "comments": [
    {
      "id": "<uuid4 hex>",
      "anchor": {
        "heading_path": "## Goals & Non-Goals > Non-Goals",
        "block_index_in_section": 1,
        "text_hash": "<sha256[:12]>",
        "preview": "<first 100 chars of plain text>"
      },
      "body": "<user instruction, ≤ 2000 chars>",
      "created_at": "2026-05-06T13:42:00+00:00",
      "updated_at": "2026-05-06T13:42:00+00:00",
      "applied": false,
      "applied_at": null
    }
  ]
}
```

## Anchor format reference

- `heading_path`: chain of ancestor headings joined by ` > ` (with the leading hash markers, e.g. `## Goals > ### Subgoal`). Empty string for blocks before any heading.
- `block_index_in_section`: 0-based index of the non-heading block within its `heading_path` scope.
- `text_hash`: `sha256(plain_text)[:12]` — useful as a tiebreaker for ambiguous matches.
- `preview`: first 100 characters of the block's plain text — your primary locator.
