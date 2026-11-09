"""pipeline.py – Document ingestion pipeline.

Steps for ingest_file(path, doc_type, min_role_level):
1. sha256 the file; if content_hash exists, skip and report duplicate.
2. insert documents row with status='pending'.
3. extract, clean, chunk, embed.
4. in ONE transaction delete old chunks, insert new chunks with
   min_role_level copied from the document, set status='indexed'.
5. on any exception set status='failed' and store the error.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import delete, select

from app.db import AsyncSessionLocal
from app.ingest.chunking import _extract_title_from_yaml, chunk_document
from app.ingest.clean import clean_text
from app.ingest.embedder import embed_passages
from app.ingest.parsers import PageDict, extract_pages
from app.models.document import Document, DocumentChunk

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# In-memory registry to store error messages for failed ingestions
INGEST_ERRORS: dict[str, str] = {}


def compute_sha256(path: Path) -> str:
    """Compute sha256 hex digest of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


async def ingest_file(
    path: str | Path,
    doc_type: str,
    min_role_level: int = 1,
    title: str | None = None,
    session: AsyncSession | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> tuple[Document, bool]:
    """Ingest a single document file into PostgreSQL / pgvector.

    Parameters
    ----------
    path:
        File path to ingest.
    doc_type:
        Canonical doc_type: 'policy', 'faq', or 'ticket'.
    min_role_level:
        Required role level (1=employee, 2=agent, 3=admin).
    title:
        Optional document title. If not given, extracted from YAML front-matter
        or derived from filename.
    session:
        Optional active AsyncSession. If None, a session is created from AsyncSessionLocal.
    chunk_size:
        Optional chunk size override in characters.
    chunk_overlap:
        Optional chunk overlap override in characters.

    Returns
    -------
    tuple[Document, bool]:
        (document, is_new) where is_new is True if newly indexed, False if duplicate.
    """
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    if session is None:
        async with AsyncSessionLocal() as sess:
            return await _ingest_file_session(
                sess, file_path, doc_type, min_role_level, title, chunk_size, chunk_overlap
            )
    return await _ingest_file_session(
        session, file_path, doc_type, min_role_level, title, chunk_size, chunk_overlap
    )


async def _ingest_file_session(
    session: AsyncSession,
    path: Path,
    doc_type: str,
    min_role_level: int,
    title: str | None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> tuple[Document, bool]:
    # 1. sha256 the file; if content_hash exists, skip and report duplicate.
    content_hash = compute_sha256(path)
    stmt = select(Document).where(Document.content_hash == content_hash)
    result = await session.execute(stmt)
    existing = result.scalars().first()
    if existing is not None:
        logger.info(
            "Duplicate file skipped: %s (hash=%s, id=%s)",
            path.name,
            content_hash,
            existing.id,
        )
        return existing, False

    # Derive title if not provided
    doc_title = title
    if not doc_title:
        try:
            sample_head = path.read_text(encoding="utf-8", errors="ignore")[:2048]
            doc_title = _extract_title_from_yaml(sample_head)
        except Exception:
            pass
    if not doc_title:
        doc_title = path.stem.replace("_", " ").title()

    # 2. insert documents row with status='pending'.
    doc = Document(
        title=doc_title,
        doc_type=doc_type,
        source_filename=path.name,
        content_hash=content_hash,
        min_role_level=min_role_level,
        status="pending",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    try:
        # 3. extract, clean, chunk, embed.
        raw_pages = extract_pages(path)
        all_texts = [p["text"] for p in raw_pages]
        cleaned_pages: list[PageDict] = [
            {
                "page": p["page"],
                "text": clean_text(p["text"], all_pages=all_texts),
                "source": p["source"],
                "doc_type": p["doc_type"],
            }
            for p in raw_pages
        ]

        chunks = chunk_document(
            cleaned_pages,
            doc_type=doc_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunk_texts = [c["text"] for c in chunks]
        embeddings = embed_passages(chunk_texts) if chunk_texts else []

        # 4. in ONE transaction delete old chunks, insert new chunks with
        #    min_role_level copied from the document, set status='indexed'.
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )

        for idx, (chunk_dict, emb) in enumerate(zip(chunks, embeddings, strict=True)):
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk_dict.get("chunk_index", idx),
                content=chunk_dict["text"],
                page_number=chunk_dict.get("page"),
                min_role_level=doc.min_role_level,
                embedding=emb,
            )
            session.add(chunk_obj)

        doc.status = "indexed"
        await session.commit()
        await session.refresh(doc)
        logger.info(
            "Successfully indexed %s as '%s' (%d chunks)",
            path.name,
            doc.doc_type,
            len(chunks),
        )
        return doc, True

    except Exception as exc:
        # 5. on any exception set status='failed' and store the error.
        await session.rollback()
        error_msg = f"{type(exc).__name__}: {exc}"
        INGEST_ERRORS[str(doc.id)] = error_msg
        logger.error("Failed ingesting %s: %s", path.name, error_msg, exc_info=True)
        doc.status = "failed"
        session.add(doc)
        await session.commit()
        raise


async def reindex_document(
    doc_id: uuid.UUID,
    source_path: Path,
    doc_type: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    session: AsyncSession | None = None,
) -> int:
    """Re-chunk and re-embed an existing document from source file in ONE transaction.

    Keeps the document id, title and min_role_level unchanged and sets status 'indexed'.
    Returns the number of newly inserted chunks.
    """
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Extract, clean, chunk, embed
    raw_pages = extract_pages(source_path)
    all_texts = [p["text"] for p in raw_pages]
    cleaned_pages: list[PageDict] = [
        {
            "page": p["page"],
            "text": clean_text(p["text"], all_pages=all_texts),
            "source": p["source"],
            "doc_type": p["doc_type"],
        }
        for p in raw_pages
    ]

    chunks = chunk_document(
        cleaned_pages,
        doc_type=doc_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunk_texts = [c["text"] for c in chunks]
    embeddings = embed_passages(chunk_texts) if chunk_texts else []
    content_hash = compute_sha256(source_path)

    async def _execute(sess: AsyncSession) -> int:
        db_doc = await sess.get(Document, doc_id)
        if db_doc is None:
            raise ValueError(f"Document with id {doc_id} not found in database")

        min_role_level = db_doc.min_role_level

        # Delete existing chunks for this document
        await sess.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        )

        # Insert new chunks with min_role_level copied from doc
        for idx, (chunk_dict, emb) in enumerate(zip(chunks, embeddings, strict=True)):
            chunk_obj = DocumentChunk(
                document_id=doc_id,
                chunk_index=chunk_dict.get("chunk_index", idx),
                content=chunk_dict["text"],
                page_number=chunk_dict.get("page"),
                min_role_level=min_role_level,
                embedding=emb,
            )
            sess.add(chunk_obj)

        # Keep document id, title and min_role_level unchanged and set status 'indexed'
        db_doc.status = "indexed"
        db_doc.content_hash = content_hash
        await sess.commit()
        await sess.refresh(db_doc)
        logger.info(
            "Successfully reindexed %s as '%s' (%d chunks)",
            source_path.name,
            db_doc.doc_type,
            len(chunks),
        )
        return len(chunks)

    if session is None:
        async with AsyncSessionLocal() as sess:
            return await _execute(sess)
    else:
        return await _execute(session)

