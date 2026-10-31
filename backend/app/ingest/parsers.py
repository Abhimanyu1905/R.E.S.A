"""
parsers.py – document ingestion parsers for the R.E.S.A Support RAG pipeline.

Public API
----------
extract_pages(path: str | Path) -> list[dict]

Each returned dict has:
  - "page"    : int  (1-based; always 1 for .md / .txt / CSV rows)
  - "text"    : str  (raw extracted text for that page / row)
  - "source"  : str  (the original file path as a string)
  - "doc_type": str  ("pdf" | "markdown" | "text" | "ticket")
"""

import csv
from pathlib import Path
from typing import TypedDict


class PageDict(TypedDict):
    page: int
    text: str
    source: str
    doc_type: str



def extract_pages(path: str | Path) -> list[PageDict]:
    """Return a list of page-dicts from *path*.

    Dispatches to the appropriate sub-parser based on file extension.
    Raises ``ValueError`` for unsupported extensions.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in {".md", ".markdown"}:
        return _extract_markdown(path)
    elif suffix == ".txt":
        return _extract_text(path)
    elif suffix == ".csv":
        return _extract_ticket_csv(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix!r}  (path={path})")


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> list[PageDict]:
    """Extract one dict per PDF page, preserving 1-based page numbers."""
    try:
        import pypdf  # lazy import so the rest of the module works without it
    except ModuleNotFoundError as exc:
        raise ImportError(
            "pypdf is required for PDF parsing.  Install it with: pip install pypdf"
        ) from exc

    pages: list[PageDict] = []
    reader = pypdf.PdfReader(path)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            {
                "page": i,
                "text": text,
                "source": str(path),
                "doc_type": "pdf",
            }
        )
    return pages


# ---------------------------------------------------------------------------
# Markdown / plain-text parsers  (single page each)
# ---------------------------------------------------------------------------

def _extract_markdown(path: Path) -> list[PageDict]:
    text = path.read_text(encoding="utf-8")
    return [{"page": 1, "text": text, "source": str(path), "doc_type": "markdown"}]


def _extract_text(path: Path) -> list[PageDict]:
    text = path.read_text(encoding="utf-8")
    return [{"page": 1, "text": text, "source": str(path), "doc_type": "text"}]


# ---------------------------------------------------------------------------
# Ticket CSV parser
# ---------------------------------------------------------------------------

def _extract_ticket_csv(path: Path) -> list[PageDict]:
    """Each CSV row becomes one page-dict.

    Expected columns (at minimum): ticket_id, subject, problem, resolution.
    The rendered text format is::

        Ticket {ticket_id}: {subject}
        Problem: {problem}
        Resolution: {resolution}

    Extra columns are silently ignored.
    """
    rows: list[PageDict] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=1):
            ticket_id = row.get("ticket_id", f"ROW-{i}")
            subject = row.get("subject", "")
            problem = row.get("problem", "")
            resolution = row.get("resolution", "")

            text = (
                f"Ticket {ticket_id}: {subject}\n"
                f"Problem: {problem}\n"
                f"Resolution: {resolution}"
            )
            rows.append(
                {
                    "page": i,
                    "text": text,
                    "source": str(path),
                    "doc_type": "ticket",
                }
            )
    return rows
