"""
clean.py – text normalisation for the R.E.S.A Support RAG pipeline.

Public API
----------
clean_text(text: str, all_pages: list[str] | None = None) -> str

Steps applied (in order):
  1. NFKC Unicode normalisation.
  2. Strip null bytes.
  3. Collapse runs of whitespace (spaces/tabs) to a single space per line.
  4. Strip leading/trailing whitespace from every line.
  5. Collapse 3+ consecutive blank lines down to two.
  6. Remove lines that appear in more than 50 % of pages (boilerplate removal).
     Only performed when *all_pages* is provided and has >1 page.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def clean_text(text: str, all_pages: list[str] | None = None) -> str:
    """Normalise *text* and optionally strip boilerplate repeated across pages.

    Parameters
    ----------
    text:
        The raw text of a single page / document.
    all_pages:
        A list of raw page texts from the *same* document.  When supplied the
        function computes a set of "boilerplate" lines – lines that appear on
        more than 50 % of pages – and removes them from *text*.
        Pass ``None`` (or omit) to skip boilerplate removal.

    Returns
    -------
    str
        The cleaned text.
    """
    text = _nfkc_normalize(text)
    text = _strip_null_bytes(text)
    text = _collapse_whitespace(text)
    if all_pages is not None and len(all_pages) > 1:
        boilerplate = _find_boilerplate_lines(all_pages)
        text = _remove_boilerplate(text, boilerplate)
    text = _collapse_blank_lines(text)
    return text.strip()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _nfkc_normalize(text: str) -> str:
    """Apply Unicode NFKC normalisation."""
    return unicodedata.normalize("NFKC", text)


def _strip_null_bytes(text: str) -> str:
    """Remove all null bytes (U+0000)."""
    return text.replace("\x00", "")


def _collapse_whitespace(text: str) -> str:
    """Collapse horizontal whitespace within each line; trim line edges."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # Collapse tabs and multiple spaces to a single space.
        line = re.sub(r"[ \t]+", " ", line)
        cleaned.append(line.strip())
    return "\n".join(cleaned)


def _collapse_blank_lines(text: str) -> str:
    """Reduce runs of 3+ consecutive blank lines to exactly two blank lines."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _find_boilerplate_lines(all_pages: list[str]) -> frozenset[str]:
    """Return the set of non-empty lines that appear on >50 % of pages."""
    total = len(all_pages)
    threshold = total / 2  # strictly more than 50 %

    # Count how many pages each (stripped) non-empty line appears on.
    line_page_count: Counter[str] = Counter()
    for page_text in all_pages:
        # Use a set so we count each unique line only once per page.
        unique_lines = {
            line.strip()
            for line in page_text.splitlines()
            if line.strip()
        }
        line_page_count.update(unique_lines)

    return frozenset(
        line for line, count in line_page_count.items() if count > threshold
    )


def _remove_boilerplate(text: str, boilerplate: frozenset[str]) -> str:
    """Remove lines whose stripped content is in *boilerplate*."""
    if not boilerplate:
        return text
    kept = [
        line
        for line in text.splitlines()
        if line.strip() not in boilerplate
    ]
    return "\n".join(kept)
