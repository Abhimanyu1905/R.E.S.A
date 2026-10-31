"""cli.py – CLI command to bulk-ingest documents from a manifest.

Usage:
    python -m app.ingest.cli --manifest corpus/manifest.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.db import AsyncSessionLocal
from app.ingest.pipeline import ingest_file
from app.models.document import Document, DocumentChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_cli")


async def run_ingest(manifest_path: Path, tickets_path: Path | None = None) -> None:
    """Ingest documents from manifest and tickets, then print counts."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest_dir = manifest_path.parent
    total_docs = 0
    new_docs = 0
    duplicate_docs = 0
    failed_docs = 0

    # 1. Ingest manifest files
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row["filename"]
            title = row.get("title")
            doc_type = row.get("doc_type", "policy")
            min_role = int(row.get("min_role_level", "1"))
            target_path = manifest_dir / filename

            if not target_path.is_file():
                logger.warning("Manifest referenced missing file: %s", target_path)
                continue

            total_docs += 1
            try:
                doc, is_new = await ingest_file(
                    path=target_path,
                    doc_type=doc_type,
                    min_role_level=min_role,
                    title=title,
                )
                if is_new:
                    new_docs += 1
                else:
                    duplicate_docs += 1
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", filename, exc)
                failed_docs += 1

    # 2. Ingest tickets if present
    if tickets_path is None:
        default_tickets = manifest_dir / "tickets.csv"
        if default_tickets.is_file():
            tickets_path = default_tickets

    if tickets_path and tickets_path.is_file():
        total_docs += 1
        try:
            doc, is_new = await ingest_file(
                path=tickets_path,
                doc_type="ticket",
                min_role_level=2,
                title="Customer Support Tickets",
            )
            if is_new:
                new_docs += 1
            else:
                duplicate_docs += 1
        except Exception as exc:
            logger.error("Failed to ingest %s: %s", tickets_path.name, exc)
            failed_docs += 1

    logger.info(
        "Ingestion run finished. Total: %d | New: %d | Duplicates: %d | Failed: %d",
        total_docs,
        new_docs,
        duplicate_docs,
        failed_docs,
    )

    # 3. Print counts of docs and chunks by doc_type from database
    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Document.doc_type,
                func.count(func.distinct(Document.id)).label("doc_count"),
                func.count(DocumentChunk.id).label("chunk_count"),
            )
            .outerjoin(DocumentChunk, Document.id == DocumentChunk.document_id)
            .where(Document.status == "indexed")
            .group_by(Document.doc_type)
            .order_by(Document.doc_type)
        )
        result = await session.execute(stmt)
        rows = result.all()

        print("\n" + "=" * 60)
        print(" Indexed Corpus Summary (by doc_type)")
        print("=" * 60)
        print(f"{'doc_type':<15} | {'Documents':<15} | {'Chunks':<15}")
        print("-" * 60)
        total_d = 0
        total_c = 0
        for doc_type, doc_cnt, chunk_cnt in rows:
            print(f"{doc_type:<15} | {doc_cnt:<15} | {chunk_cnt:<15}")
            total_d += doc_cnt
            total_c += chunk_cnt
        print("-" * 60)
        print(f"{'TOTAL':<15} | {total_d:<15} | {total_c:<15}")
        print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into R.E.S.A RAG database")
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to manifest CSV (e.g. corpus/manifest.csv)",
    )
    parser.add_argument(
        "--tickets",
        type=Path,
        default=None,
        help="Optional path to tickets CSV (defaults to tickets.csv in manifest directory)",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_ingest(args.manifest, args.tickets))


if __name__ == "__main__":
    main()
