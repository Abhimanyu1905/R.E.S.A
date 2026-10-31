"""retriever.py – RBAC-filtered vector retrieval for R.E.S.A.

Retrieves document chunks using pgvector cosine similarity, filtered by
the caller's role level (user_level).  Chunks with min_role_level > user_level
are never returned — enforced in the SQL WHERE clause.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import text

from app.db import AsyncSessionLocal
from app.ingest.embedder import embed_query

if TYPE_CHECKING:
    from app.models.document import Document


class Chunk(BaseModel):
    """A single retrieved document chunk with RBAC metadata and similarity score."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    page_number: int | None
    min_role_level: int
    title: str
    score: float


_RETRIEVE_SQL = text("""\
SELECT c.id            AS chunk_id,
       c.document_id,
       c.content,
       c.page_number,
       c.min_role_level,
       d.title,
       1 - (c.embedding <=> CAST(:qvec AS vector)) AS score
  FROM document_chunks c
  JOIN documents d ON c.document_id = d.id
 WHERE c.min_role_level <= :user_level
   AND d.status = 'indexed'
 ORDER BY c.embedding <=> CAST(:qvec AS vector)
 LIMIT :k
""")


async def retrieve(query: str, *, user_level: int, k: int = 5) -> list[Chunk]:
    """Retrieve top-k RBAC-filtered chunks for a query.

    Parameters
    ----------
    query:
        Natural-language query string.  Embedded with the BGE query prefix.
    user_level:
        Required keyword argument.  The caller's role level
        (1=employee, 2=agent, 3=admin).  Chunks whose
        ``min_role_level`` exceeds this value are excluded by the SQL
        WHERE clause.
    k:
        Maximum number of chunks to return (default 5).

    Returns
    -------
    list[Chunk]
        Chunks ordered by descending cosine similarity, RBAC-filtered.
    """
    qvec = embed_query(query)
    qvec_str = "[" + ",".join(str(v) for v in qvec) + "]"

    async with AsyncSessionLocal() as session:
        # Set app.user_level for PostgreSQL Row-Level Security (RLS) enforcement.
        await session.execute(text(f"SET LOCAL app.user_level = {int(user_level)}"))

        # Raise HNSW ef_search for higher recall; scoped to this transaction.
        await session.execute(text("SET LOCAL hnsw.ef_search = 100"))

        result = await session.execute(
            _RETRIEVE_SQL,
            {"qvec": qvec_str, "user_level": user_level, "k": k},
        )
        rows = result.all()

        return [
            Chunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                page_number=row.page_number,
                min_role_level=row.min_role_level,
                title=row.title,
                score=float(row.score),
            )
            for row in rows
        ]


async def update_document_level(*, doc_id: uuid.UUID, new_level: int) -> Document:
    """Update a document's min_role_level and propagate to all its chunks atomically.

    Both the ``documents`` row and every associated ``document_chunks`` row are
    updated within a single transaction so there is never a window where the
    chunk level is out of sync with its parent document.

    Parameters
    ----------
    doc_id:
        UUID of the document to update.
    new_level:
        New min_role_level value (1, 2, or 3).

    Returns
    -------
    Document
        The refreshed ORM document object with the new level.

    Raises
    ------
    ValueError
        If no document exists with the given *doc_id*.
    """
    from app.models.document import Document

    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        if doc is None:
            msg = f"Document {doc_id} not found"
            raise ValueError(msg)

        doc.min_role_level = new_level

        # Propagate level to all chunks in the same transaction
        await session.execute(
            text(
                "UPDATE document_chunks SET min_role_level = :level "
                "WHERE document_id = :doc_id"
            ),
            {"level": new_level, "doc_id": doc_id},
        )

        await session.commit()
        await session.refresh(doc)
        return doc
