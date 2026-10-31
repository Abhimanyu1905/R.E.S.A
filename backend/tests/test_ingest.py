"""
tests/test_ingest.py - unit tests for the R.E.S.A Support ingest pipeline.

Covers:
  - parsers.extract_pages()  (markdown, txt, CSV)
  - clean.clean_text()
  - chunking.chunk_document()
      - chunk sizes within bounds (<=800 chars)
      - overlap present between consecutive chunks
      - tickets produce exactly 1 chunk per ticket row
      - policy/FAQ chunks carry a "Title > Section:" heading prefix

Run from backend/ with:  pytest tests/test_ingest.py -v
(pytest finds the `app` package through `pythonpath = ["."]` in pyproject.toml.)
"""

from __future__ import annotations

import csv
import textwrap
from typing import TYPE_CHECKING

import pytest

from app.ingest.chunking import (
    RecursiveCharacterTextSplitter,
    chunk_document,
)
from app.ingest.clean import clean_text
from app.ingest.parsers import PageDict, extract_pages

if TYPE_CHECKING:
    from pathlib import Path

# ===========================================================================
# Helpers
# ===========================================================================


def _write_tmp(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _make_ticket_csv(tmp_path: Path, rows: int = 5) -> Path:
    p = tmp_path / "tickets.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "ticket_id",
                "subject",
                "problem",
                "resolution",
                "category",
                "min_role_level",
            ],
        )
        writer.writeheader()
        for i in range(1, rows + 1):
            writer.writerow(
                {
                    "ticket_id": f"T-{1000 + i}",
                    "subject": f"Test subject {i}",
                    "problem": f"The customer reported issue number {i}.",
                    "resolution": f"Agent applied fix {i} per the runbook.",
                    "category": "billing",
                    "min_role_level": "2",
                }
            )
    return p


SAMPLE_MD = textwrap.dedent(
    """\
    ---
    title: Sample Policy
    doc_type: policy
    min_role_level: 1
    ---

    ## Introduction

    This is the introduction section. It explains the scope of this policy.
    All customers must read this before contacting support.

    ## Refund Window

    Refunds are accepted within 30 days of confirmed delivery.
    Items must be unused and in original packaging.
    A restocking fee of 10 % applies to opened electronics.

    ## Contact

    Reach us at support@resa.example for any queries.
"""
)


# ===========================================================================
# parsers.extract_pages()
# ===========================================================================


class TestExtractPages:
    def test_markdown_single_page(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "doc.md", SAMPLE_MD)
        pages = extract_pages(p)
        assert len(pages) == 1
        assert pages[0]["page"] == 1
        assert pages[0]["doc_type"] == "markdown"
        assert "Refund Window" in pages[0]["text"]

    def test_txt_single_page(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "doc.txt", "Hello world.\nLine two.")
        pages = extract_pages(p)
        assert len(pages) == 1
        assert pages[0]["doc_type"] == "text"

    def test_ticket_csv_row_count(self, tmp_path: Path) -> None:
        p = _make_ticket_csv(tmp_path, rows=10)
        pages = extract_pages(p)
        assert len(pages) == 10

    def test_ticket_csv_text_format(self, tmp_path: Path) -> None:
        p = _make_ticket_csv(tmp_path, rows=3)
        pages = extract_pages(p)
        first = pages[0]
        assert first["text"].startswith("Ticket T-1001:")
        assert "Problem:" in first["text"]
        assert "Resolution:" in first["text"]

    def test_ticket_csv_page_numbers(self, tmp_path: Path) -> None:
        p = _make_ticket_csv(tmp_path, rows=5)
        pages = extract_pages(p)
        page_nums = [pg["page"] for pg in pages]
        assert page_nums == list(range(1, 6))

    def test_ticket_csv_doc_type(self, tmp_path: Path) -> None:
        p = _make_ticket_csv(tmp_path, rows=2)
        pages = extract_pages(p)
        assert all(pg["doc_type"] == "ticket" for pg in pages)

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "file.docx", "content")
        with pytest.raises(ValueError, match="Unsupported"):
            extract_pages(p)

    def test_source_field_is_path_string(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "doc.md", SAMPLE_MD)
        pages = extract_pages(p)
        assert pages[0]["source"] == str(p)


# ===========================================================================
# clean.clean_text()
# ===========================================================================


class TestCleanText:
    def test_nfkc_normalisation(self) -> None:
        # Ligature fi -> f + i
        result = clean_text("\ufb01nancial")
        assert result == "financial"

    def test_null_bytes_stripped(self) -> None:
        result = clean_text("hello\x00world")
        assert "\x00" not in result
        assert "hello" in result

    def test_whitespace_collapsed(self) -> None:
        result = clean_text("hello    world\t\tfoo")
        assert "  " not in result
        assert "\t" not in result

    def test_boilerplate_removed_when_majority(self) -> None:
        # "Page footer" appears on 3 of 4 pages (75 % > 50 %)
        footer = "Page footer - R.E.S.A Support"
        pages = [
            f"Content A\n{footer}",
            f"Content B\n{footer}",
            f"Content C\n{footer}",
            "Content D",
        ]
        result = clean_text(pages[0], all_pages=pages)
        assert footer not in result

    def test_boilerplate_kept_when_minority(self) -> None:
        # "Occasional line" appears on 1 of 4 pages (25 % < 50 %)
        line = "Occasional line"
        pages = [
            f"Content A\n{line}",
            "Content B",
            "Content C",
            "Content D",
        ]
        result = clean_text(pages[0], all_pages=pages)
        assert line in result

    def test_single_page_no_boilerplate_removal(self) -> None:
        text = "Only page.\nFooter line."
        result = clean_text(text, all_pages=[text])
        assert "Footer line." in result

    def test_blank_lines_collapsed(self) -> None:
        text = "Para one.\n\n\n\n\nPara two."
        result = clean_text(text)
        assert "\n\n\n" not in result


# ===========================================================================
# chunking.RecursiveCharacterTextSplitter
# ===========================================================================


class TestRecursiveCharacterTextSplitter:
    def test_short_text_is_single_chunk(self) -> None:
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        text = "Short text."
        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_sizes_within_bounds(self) -> None:
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        text = ("A" * 200 + "\n\n") * 20  # 4000+ chars
        chunks = splitter.split_text(text)
        assert chunks, "Expected at least one chunk"
        for chunk in chunks:
            assert len(chunk) <= 800, f"Chunk too long: {len(chunk)}"

    def test_overlap_present(self) -> None:
        """The end of chunk N should share tokens with the start of chunk N+1.

        The splitter preserves overlap at the *piece* level (not character
        level): a word near the tail of chunk 0 should appear near the head
        of chunk 1.
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        words = [f"word{i}" for i in range(200)]
        text = " ".join(words)
        chunks = splitter.split_text(text)
        if len(chunks) < 2:
            pytest.skip("Not enough chunks to test overlap")
        # Extract the last few tokens of chunk 0.
        tail_tokens = set(chunks[0].split()[-4:])
        # At least one of those tokens should appear in chunk 1.
        head_tokens = set(chunks[1].split()[:8])
        assert tail_tokens & head_tokens, (
            f"Expected overlap between consecutive chunks.\n"
            f"Tail of chunk 0: {chunks[0][-50:]!r}\n"
            f"Head of chunk 1: {chunks[1][:50]!r}"
        )

    def test_invalid_overlap_raises(self) -> None:
        with pytest.raises(ValueError):
            RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=100)


# ===========================================================================
# chunking.chunk_document()
# ===========================================================================


class TestChunkDocument:
    # -----------------------------------------------------------------------
    # Ticket chunks
    # -----------------------------------------------------------------------

    def test_ticket_one_chunk_per_row(self, tmp_path: Path) -> None:
        csv_path = _make_ticket_csv(tmp_path, rows=10)
        pages = extract_pages(csv_path)
        chunks = chunk_document(pages, doc_type="ticket")
        assert len(chunks) == 10, "Must be exactly 1 chunk per ticket row"

    def test_ticket_chunk_text_unchanged(self, tmp_path: Path) -> None:
        csv_path = _make_ticket_csv(tmp_path, rows=3)
        pages = extract_pages(csv_path)
        chunks = chunk_document(pages, doc_type="ticket")
        # Each chunk text should exactly match the parsed page text.
        for chunk, page in zip(chunks, pages, strict=True):
            assert chunk["text"] == page["text"]

    def test_ticket_chunk_index_sequential(self, tmp_path: Path) -> None:
        csv_path = _make_ticket_csv(tmp_path, rows=5)
        pages = extract_pages(csv_path)
        chunks = chunk_document(pages, doc_type="ticket")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(5))

    # -----------------------------------------------------------------------
    # Policy / FAQ chunks - heading prefix
    # -----------------------------------------------------------------------

    def test_policy_heading_prefix_present(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "policy.md", SAMPLE_MD)
        pages = extract_pages(p)
        chunks = chunk_document(pages, doc_type="markdown")
        assert chunks, "Expected at least one chunk"
        prefixed = [c for c in chunks if "Sample Policy" in c["text"]]
        assert prefixed, "At least one chunk should contain the document title"

    def test_policy_section_label_in_chunk(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "policy.md", SAMPLE_MD)
        pages = extract_pages(p)
        chunks = chunk_document(pages, doc_type="markdown")
        # At least one chunk should carry a ">" section separator.
        prefixed = [c for c in chunks if " > " in c["text"]]
        assert prefixed, "Expected 'Title > Section:' prefix in at least one chunk"

    def test_policy_chunk_sizes_within_bounds(self, tmp_path: Path) -> None:
        # Repeat the sample doc many times so it gets split.
        big_doc = SAMPLE_MD + ("\n## Extra Section\n\n" + "Word " * 200 + "\n") * 10
        p = _write_tmp(tmp_path, "big_policy.md", big_doc)
        pages = extract_pages(p)
        chunks = chunk_document(pages, doc_type="markdown")
        max_len = 800 + len("Sample Policy > Extra Section: ")
        for chunk in chunks:
            assert len(chunk["text"]) <= max_len, (
                f"Chunk exceeds size bound: {len(chunk['text'])}"
            )

    # -----------------------------------------------------------------------
    # PDF chunks (mocked - no real PDF needed)
    # -----------------------------------------------------------------------

    def test_pdf_chunks_within_bounds(self) -> None:
        """Feed fake PDF page-dicts and check chunking respects size limit."""
        # Simulate 5 pages of ~300 chars each.
        fake_pages: list[PageDict] = [
            {
                "page": i,
                "text": f"Page {i}: " + "Content word. " * 25,
                "source": "fake.pdf",
                "doc_type": "pdf",
            }
            for i in range(1, 6)
        ]

        chunks = chunk_document(fake_pages, doc_type="pdf")
        assert chunks, "Expected chunks from PDF"
        for chunk in chunks:
            assert len(chunk["text"]) <= 800

    # -----------------------------------------------------------------------
    # Edge cases
    # -----------------------------------------------------------------------

    def test_empty_pages_returns_empty(self) -> None:
        chunks = chunk_document([], doc_type="markdown")
        assert chunks == []

    def test_chunk_fields_present(self, tmp_path: Path) -> None:
        p = _write_tmp(tmp_path, "doc.md", SAMPLE_MD)
        pages = extract_pages(p)
        chunks = chunk_document(pages, doc_type="markdown")
        for chunk in chunks:
            assert "text" in chunk
            assert "source" in chunk
            assert "doc_type" in chunk
            assert "chunk_index" in chunk
            assert "page" in chunk
