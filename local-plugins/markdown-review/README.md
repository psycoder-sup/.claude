# markdown-review

A markdown comment review skill that opens a document in a browser for block-level commenting. Comments are written to a sidecar JSON file, enabling a structured handoff to Claude for applying edits in a subsequent turn.

## Install

This is a local plugin, automatically discovered from `local-plugins/markdown-review/`.

## Invocation

```
/markdown-review:annotate <path-to-md>
```

Example:

```
/markdown-review:annotate docs/feature/bookmarks/2026-04-28-bookmarks-prd.md
```

## What it does

- Starts a local web server bound to `127.0.0.1` on a free port
- Opens the markdown document in a browser for per-block commenting
- Blocks are heading, paragraph, list item, code block, table, and blockquote
- Each comment is anchored by a stable block identifier (heading path + index + content hash)
- Writes all comments to a sidecar file `<file>.comments.json`
- Prints a copy-pasteable next-turn prompt to apply comments in a separate Claude turn

## Sidecar format

See plan §3 for the schema; full reference filled in by task 11.

## Status

v0.1.0 — under construction.
