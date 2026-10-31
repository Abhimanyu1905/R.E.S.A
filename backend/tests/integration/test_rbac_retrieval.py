"""tests/integration/test_rbac_retrieval.py - RBAC retriever integration tests.

Tests RBAC isolation and chunk level synchronization using real PostgreSQL + pgvector
and the real sentence-transformers embedder.

Verifies:
- Seeding 3 documents at levels 1, 2, 3 with unique markers (MARKER-L1, MARKER-L2, MARKER-L3).
- Employee (user_level=1) never receives chunks containing MARKER-L2 or MARKER-L3,
  even when query text is exactly the marker sentence.
- Agent (user_level=2) gets L1 and L2 but never L3.
- Admin (user_level=3) gets all levels.
- retrieve() without user_level raises TypeError.
- Changing a document's level updates all its chunks in the same transaction.
"""

from __future__ import annotations

import hashlib
import inspect
import sys
from typing import TYPE_CHECKING, Any

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import AsyncSessionLocal, _db_url
from app.ingest.embedder import embed_passages
from app.models.document import Document, DocumentChunk
from app.retrieval.retriever import retrieve, update_document_level

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

MARKER_L1 = "MARKER-L1"
MARKER_L2 = "MARKER-L2"
MARKER_L3 = "MARKER-L3"

TEXT_L1 = (
    "Standard operating employee rules and general guidance. "
    f"Protocol reference {MARKER_L1} applies to all general staff operations."
)
TEXT_L2 = (
    "Tier 2 support agent escalation instructions and dispute thresholds. "
    f"Reference code {MARKER_L2} applies to internal agent investigation records."
)
TEXT_L3 = (
    "Confidential executive board compensation and crisis administration strategy. "
    f"Reference code {MARKER_L3} applies exclusively to board level deliberations."
)


def get_chunk_content(chunk: Any) -> str:
    """Extract content string from a chunk object, dict, or string."""
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, dict):
        return str(chunk.get("content", ""))
    return str(getattr(chunk, "content", ""))


def get_chunk_level(chunk: Any) -> int:
    """Extract min_role_level integer from a chunk object or dict."""
    if isinstance(chunk, dict):
        return int(chunk.get("min_role_level", 0))
    return int(getattr(chunk, "min_role_level", 0))


@pytest.fixture
async def seed_rbac_documents() -> AsyncGenerator[dict[str, Any], None]:
    """Seed three documents at levels 1, 2, and 3 with real embeddings and clean up afterwards."""
    hash_l1 = hashlib.sha256(b"seed_rbac_l1_test_doc").hexdigest()
    hash_l2 = hashlib.sha256(b"seed_rbac_l2_test_doc").hexdigest()
    hash_l3 = hashlib.sha256(b"seed_rbac_l3_test_doc").hexdigest()
    test_hashes = [hash_l1, hash_l2, hash_l3]

    # Require sentence_transformers (installed in Docker test environment)
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        pytest.skip(
            "sentence_transformers not installed in host environment. "
            "Run integration tests inside Docker: "
            "docker exec resa-backend-1 python -m pytest tests/integration/test_rbac_retrieval.py"
        )

    # Pre-clean any leftover documents from aborted runs
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Document).where(Document.content_hash.in_(test_hashes))
        )
        await session.commit()

    # Generate real embeddings via embed_passages
    embeddings = embed_passages([TEXT_L1, TEXT_L2, TEXT_L3])

    async with AsyncSessionLocal() as session:
        doc1 = Document(
            title="Test Document L1 (Employee)",
            doc_type="policy",
            source_filename="test_policy_l1.md",
            content_hash=hash_l1,
            min_role_level=1,
            status="indexed",
        )
        doc2 = Document(
            title="Test Document L2 (Agent)",
            doc_type="policy",
            source_filename="test_policy_l2.md",
            content_hash=hash_l2,
            min_role_level=2,
            status="indexed",
        )
        doc3 = Document(
            title="Test Document L3 (Admin)",
            doc_type="policy",
            source_filename="test_policy_l3.md",
            content_hash=hash_l3,
            min_role_level=3,
            status="indexed",
        )
        session.add_all([doc1, doc2, doc3])
        await session.commit()
        await session.refresh(doc1)
        await session.refresh(doc2)
        await session.refresh(doc3)

        chunk1 = DocumentChunk(
            document_id=doc1.id,
            chunk_index=0,
            content=TEXT_L1,
            page_number=1,
            min_role_level=1,
            embedding=embeddings[0],
        )
        chunk2 = DocumentChunk(
            document_id=doc2.id,
            chunk_index=0,
            content=TEXT_L2,
            page_number=1,
            min_role_level=2,
            embedding=embeddings[1],
        )
        chunk3 = DocumentChunk(
            document_id=doc3.id,
            chunk_index=0,
            content=TEXT_L3,
            page_number=1,
            min_role_level=3,
            embedding=embeddings[2],
        )
        session.add_all([chunk1, chunk2, chunk3])
        await session.commit()

        doc1_id = doc1.id
        doc2_id = doc2.id
        doc3_id = doc3.id

    seeded_data = {
        "doc1_id": doc1_id,
        "doc2_id": doc2_id,
        "doc3_id": doc3_id,
        "texts": {1: TEXT_L1, 2: TEXT_L2, 3: TEXT_L3},
        "hashes": test_hashes,
    }

    try:
        yield seeded_data
    finally:
        async with AsyncSessionLocal() as teardown_session:
            await teardown_session.execute(
                delete(Document).where(Document.content_hash.in_(test_hashes))
            )
            await teardown_session.commit()


async def test_retrieve_without_user_level_raises_type_error() -> None:
    """Assert that calling retrieve() without user_level raises TypeError.

    user_level is a required argument with no default to prevent accidental
    unrestricted queries.
    """
    # Calling without user_level must raise TypeError
    with pytest.raises(TypeError):
        res = retrieve("test query")  # type: ignore[call-arg]
        if inspect.iscoroutine(res):
            await res

    # Calling with no arguments must raise TypeError
    with pytest.raises(TypeError):
        res = retrieve()  # type: ignore[call-arg]
        if inspect.iscoroutine(res):
            await res


async def test_employee_never_receives_l2_or_l3_chunks(
    seed_rbac_documents: dict[str, Any],
) -> None:
    """Assert employee (user_level=1) never receives chunks at level 2 or 3.

    Even when the query text is exactly the marker sentence from an L2 or L3
    document, the SQL WHERE clause must prevent those chunks from being returned.
    """
    # 1. Query for standard L1 content
    results_l1 = await retrieve("Standard employee guidance MARKER-L1", user_level=1)
    assert any(MARKER_L1 in get_chunk_content(c) for c in results_l1)
    assert not any(MARKER_L2 in get_chunk_content(c) for c in results_l1)
    assert not any(MARKER_L3 in get_chunk_content(c) for c in results_l1)
    assert all(get_chunk_level(c) <= 1 for c in results_l1)

    # 2. Query with the EXACT marker sentence of L2
    results_l2_leak_attempt = await retrieve(TEXT_L2, user_level=1)
    assert not any(
        MARKER_L2 in get_chunk_content(c) for c in results_l2_leak_attempt
    ), "LEAK: Employee received L2 chunk when querying exact L2 text!"
    assert not any(
        MARKER_L3 in get_chunk_content(c) for c in results_l2_leak_attempt
    )
    assert all(get_chunk_level(c) <= 1 for c in results_l2_leak_attempt)

    # 3. Query with the EXACT marker sentence of L3
    results_l3_leak_attempt = await retrieve(TEXT_L3, user_level=1)
    assert not any(
        MARKER_L2 in get_chunk_content(c) for c in results_l3_leak_attempt
    )
    assert not any(
        MARKER_L3 in get_chunk_content(c) for c in results_l3_leak_attempt
    ), "LEAK: Employee received L3 chunk when querying exact L3 text!"
    assert all(get_chunk_level(c) <= 1 for c in results_l3_leak_attempt)


async def test_agent_receives_l1_and_l2_but_never_l3(
    seed_rbac_documents: dict[str, Any],
) -> None:
    """Assert agent (user_level=2) gets L1 and L2 chunks but never L3 chunks."""
    # 1. Query for L1 content
    results_l1 = await retrieve("General staff operations MARKER-L1", user_level=2)
    assert any(MARKER_L1 in get_chunk_content(c) for c in results_l1)
    assert not any(MARKER_L3 in get_chunk_content(c) for c in results_l1)
    assert all(get_chunk_level(c) <= 2 for c in results_l1)

    # 2. Query for L2 content
    results_l2 = await retrieve("Support agent escalation MARKER-L2", user_level=2)
    assert any(MARKER_L2 in get_chunk_content(c) for c in results_l2)
    assert not any(MARKER_L3 in get_chunk_content(c) for c in results_l2)
    assert all(get_chunk_level(c) <= 2 for c in results_l2)

    # 3. Query with exact L3 sentence
    results_l3_leak_attempt = await retrieve(TEXT_L3, user_level=2)
    assert not any(
        MARKER_L3 in get_chunk_content(c) for c in results_l3_leak_attempt
    ), "LEAK: Agent received L3 chunk when querying exact L3 text!"
    assert all(get_chunk_level(c) <= 2 for c in results_l3_leak_attempt)


async def test_admin_receives_all_levels(
    seed_rbac_documents: dict[str, Any],
) -> None:
    """Assert admin (user_level=3) can retrieve chunks from all levels (1, 2, and 3)."""
    # 1. Query for L1
    results_l1 = await retrieve("Employee guidance MARKER-L1", user_level=3)
    assert any(MARKER_L1 in get_chunk_content(c) for c in results_l1)

    # 2. Query for L2
    results_l2 = await retrieve("Tier 2 escalation MARKER-L2", user_level=3)
    assert any(MARKER_L2 in get_chunk_content(c) for c in results_l2)

    # 3. Query for L3
    results_l3 = await retrieve("Executive board strategy MARKER-L3", user_level=3)
    assert any(MARKER_L3 in get_chunk_content(c) for c in results_l3)


async def test_change_document_level_updates_chunks_in_same_transaction(
    seed_rbac_documents: dict[str, Any],
) -> None:
    """Assert changing a document's level updates its chunks in the same transaction."""
    doc3_id = seed_rbac_documents["doc3_id"]
    doc1_id = seed_rbac_documents["doc1_id"]

    # Initial state: employee (1) cannot retrieve MARKER-L3
    initial_res = await retrieve(TEXT_L3, user_level=1)
    assert not any(MARKER_L3 in get_chunk_content(c) for c in initial_res)

    # Update Document 3 from level 3 down to level 1
    updated_doc = await update_document_level(doc_id=doc3_id, new_level=1)
    assert updated_doc.min_role_level == 1

    # Verify both Document and its DocumentChunks are updated in the database
    async with AsyncSessionLocal() as session:
        doc_db = await session.get(Document, doc3_id)
        assert doc_db is not None
        assert doc_db.min_role_level == 1

        chunks_stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc3_id)
        chunks_res = await session.execute(chunks_stmt)
        chunks = chunks_res.scalars().all()
        assert len(chunks) > 0
        assert all(c.min_role_level == 1 for c in chunks)

    # Now employee (1) CAN retrieve MARKER-L3 because chunks were updated in the same transaction
    updated_retrieval = await retrieve(TEXT_L3, user_level=1)
    assert any(
        MARKER_L3 in get_chunk_content(c) for c in updated_retrieval
    ), "Expected MARKER-L3 to be retrievable by employee after document was downgraded to level 1"

    # Now upgrade Document 1 from level 1 up to level 3
    await update_document_level(doc_id=doc1_id, new_level=3)

    # Verify employee (1) can no longer retrieve MARKER-L1
    restricted_retrieval = await retrieve(TEXT_L1, user_level=1)
    assert not any(
        MARKER_L1 in get_chunk_content(c) for c in restricted_retrieval
    ), "Expected MARKER-L1 to no longer be accessible to employee after upgrading document to level 3"

    # Admin (3) can still retrieve MARKER-L1
    admin_retrieval = await retrieve(TEXT_L1, user_level=3)
    assert any(MARKER_L1 in get_chunk_content(c) for c in admin_retrieval)


def get_non_owner_db_url() -> str:
    """Derive a connection URL for the non-owner role 'resa_app'."""
    parsed = urlsplit(_db_url)
    host_port = parsed.netloc.split("@")[-1]
    new_netloc = f"resa_app:resa_app_pass@{host_port}"
    return urlunsplit((parsed.scheme, new_netloc, parsed.path, parsed.query, parsed.fragment))


async def test_rls_raw_select_without_where_clause_blocks_higher_level_chunks(
    seed_rbac_documents: dict[str, Any],
) -> None:
    """Assert that Row-Level Security blocks higher-level chunks on a raw SELECT.

    Even when the query has NO WHERE clause filtering on min_role_level or document status,
    a non-owner session with SET LOCAL app.user_level = 1 will NOT see level 2 or 3 chunks.
    """
    non_owner_url = get_non_owner_db_url()
    engine = create_async_engine(non_owner_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    try:
        # 1. Employee level: raw SELECT without WHERE clause must only see L1 chunks
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.user_level = 1"))
            result = await session.execute(
                text("SELECT id, content, min_role_level FROM document_chunks")
            )
            rows = result.all()
            contents = [r.content for r in rows]

            assert any(
                MARKER_L1 in c for c in contents
            ), "Employee should see MARKER-L1 via RLS"
            assert not any(
                MARKER_L2 in c for c in contents
            ), "RLS LEAK: Employee saw MARKER-L2 in raw SELECT!"
            assert not any(
                MARKER_L3 in c for c in contents
            ), "RLS LEAK: Employee saw MARKER-L3 in raw SELECT!"
            assert all(r.min_role_level <= 1 for r in rows)

        # 2. Agent level: raw SELECT without WHERE clause must see L1 and L2, but never L3
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.user_level = 2"))
            result = await session.execute(
                text("SELECT id, content, min_role_level FROM document_chunks")
            )
            rows = result.all()
            contents = [r.content for r in rows]

            assert any(
                MARKER_L1 in c for c in contents
            ), "Agent should see MARKER-L1 via RLS"
            assert any(
                MARKER_L2 in c for c in contents
            ), "Agent should see MARKER-L2 via RLS"
            assert not any(
                MARKER_L3 in c for c in contents
            ), "RLS LEAK: Agent saw MARKER-L3 in raw SELECT!"
            assert all(r.min_role_level <= 2 for r in rows)

        # 3. Admin level: raw SELECT sees all levels
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.user_level = 3"))
            result = await session.execute(
                text("SELECT id, content, min_role_level FROM document_chunks")
            )
            rows = result.all()
            contents = [r.content for r in rows]

            assert any(MARKER_L1 in c for c in contents)
            assert any(MARKER_L2 in c for c in contents)
            assert any(MARKER_L3 in c for c in contents)
    finally:
        await engine.dispose()

