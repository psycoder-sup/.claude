"""
markdown_blocks — block parser, anchor builder, and resolver.

Usage::

    from server.markdown_blocks import parse_blocks, resolve_anchor, ResolveOutcome

    blocks = parse_blocks(markdown_source)
    result = resolve_anchor(some_anchor, blocks)

Heading path format
-------------------
The heading_path is the chain of ancestor headings joined by " > ", where each
heading is represented as its ATX marker (# / ## / ###, etc.) plus a space
plus the heading's plain text.  For example, a paragraph nested under an H2
"Goals" containing an H3 "Subgoal" has::

    heading_path = "## Goals > ### Subgoal"

Blocks that appear before any heading have ``heading_path = ""``.

block_index_in_section
-----------------------
A 0-based counter that counts non-heading blocks within the current
``heading_path`` scope.  The counter resets to 0 each time the
``heading_path`` changes (i.e. each time a heading token is encountered).

plain_text extraction
---------------------
- **heading**: concatenated raw text of child text nodes (no # prefix).
- **paragraph**: concatenated raw text of all inline children recursively.
- **list_item**: concatenated raw text of the item's direct ``block_text``
  children only — nested list items are excluded (they appear as their own
  ``Block`` records).
- **code_block**: the raw code body (``token["raw"]``).
- **table**: concatenated raw text of all cell children recursively.
- **blockquote**: concatenated raw text of all children recursively.
- **thematic_break**: empty string.

Per-token HTML rendering strategy
----------------------------------
Two mistune instances are created:
1. AST instance (``renderer=None``) — to obtain the structured token list.
2. HTML instance (``renderer="html"``, ``escape=True``) — to render HTML.

For each top-level token (or list_item child within a list), a single-token
``BlockState`` is built and passed to ``md_html.render_state()``.  This
produces exactly the HTML that mistune would emit for that individual block.

Both instances use the ``["strikethrough", "table"]`` plugin set so that
GFM tables and ~~strikethrough~~ are supported.
"""

import hashlib
import copy
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Literal, Optional

from server.vendor import mistune
from server.vendor.mistune.core import BlockState

# ---------------------------------------------------------------------------
# Type definitions (verbatim from plan §3)
# ---------------------------------------------------------------------------

BlockKind = Literal[
    "heading", "paragraph", "list_item", "code_block",
    "table", "blockquote", "thematic_break"
]

_PLUGINS = ["strikethrough", "table"]

# Two shared mistune instances — created once, reused.
_md_ast = mistune.create_markdown(renderer=None, plugins=_PLUGINS)
_md_html = mistune.create_markdown(renderer="html", escape=True, plugins=_PLUGINS)


@dataclass(frozen=True)
class Anchor:
    """Stable identifier for a single block."""
    heading_path: str            # e.g. "## Goals & Non-Goals > ### Non-Goals"
    block_index_in_section: int  # 0-based, counts non-heading blocks under heading_path
    text_hash: str               # sha256(plain_text)[:12]
    preview: str                 # plain_text[:100]


@dataclass
class Block:
    kind: BlockKind
    anchor: Anchor
    html: str                    # sanitized HTML (mistune escapes by default)
    plain_text: str              # used for hashing + preview
    heading_level: Optional[int] = None  # set when kind == "heading"


def anchor_dict(a: Anchor) -> dict:
    return asdict(a)


class ResolveOutcome:
    EXACT = "exact"
    BY_PATH_INDEX = "by_path_index"   # heading rename tolerated
    BY_HASH = "by_hash"               # block moved tolerated
    ORPHAN = "orphan"


@dataclass
class ResolveResult:
    outcome: str                  # one of ResolveOutcome.*
    block: Optional[Block]        # None iff outcome == ORPHAN


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Map mistune token types to our BlockKind.
_KIND_MAP: Dict[str, BlockKind] = {
    "heading": "heading",
    "paragraph": "paragraph",
    "block_code": "code_block",
    "table": "table",
    "block_quote": "blockquote",
    "thematic_break": "thematic_break",
}


def _text_hash(plain_text: str) -> str:
    """sha256(plain_text)[:12]."""
    return hashlib.sha256(plain_text.encode("utf-8")).hexdigest()[:12]


def _render_token_html(token: Dict[str, Any]) -> str:
    """Render a single mistune token to HTML using the shared HTML renderer.

    A throw-away BlockState is created, the token (deep-copied to avoid
    mutation from render_state's inline expansion) is placed in it, and
    ``render_state`` is called.
    """
    state = _md_html.block.state_cls()
    # Deep-copy so render_state can mutate children without affecting the AST
    state.tokens = [copy.deepcopy(token)]
    return _md_html.render_state(state)


def _extract_plain_text(token: Dict[str, Any], *, list_item_shallow: bool = False) -> str:
    """Recursively extract plain text from a token's children.

    :param list_item_shallow: When True, stop recursion at nested ``list``
        children (used when extracting a list_item's own text only, so that
        nested sub-items are excluded).
    """
    # Leaf: raw/text value
    tok_type = token.get("type", "")

    if tok_type == "block_html":
        return ""

    if "raw" in token:
        # block_code, codespan, and inline leaf nodes all store text in "raw"
        return token["raw"]

    # When extracting a list_item's own text, skip nested list children
    if list_item_shallow and tok_type == "list":
        return ""

    children = token.get("children", [])
    if not children:
        return ""

    parts: List[str] = []
    for child in children:
        child_type = child.get("type", "")
        # When shallow mode, skip nested list tokens at any depth
        if list_item_shallow and child_type == "list":
            continue
        parts.append(_extract_plain_text(child, list_item_shallow=list_item_shallow))

    return "".join(parts)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _make_anchor(heading_path: str, block_index: int, plain_text: str) -> Anchor:
    return Anchor(
        heading_path=heading_path,
        block_index_in_section=block_index,
        text_hash=_text_hash(plain_text),
        preview=plain_text[:100],
    )


def _heading_marker(level: int) -> str:
    return "#" * level


def _render_list_item_html(
    item_token: Dict[str, Any],
    *,
    ordered: bool,
    item_number: int,
    depth: int,
) -> str:
    """Render a single ``list_item`` wrapped in its own ``<ol>``/``<ul>``.

    Because each list item is its own commentable block, we render it in
    isolation. To preserve the visual marker (number or bullet), the rendered
    ``<li>`` is wrapped in a list element with:

    - ``start="N"`` on ``<ol>`` so ordered items keep their original number,
    - ``data-md-depth="D"`` on the wrapper so CSS can indent nested items.

    Nested ``list`` children inside the item are stripped before rendering
    (they are emitted as their own blocks by :func:`_process_list`), otherwise
    the same content would be rendered twice.
    """
    # Shallow-copy the token with a filtered children list — the inner dicts
    # are still shared, but _render_token_html deep-copies before rendering.
    filtered = {
        **item_token,
        "children": [
            c for c in item_token.get("children", []) if c.get("type") != "list"
        ],
    }
    li_html = _render_token_html(filtered).strip()

    if ordered:
        return f'<ol start="{item_number}" data-md-depth="{depth}">{li_html}</ol>'
    return f'<ul data-md-depth="{depth}">{li_html}</ul>'


def _process_list(
    list_token: Dict[str, Any],
    heading_path: str,
    section_counter: List[int],
    out: List[Block],
) -> None:
    """Walk a ``list`` token and emit one ``Block`` per ``list_item``.

    Nested lists inside a list_item are also walked recursively, producing
    their own blocks. Each item's rendered HTML is wrapped in an isolated
    ``<ol>``/``<ul>`` so ordered numbering and bullet markers survive, and
    nested-list children are excluded so they don't render twice.
    """
    attrs = list_token.get("attrs", {})
    ordered: bool = bool(attrs.get("ordered", False))
    depth: int = int(attrs.get("depth", 0))
    start_value: int = int(attrs.get("start", 1)) if ordered else 1

    list_items = [
        c for c in list_token.get("children", []) if c.get("type") == "list_item"
    ]
    for item_position, child in enumerate(list_items):
        plain_text = _extract_plain_text(child, list_item_shallow=True).strip()
        html = _render_list_item_html(
            child,
            ordered=ordered,
            item_number=start_value + item_position,
            depth=depth,
        )
        anchor = _make_anchor(heading_path, section_counter[0], plain_text)
        out.append(Block(
            kind="list_item",
            anchor=anchor,
            html=html,
            plain_text=plain_text,
        ))
        section_counter[0] += 1

        # Recurse into nested lists that live inside this list_item
        for sub_child in child.get("children", []):
            if sub_child.get("type") == "list":
                _process_list(sub_child, heading_path, section_counter, out)


def parse_blocks(markdown_source: str) -> list[Block]:
    """Parse ``markdown_source`` and return an ordered list of :class:`Block` records.

    Each block has:
    - ``kind``: one of the :data:`BlockKind` literals.
    - ``anchor``: a :class:`Anchor` with heading_path, block_index_in_section,
      text_hash (sha256[:12]), and preview (plain_text[:100]).
    - ``html``: the rendered HTML for this block (script tags escaped).
    - ``plain_text``: human-readable text used for hashing.
    - ``heading_level``: integer 1–6 when ``kind == "heading"``, else ``None``.

    Heading path format
    -------------------
    ``"## Goals > ### Subgoal"`` — ATX marker + space + heading text, joined
    by ``" > "``.  Blocks before any heading have ``heading_path = ""``.

    block_index_in_section reset
    ----------------------------
    The counter resets to 0 whenever the heading_path changes (i.e. when a
    heading token is encountered and the current heading stack is updated).
    """
    tokens = _md_ast(markdown_source)

    # Heading stack: list of (level, plain_text) tuples for current ancestor chain
    heading_stack: List[tuple] = []
    # heading_path derived from heading_stack
    heading_path: str = ""
    # 0-based counter of non-heading blocks under the current heading_path
    section_counter: List[int] = [0]  # wrapped in list for mutability in nested fn

    out: List[Block] = []

    def update_heading_path(new_level: int, text: str) -> None:
        """Update heading_stack and heading_path when a heading token is seen."""
        # Pop headings at the same or deeper level
        while heading_stack and heading_stack[-1][0] >= new_level:
            heading_stack.pop()
        heading_stack.append((new_level, text))
        nonlocal heading_path
        heading_path = " > ".join(
            f"{_heading_marker(lvl)} {txt}" for lvl, txt in heading_stack
        )
        section_counter[0] = 0  # reset index for the new section

    for token in tokens:
        tok_type = token.get("type", "")

        if tok_type == "blank_line":
            continue

        if tok_type == "heading":
            level = token["attrs"]["level"]
            plain_text = _extract_plain_text(token).strip()
            html = _render_token_html(token)
            # Update heading path BEFORE creating anchor for the heading itself
            update_heading_path(level, plain_text)
            # Headings use block_index_in_section = -1 to distinguish them from
            # non-heading blocks (which start at index 0).  This avoids collisions
            # between a heading's anchor and the first non-heading block in the
            # same section when the resolver does BY_PATH_INDEX matching.
            anchor = _make_anchor(heading_path, -1, plain_text)
            out.append(Block(
                kind="heading",
                anchor=anchor,
                html=html,
                plain_text=plain_text,
                heading_level=level,
            ))
            # Do NOT increment section_counter for headings

        elif tok_type == "list":
            _process_list(token, heading_path, section_counter, out)

        elif tok_type in _KIND_MAP:
            kind = _KIND_MAP[tok_type]
            if tok_type == "block_code":
                plain_text = token.get("raw", "").rstrip("\n")
            elif tok_type == "thematic_break":
                plain_text = ""
            else:
                plain_text = _extract_plain_text(token).strip()

            html = _render_token_html(token)
            anchor = _make_anchor(heading_path, section_counter[0], plain_text)
            out.append(Block(
                kind=kind,
                anchor=anchor,
                html=html,
                plain_text=plain_text,
                heading_level=None,
            ))
            section_counter[0] += 1

        # All other token types (blank_line already skipped, block_html, etc.)
        # are silently ignored.

    return out


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolve_anchor(anchor: Anchor, blocks: list[Block]) -> ResolveResult:
    """Resolve *anchor* against *blocks*, falling back through four tiers.

    Resolution order (first match wins):

    1. **EXACT** — all four anchor fields match exactly.
    2. **BY_PATH_INDEX** — ``(heading_path, block_index_in_section)`` match;
       text may have changed (heading rename survived because path also changed
       in both, but index within section is the same).
    3. **BY_HASH** — ``text_hash`` matches; heading may have been renamed or
       block may have moved to a different section.
    4. **ORPHAN** — no axis matches; ``block`` is ``None``.
    """
    # Tier 1: exact match on all four fields
    for b in blocks:
        if b.anchor == anchor:
            return ResolveResult(outcome=ResolveOutcome.EXACT, block=b)

    # Tier 2: (heading_path, block_index_in_section) match
    for b in blocks:
        if (b.anchor.heading_path == anchor.heading_path and
                b.anchor.block_index_in_section == anchor.block_index_in_section):
            return ResolveResult(outcome=ResolveOutcome.BY_PATH_INDEX, block=b)

    # Tier 3: text_hash match
    for b in blocks:
        if b.anchor.text_hash == anchor.text_hash:
            return ResolveResult(outcome=ResolveOutcome.BY_HASH, block=b)

    # Tier 4: orphan
    return ResolveResult(outcome=ResolveOutcome.ORPHAN, block=None)
