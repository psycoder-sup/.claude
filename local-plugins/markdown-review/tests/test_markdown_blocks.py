"""
Tests for server.markdown_blocks — block parser, anchor builder, and resolver.

Covers FR-09 (CommonMark/GFM rendering, sanitization) and
FR-21 (anchor stability + resolver fallbacks: EXACT → BY_PATH_INDEX → BY_HASH → ORPHAN).
"""

import unittest

from server.markdown_blocks import (
    Block,
    Anchor,
    BlockKind,
    ResolveOutcome,
    ResolveResult,
    parse_blocks,
    anchor_dict,
    resolve_anchor,
)


# ---------------------------------------------------------------------------
# Parser tests — FR-09
# ---------------------------------------------------------------------------

class TestParseHeadings(unittest.TestCase):
    def test_parses_heading_levels(self):
        src = "# H1\n\n## H2\n\n### H3\n\n#### H4\n\n##### H5\n\n###### H6\n"
        blocks = parse_blocks(src)
        heading_blocks = [b for b in blocks if b.kind == "heading"]
        self.assertEqual(len(heading_blocks), 6)
        levels = [b.heading_level for b in heading_blocks]
        self.assertEqual(levels, [1, 2, 3, 4, 5, 6])
        for b in heading_blocks:
            self.assertEqual(b.kind, "heading")

    def test_heading_html_uses_correct_tag(self):
        blocks = parse_blocks("## My Heading\n")
        h = blocks[0]
        self.assertEqual(h.kind, "heading")
        self.assertEqual(h.heading_level, 2)
        self.assertIn("<h2", h.html)
        self.assertIn("My Heading", h.html)


class TestParseParagraph(unittest.TestCase):
    def test_parses_paragraph(self):
        blocks = parse_blocks("Hello world.\n")
        self.assertEqual(len(blocks), 1)
        b = blocks[0]
        self.assertEqual(b.kind, "paragraph")
        self.assertEqual(b.plain_text, "Hello world.")

    def test_paragraph_html_wrapped_in_p(self):
        blocks = parse_blocks("Some text.\n")
        self.assertIn("<p>", blocks[0].html)
        self.assertIn("</p>", blocks[0].html)


class TestParseListItems(unittest.TestCase):
    def test_parses_unordered_list_items(self):
        blocks = parse_blocks("- a\n- b\n")
        list_items = [b for b in blocks if b.kind == "list_item"]
        self.assertEqual(len(list_items), 2)
        texts = [b.plain_text for b in list_items]
        self.assertIn("a", texts)
        self.assertIn("b", texts)

    def test_parses_ordered_list_items(self):
        blocks = parse_blocks("1. one\n2. two\n")
        list_items = [b for b in blocks if b.kind == "list_item"]
        self.assertEqual(len(list_items), 2)
        texts = [b.plain_text for b in list_items]
        self.assertIn("one", texts)
        self.assertIn("two", texts)

    def test_parses_nested_lists(self):
        src = "- outer\n  - inner\n"
        blocks = parse_blocks(src)
        list_items = [b for b in blocks if b.kind == "list_item"]
        # Both outer item and inner item should produce list_item blocks
        self.assertGreaterEqual(len(list_items), 2)
        texts = [b.plain_text for b in list_items]
        self.assertIn("outer", texts)
        self.assertIn("inner", texts)


class TestParseCodeBlock(unittest.TestCase):
    def test_parses_fenced_code_block_with_lang(self):
        src = "```python\nprint('x')\n```\n"
        blocks = parse_blocks(src)
        code_blocks = [b for b in blocks if b.kind == "code_block"]
        self.assertEqual(len(code_blocks), 1)
        b = code_blocks[0]
        self.assertIn("print('x')", b.plain_text)

    def test_fenced_code_html_has_pre_code(self):
        src = "```python\nprint('x')\n```\n"
        blocks = parse_blocks(src)
        b = next(b for b in blocks if b.kind == "code_block")
        self.assertIn("<pre>", b.html)
        self.assertIn("<code", b.html)


class TestParseTable(unittest.TestCase):
    def test_parses_table_gfm(self):
        src = "| a | b |\n|---|---|\n| 1 | 2 |\n"
        blocks = parse_blocks(src)
        tables = [b for b in blocks if b.kind == "table"]
        self.assertEqual(len(tables), 1)
        b = tables[0]
        self.assertIn("<table>", b.html)


class TestParseBlockquote(unittest.TestCase):
    def test_parses_blockquote(self):
        src = "> quoted\n"
        blocks = parse_blocks(src)
        quotes = [b for b in blocks if b.kind == "blockquote"]
        self.assertEqual(len(quotes), 1)
        self.assertIn("quoted", quotes[0].plain_text)

    def test_blockquote_html(self):
        blocks = parse_blocks("> quoted\n")
        b = next(b for b in blocks if b.kind == "blockquote")
        self.assertIn("<blockquote>", b.html)


class TestParseThematicBreak(unittest.TestCase):
    def test_parses_thematic_break(self):
        src = "---\n"
        blocks = parse_blocks(src)
        breaks = [b for b in blocks if b.kind == "thematic_break"]
        self.assertEqual(len(breaks), 1)


class TestInlineFeatures(unittest.TestCase):
    def test_inline_features_render_in_html(self):
        src = "**bold** *em* ~~strike~~ [link](url) ![alt](src.png) `code`\n"
        blocks = parse_blocks(src)
        self.assertEqual(len(blocks), 1)
        html = blocks[0].html
        self.assertIn("<strong>", html)
        self.assertIn("<em>", html)
        # strikethrough renders as <del> or <s>
        self.assertTrue("<del>" in html or "<s>" in html)
        self.assertIn("<a", html)
        self.assertIn("<img", html)
        self.assertIn("<code>", html)


# ---------------------------------------------------------------------------
# Sanitization tests — FR-09
# ---------------------------------------------------------------------------

class TestSanitization(unittest.TestCase):
    def test_script_tags_in_source_are_escaped(self):
        src = "Hello <script>alert(1)</script> world\n"
        blocks = parse_blocks(src)
        self.assertEqual(len(blocks), 1)
        html = blocks[0].html
        # Must NOT contain a literal <script> tag
        self.assertNotIn("<script>", html)
        # Should be escaped
        self.assertIn("&lt;script&gt;", html)


# ---------------------------------------------------------------------------
# Anchor stability tests — FR-21
# ---------------------------------------------------------------------------

class TestAnchorStability(unittest.TestCase):
    def test_anchor_is_deterministic_for_same_text(self):
        src = "Hello world.\n"
        blocks1 = parse_blocks(src)
        blocks2 = parse_blocks(src)
        self.assertEqual(blocks1[0].anchor, blocks2[0].anchor)

    def test_anchor_changes_when_text_changes(self):
        blocks_abc = parse_blocks("abc\n")
        blocks_xyz = parse_blocks("xyz\n")
        self.assertNotEqual(blocks_abc[0].anchor.text_hash, blocks_xyz[0].anchor.text_hash)

    def test_anchor_stable_when_other_blocks_change(self):
        src = "First paragraph.\n\nSecond paragraph.\n"
        blocks_before = parse_blocks(src)
        anchor_first = blocks_before[0].anchor

        src2 = "First paragraph.\n\nModified second paragraph.\n"
        blocks_after = parse_blocks(src2)
        anchor_first_after = blocks_after[0].anchor

        # All four fields must remain identical
        self.assertEqual(anchor_first.heading_path, anchor_first_after.heading_path)
        self.assertEqual(anchor_first.block_index_in_section, anchor_first_after.block_index_in_section)
        self.assertEqual(anchor_first.text_hash, anchor_first_after.text_hash)
        self.assertEqual(anchor_first.preview, anchor_first_after.preview)

    def test_heading_path_includes_ancestor_chain(self):
        """heading_path format: '## Goals > ### Subgoal' (heading marker + text joined by ' > ')"""
        src = "## Goals\n\n### Subgoal\n\npara\n"
        blocks = parse_blocks(src)
        # Find the paragraph block (after the two headings)
        para = next(b for b in blocks if b.kind == "paragraph")
        # Should include both ancestor headings
        self.assertIn("## Goals", para.anchor.heading_path)
        self.assertIn("### Subgoal", para.anchor.heading_path)
        self.assertIn(" > ", para.anchor.heading_path)

    def test_block_index_in_section_resets_per_section(self):
        src = "## Section A\n\nParagraph one.\n\nParagraph two.\n\n## Section B\n\nFirst under B.\n"
        blocks = parse_blocks(src)
        paras = [b for b in blocks if b.kind == "paragraph"]
        # First two paragraphs under Section A: indexes 0 and 1
        under_a = [p for p in paras if "Section A" in p.anchor.heading_path]
        self.assertEqual(len(under_a), 2)
        indexes_a = sorted(p.anchor.block_index_in_section for p in under_a)
        self.assertEqual(indexes_a, [0, 1])

        # First paragraph under Section B: index 0
        under_b = [p for p in paras if "Section B" in p.anchor.heading_path]
        self.assertEqual(len(under_b), 1)
        self.assertEqual(under_b[0].anchor.block_index_in_section, 0)

    def test_block_before_any_heading_has_empty_heading_path(self):
        src = "Leading paragraph.\n\n# First Heading\n\nUnder heading.\n"
        blocks = parse_blocks(src)
        first_para = blocks[0]
        self.assertEqual(first_para.kind, "paragraph")
        self.assertEqual(first_para.anchor.heading_path, "")


# ---------------------------------------------------------------------------
# Resolver tests — FR-21
# ---------------------------------------------------------------------------

class TestResolver(unittest.TestCase):
    def test_resolver_finds_exact_match(self):
        src = "## H\n\nSame text.\n"
        blocks = parse_blocks(src)
        anchor = blocks[1].anchor  # paragraph
        result = resolve_anchor(anchor, blocks)
        self.assertEqual(result.outcome, ResolveOutcome.EXACT)
        self.assertIsNotNone(result.block)
        self.assertEqual(result.block.plain_text, "Same text.")

    def test_resolver_falls_back_to_hash_on_rename(self):
        """Verbatim from plan §4 skeleton."""
        blocks_before = parse_blocks("## Goals\n\nFirst paragraph.\n")
        anchor = blocks_before[1].anchor  # NOTE: blocks_before[0] is the heading, [1] is the paragraph
        blocks_after = parse_blocks("## Aims\n\nFirst paragraph.\n")
        result = resolve_anchor(anchor, blocks_after)
        self.assertEqual(result.outcome, ResolveOutcome.BY_HASH)
        self.assertIsNotNone(result.block)
        self.assertEqual(result.block.plain_text, "First paragraph.")

    def test_resolver_falls_back_to_path_index_on_text_change(self):
        """Same heading_path + same block_index, but text changed → BY_PATH_INDEX."""
        anchor = parse_blocks("## H\n\noriginal\n")[1].anchor
        after = parse_blocks("## H\n\nedited\n")
        r = resolve_anchor(anchor, after)
        self.assertEqual(r.outcome, ResolveOutcome.BY_PATH_INDEX)
        self.assertIsNotNone(r.block)
        self.assertEqual(r.block.plain_text, "edited")

    def test_resolver_returns_orphan_when_no_axis_matches(self):
        """Block that no longer exists in any axis → ORPHAN."""
        # Create an anchor with completely different content + heading
        anchor = parse_blocks("## Gone Section\n\nCompletely unique text xyz987.\n")[1].anchor
        # New document with no matching heading, index, or hash
        after = parse_blocks("## Different\n\nSomething else entirely.\n\nAnother block.\n")
        r = resolve_anchor(anchor, after)
        self.assertEqual(r.outcome, ResolveOutcome.ORPHAN)
        self.assertIsNone(r.block)

    def test_anchor_dict_returns_all_fields(self):
        blocks = parse_blocks("## H\n\nText.\n")
        a = blocks[1].anchor
        d = anchor_dict(a)
        self.assertIn("heading_path", d)
        self.assertIn("block_index_in_section", d)
        self.assertIn("text_hash", d)
        self.assertIn("preview", d)

    def test_resolve_result_has_correct_structure(self):
        blocks = parse_blocks("Paragraph.\n")
        anchor = blocks[0].anchor
        result = resolve_anchor(anchor, blocks)
        self.assertIsInstance(result, ResolveResult)
        self.assertIsNotNone(result.outcome)
        self.assertIsNotNone(result.block)


if __name__ == "__main__":
    unittest.main()
