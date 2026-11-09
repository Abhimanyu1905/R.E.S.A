"""
chunking.py – text chunking for the R.E.S.A Support RAG pipeline.

Public API
----------


Strategy
--------
* **Policies / FAQs** (doc_type in {"markdown", "text"}):
    1. Split the document at Markdown heading boundaries first.
    2. Run RecursiveCharacterTextSplitter on each section.
    3. Prefix every chunk with  ``"<Title> > <Section>: "``  so that the
       heading context travels with the chunk into the vector store.

* **Tickets** (doc_type == "ticket"):
    One chunk per ticket row – no further splitting.

* **PDF** (doc_type == "pdf"):
    Concatenate all page texts, then run RecursiveCharacterTextSplitter
    (no heading prefix).

RecursiveCharacterTextSplitter parameters (matches spec):
    chunk_size    = 800
    chunk_overlap = 120
    separators    = ["\n\n", "\n", ". ", " "]

Each returned chunk dict has:
    - "text"        : str   – the chunk text
    - "source"      : str   – originating file path
    - "doc_type"    : str   – same as input doc_type
    - "chunk_index" : int   – 0-based index within the document
    - "page"        : int   – page number of the *first* page this chunk came from
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .parsers import PageDict

# ---------------------------------------------------------------------------
# RecursiveCharacterTextSplitter  (implemented natively – no langchain needed)
# ---------------------------------------------------------------------------

class RecursiveCharacterTextSplitter:
    """Minimal, spec-compatible implementation of the LangChain splitter.

    Splits text hierarchically through *separators*, producing chunks of at
    most *chunk_size* characters with *chunk_overlap* characters of overlap
    between consecutive chunks.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators if separators is not None else ["\n\n", "\n", ". ", " "]

    # ------------------------------------------------------------------
    # Public method
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> list[str]:
        """Return a list of chunks derived from *text*."""
        return self._split_text(text, self.separators)

    # ------------------------------------------------------------------
    # Internal recursive logic
    # ------------------------------------------------------------------

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Find the first separator that actually occurs in the text.
        chosen_sep = separators[-1]  # fallback: character-level
        remaining_seps: list[str] = []
        for i, sep in enumerate(separators):
            if sep in text:
                chosen_sep = sep
                remaining_seps = separators[i + 1 :]
                break

        parts = text.split(chosen_sep)
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(chosen_sep)
            if current_len + part_len > self.chunk_size and current_parts:
                # Flush
                chunk_text = chosen_sep.join(current_parts)
                if len(chunk_text) > self.chunk_size and remaining_seps:
                    chunks.extend(self._split_text(chunk_text, remaining_seps))
                else:
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                # Overlap: keep the last N characters worth of parts
                current_parts, current_len = self._trim_to_overlap(
                    current_parts, chosen_sep
                )
            current_parts.append(part)
            current_len += part_len

        # Flush remainder
        if current_parts:
            chunk_text = chosen_sep.join(current_parts)
            if len(chunk_text) > self.chunk_size and remaining_seps:
                chunks.extend(self._split_text(chunk_text, remaining_seps))
            else:
                if chunk_text.strip():
                    chunks.append(chunk_text)

        return chunks

    def _trim_to_overlap(
        self, parts: list[str], sep: str
    ) -> tuple[list[str], int]:
        """Return a suffix of *parts* whose joined length <= chunk_overlap."""
        kept: list[str] = []
        length = 0
        for part in reversed(parts):
            part_len = len(part) + len(sep)
            if length + part_len > self.chunk_overlap:
                break
            kept.insert(0, part)
            length += part_len
        return kept, length


# ---------------------------------------------------------------------------
# Module-level splitter instance (shared, re-entrant)
# ---------------------------------------------------------------------------

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " "],
)

# Regex that matches any ATX Markdown heading  (# … ######)
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def chunk_document(
    pages: list[PageDict],
    doc_type: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict[str, Any]]:
    """Chunk a parsed document into RAG-ready pieces.

    Parameters
    ----------
    pages:
        Output of ``parsers.extract_pages()`` – a list of page-dicts.
    doc_type:
        The canonical document type string: "markdown", "text", "pdf",
        or "ticket".
    chunk_size:
        Optional chunk size override in characters.
    chunk_overlap:
        Optional chunk overlap override in characters.

    Returns
    -------
    list[dict]
        A list of chunk dicts (see module docstring for field definitions).
    """
    if not pages:
        return []

    source = pages[0]["source"]
    first_page = pages[0]["page"]

    splitter = _SPLITTER
    if chunk_size is not None or chunk_overlap is not None:
        cs = chunk_size if chunk_size is not None else CHUNK_SIZE
        co = chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cs,
            chunk_overlap=co,
            separators=["\n\n", "\n", ". ", " "],
        )

    if doc_type == "ticket":
        return _chunk_tickets(pages)
    elif doc_type in {"markdown", "text", "policy", "faq"}:
        full_text = "\n\n".join(p["text"] for p in pages)
        return _chunk_policy_or_faq(
            full_text, source, doc_type, first_page, splitter=splitter
        )
    else:
        # PDF and anything else: concatenate pages, split without heading prefix.
        full_text = "\n\n".join(p["text"] for p in pages)
        raw_chunks = splitter.split_text(full_text)
        return [
            {
                "text": chunk,
                "source": source,
                "doc_type": doc_type,
                "chunk_index": i,
                "page": first_page,
            }
            for i, chunk in enumerate(raw_chunks)
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_title_from_yaml(text: str) -> str:
    """Pull the ``title:`` value out of a YAML front-matter block, if present."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return ""
    front_matter = match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", front_matter, re.MULTILINE)
    return title_match.group(1).strip() if title_match else ""


def _strip_yaml_front_matter(text: str) -> str:
    """Remove YAML front-matter block from the beginning of *text*."""
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Split *text* into (heading_label, section_body) pairs.

    The first entry may have an empty heading_label if there is content
    before the first heading.
    """
    positions = [m.start() for m in _HEADING_RE.finditer(text)]

    if not positions:
        return [("", text)]

    sections: list[tuple[str, str]] = []

    # Content before the first heading
    if positions[0] > 0:
        sections.append(("", text[: positions[0]].strip()))

    for idx, start in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
        section = text[start:end]
        # First line is the heading itself.
        lines = section.split("\n", 1)
        heading_line = _HEADING_RE.sub("", lines[0]).strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        sections.append((heading_line, body))

    return sections


def _chunk_policy_or_faq(
    full_text: str,
    source: str,
    doc_type: str,
    first_page: int,
    splitter: RecursiveCharacterTextSplitter | None = None,
) -> list[dict[str, Any]]:
    """Split a policy/FAQ document by heading, then by the text splitter.

    Every chunk is prefixed with  ``"<Title> > <Section>: "``.
    """
    if splitter is None:
        splitter = _SPLITTER

    title = _extract_title_from_yaml(full_text)
    body = _strip_yaml_front_matter(full_text)
    sections = _split_by_headings(body)

    chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for heading, content in sections:
        if not content.strip():
            continue

        # Build the prefix string.
        if title and heading:
            prefix = f"{title} > {heading}: "
        elif title:
            prefix = f"{title}: "
        elif heading:
            prefix = f"{heading}: "
        else:
            prefix = ""

        raw_chunks = splitter.split_text(content)
        for raw in raw_chunks:
            chunk_text = prefix + raw if prefix else raw
            chunks.append(
                {
                    "text": chunk_text,
                    "source": source,
                    "doc_type": doc_type,
                    "chunk_index": chunk_index,
                    "page": first_page,
                }
            )
            chunk_index += 1

    return chunks


def _chunk_tickets(pages: list[PageDict]) -> list[dict[str, Any]]:
    """One chunk per ticket – no further splitting."""
    return [
        {
            "text": p["text"],
            "source": p["source"],
            "doc_type": p["doc_type"],
            "chunk_index": i,
            "page": p["page"],
        }
        for i, p in enumerate(pages)
    ]
