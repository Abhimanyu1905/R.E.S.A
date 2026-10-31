"""inspect_search.py – Test vector retrieval quality against pgvector.

Usage:
    python scripts/inspect_search.py "What is the refund window for online purchases?"
    python scripts/inspect_search.py --top-k 5 "How do I troubleshoot softphone WebRTC errors?"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure backend/ (or /app in container) is in sys.path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if backend_dir.is_dir() and str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if (repo_root / "app").is_dir() and str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from app.db import AsyncSessionLocal
from app.ingest.embedder import embed_query
from app.models.document import Document, DocumentChunk
from sqlalchemy import select


async def inspect_search(query: str, top_k: int = 5) -> None:
    """Embed query, execute cosine similarity search, and display top chunks."""
    print("\n" + "=" * 70)
    print(f" Query: {query}")
    print("=" * 70)

    # 1. Embed query with BGE query prefix
    query_vector = embed_query(query)

    # 2. Plain cosine similarity search (1 - cosine_distance)
    async with AsyncSessionLocal() as session:
        # Distance calculation via pgvector
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)
        similarity_expr = (1.0 - distance_expr).label("score")

        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.chunk_index,
                DocumentChunk.page_number,
                DocumentChunk.min_role_level,
                DocumentChunk.content,
                Document.title.label("doc_title"),
                Document.doc_type.label("doc_type"),
                similarity_expr,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            print("\nNo chunks found in database. Have you run the ingestion pipeline yet?")
            print("Try running: python -m app.ingest.cli --manifest corpus/manifest.csv")
            return

        print(f"\nTop {len(rows)} Chunks by Cosine Similarity (No RBAC filter):\n")
        for rank, row in enumerate(rows, start=1):
            score = row.score
            title = row.doc_title
            doc_type = row.doc_type
            min_role = row.min_role_level
            chunk_idx = row.chunk_index
            page = row.page_number
            content = row.content.strip()

            print(f"[{rank}] Score: {score:.4f} | Role Level: {min_role} | Type: {doc_type}")
            print(f"    Document: {title} (Chunk #{chunk_idx}, Page: {page})")
            print("    " + "-" * 66)
            # Indent text snippet for clean readability
            snippet = "\n".join(f"    {line}" for line in content.splitlines()[:10])
            print(snippet)
            if len(content.splitlines()) > 10:
                print("    ... (truncated)")
            print()
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect cosine search results on pgvector chunks")
    parser.add_argument(
        "query",
        nargs="*",
        help="Question or query string to search for",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to return (default: 5)",
    )
    args = parser.parse_args()

    query_str = " ".join(args.query).strip()
    if not query_str:
        try:
            query_str = input("Enter search query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return

    if not query_str:
        print("Error: Empty query provided.")
        sys.exit(1)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inspect_search(query_str, top_k=args.top_k))


if __name__ == "__main__":
    main()
