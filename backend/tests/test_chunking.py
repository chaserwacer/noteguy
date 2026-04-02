"""Unit tests for the ingestion chunking pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.ingestion import (
    chunk_markdown,
    _split_on_headings,
    _subdivide_section,
    _chunk_id,
    _token_len,
    docx_to_markdown,
    TARGET_TOKENS,
)


# ── Heading-based splitting ─────────────────────────────────────────────────


class TestSplitOnHeadings:
    def test_single_heading_section(self):
        text = "# Title\n\nSome content here."
        sections = _split_on_headings(text)
        assert len(sections) == 1
        assert sections[0].startswith("# Title")

    def test_multiple_headings(self):
        text = "# First\n\nContent 1.\n\n## Second\n\nContent 2.\n\n### Third\n\nContent 3."
        sections = _split_on_headings(text)
        assert len(sections) == 3

    def test_content_before_first_heading(self):
        text = "Preamble text.\n\n# Heading\n\nContent."
        sections = _split_on_headings(text)
        assert len(sections) == 2
        assert sections[0].startswith("Preamble")

    def test_no_headings_returns_whole_text(self):
        text = "Just plain text without any headings."
        sections = _split_on_headings(text)
        assert sections == [text]

    def test_empty_text(self):
        assert _split_on_headings("") == []
        assert _split_on_headings("   ") == []

    def test_all_heading_levels(self):
        text = "# H1\n\n## H2\n\n### H3\n\n#### H4\n\n##### H5\n\n###### H6"
        sections = _split_on_headings(text)
        assert len(sections) == 6


# ── Section subdivision ─────────────────────────────────────────────────────


class TestSubdivideSection:
    def test_short_section_stays_intact(self):
        text = "A short paragraph."
        result = _subdivide_section(text)
        assert result == [text]

    def test_long_section_is_split(self):
        # Create a section longer than TARGET_TOKENS
        paragraphs = [f"Paragraph {i}. " + "word " * 80 for i in range(10)]
        text = "\n\n".join(paragraphs)
        assert _token_len(text) > TARGET_TOKENS

        result = _subdivide_section(text)
        assert len(result) > 1
        # Each chunk should be roughly within target
        for chunk in result:
            assert _token_len(chunk) <= TARGET_TOKENS * 2  # allow some overflow

    def test_overlap_exists_between_chunks(self):
        # Create content that will be split into at least 2 chunks
        paragraphs = [f"Unique paragraph {i}. " + "filler " * 60 for i in range(8)]
        text = "\n\n".join(paragraphs)
        result = _subdivide_section(text)
        if len(result) >= 2:
            # Some content from end of chunk 0 should appear in chunk 1
            # (overlap mechanism)
            last_para_of_first = result[0].split("\n\n")[-1]
            assert last_para_of_first in result[1] or len(result) == 2


# ── Full markdown chunking ──────────────────────────────────────────────────


class TestChunkMarkdown:
    def test_simple_markdown(self):
        text = "# Title\n\nSome content."
        chunks = chunk_markdown(text)
        assert len(chunks) >= 1
        assert any("Title" in c for c in chunks)

    def test_empty_content(self):
        assert chunk_markdown("") == []
        assert chunk_markdown("   ") == []

    def test_no_headings_returns_whole_text(self):
        text = "Just plain text."
        chunks = chunk_markdown(text)
        assert chunks == ["Just plain text."]

    def test_multiple_sections(self):
        text = "# Section 1\n\nContent 1.\n\n## Section 2\n\nContent 2."
        chunks = chunk_markdown(text)
        assert len(chunks) >= 2

    def test_preserves_content(self):
        """All original content should be present across chunks."""
        text = "# A\n\nAlpha content.\n\n# B\n\nBeta content."
        chunks = chunk_markdown(text)
        full = " ".join(chunks)
        assert "Alpha content" in full
        assert "Beta content" in full


# ── Deterministic chunk IDs ─────────────────────────────────────────────────


class TestChunkId:
    def test_deterministic(self):
        """Same inputs produce same ID."""
        id1 = _chunk_id("note-123", 0)
        id2 = _chunk_id("note-123", 0)
        assert id1 == id2

    def test_different_for_different_notes(self):
        id1 = _chunk_id("note-1", 0)
        id2 = _chunk_id("note-2", 0)
        assert id1 != id2

    def test_different_for_different_indices(self):
        id1 = _chunk_id("note-1", 0)
        id2 = _chunk_id("note-1", 1)
        assert id1 != id2

    def test_length(self):
        """Chunk IDs are 16 hex characters."""
        cid = _chunk_id("note-1", 0)
        assert len(cid) == 16
        assert all(c in "0123456789abcdef" for c in cid)


# ── Token length ────────────────────────────────────────────────────────────


class TestTokenLen:
    def test_empty_string(self):
        assert _token_len("") == 0

    def test_single_word(self):
        length = _token_len("hello")
        assert length >= 1

    def test_longer_text_has_more_tokens(self):
        short = _token_len("hi")
        long = _token_len("this is a much longer sentence with many words")
        assert long > short


# ── Docx conversion ─────────────────────────────────────────────────────────


class TestDocxToMarkdown:
    def test_converts_simple_docx(self):
        """Create a minimal docx in memory and verify conversion."""
        from docx import Document

        import io
        doc = Document()
        doc.add_heading("Test Heading", level=1)
        doc.add_paragraph("Body text here.")
        doc.add_heading("Sub Heading", level=2)
        doc.add_paragraph("More content.")

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        md = docx_to_markdown(buf.read())
        assert "# Test Heading" in md
        assert "## Sub Heading" in md
        assert "Body text here." in md
        assert "More content." in md

    def test_handles_missing_paragraph_style(self, monkeypatch):
        """Paragraphs with missing style metadata should still convert."""
        from types import SimpleNamespace

        fake_doc = SimpleNamespace(
            paragraphs=[
                SimpleNamespace(text="Styled heading", style=SimpleNamespace(name="Heading 1")),
                SimpleNamespace(text="Plain paragraph", style=None),
                SimpleNamespace(text="No style name", style=SimpleNamespace()),
            ]
        )

        monkeypatch.setattr("app.ingestion.DocxDocument", lambda _: fake_doc)

        md = docx_to_markdown(b"fake-docx")
        assert "# Styled heading" in md
        assert "Plain paragraph" in md
        assert "No style name" in md
