"""cli.py – CLI command to bulk-ingest documents from a manifest.

Usage:
    python -m app.ingest.cli --manifest corpus/manifest.csv
    python -m app.ingest.cli --reindex --chunk-size 800 --chunk-overlap 120
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

from sqlalchemy import func, select

from app.db import AsyncSessionLocal
from app.ingest.pipeline import ingest_file, reindex_document
from app.models.document import Document, DocumentChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_cli")


def write_ingest_config(
    chunk_size: int,
    chunk_overlap: int,
    total_chunk_count: int,
) -> None:
    """Write /app/metrics/ingest_config.json if /app/metrics exists; otherwise warn and skip."""
    metrics_dir = Path("/app/metrics")
    if not metrics_dir.is_dir():
        warning_msg = "WARNING: /app/metrics does not exist; skipping writing ingest_config.json"
        logger.warning(warning_msg)
        print(warning_msg)
        return

    config_data = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_chunk_count": total_chunk_count,
    }
    target_file = metrics_dir / "ingest_config.json"
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        logger.info("Successfully wrote ingest config to %s", target_file)
    except Exception as exc:
        logger.warning("Failed to write %s: %s", target_file, exc)


async def run_reindex(
    manifest_path: Path,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> None:
    """Reindex all manifest documents in ONE transaction per document."""
    if not manifest_path.is_file():
        candidates = [
            Path("corpus/manifest.csv"),
            Path("/app/corpus/manifest.csv"),
            Path(__file__).resolve().parent.parent.parent.parent / "corpus" / "manifest.csv",
        ]
        found = False
        for c in candidates:
            if c.is_file():
                manifest_path = c
                found = True
                break
        if not found:
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest_dir = manifest_path.parent

    # 1. Read manifest rows
    manifest_rows: dict[str, dict] = {}
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            manifest_rows[row["filename"]] = row

    # 2. Get total chunks before and check DB documents
    async with AsyncSessionLocal() as session:
        chunks_before = await session.scalar(select(func.count(DocumentChunk.id))) or 0
        res = await session.execute(select(Document))
        db_docs = res.scalars().all()

    print(f"Total chunk count before reindex: {chunks_before}")

    # 3. Identify and warn about documents in DB not in manifest
    db_docs_by_filename = {d.source_filename: d for d in db_docs}
    untouched_docs = [
        d.source_filename
        for d in db_docs
        if d.source_filename not in manifest_rows
    ]
    if untouched_docs:
        warning_msg = (
            f"WARNING: The following {len(untouched_docs)} document(s) in database are not "
            f"in manifest and stay untouched: {', '.join(sorted(untouched_docs))}"
        )
        logger.warning(warning_msg)
        print(warning_msg)

    # 4. Reindex each manifest document in ONE transaction per document
    reindexed_count = 0
    failed_count = 0

    for filename in manifest_rows:
        db_doc = db_docs_by_filename.get(filename)
        if not db_doc:
            logger.warning("Manifest document %s not found in database; skipping", filename)
            continue

        target_path = manifest_dir / filename
        if not target_path.is_file():
            alt_candidates = [
                Path("corpus") / filename,
                Path("/app/corpus") / filename,
            ]
            for alt in alt_candidates:
                if alt.is_file():
                    target_path = alt
                    break

        if not target_path.is_file():
            logger.error("Source file for %s not found at %s", filename, target_path)
            failed_count += 1
            continue

        try:
            n_chunks = await reindex_document(
                doc_id=db_doc.id,
                source_path=target_path,
                doc_type=db_doc.doc_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            reindexed_count += 1
            logger.info("Reindexed %s (%d chunks)", filename, n_chunks)
        except Exception as exc:
            logger.error("Failed to reindex %s: %s", filename, exc, exc_info=True)
            failed_count += 1

    # 5. Get total chunks after
    async with AsyncSessionLocal() as session:
        chunks_after = await session.scalar(select(func.count(DocumentChunk.id))) or 0

    print(f"Total chunk count after reindex: {chunks_after}")
    logger.info(
        "Reindex completed. Reindexed: %d | Failed: %d | Total chunks: %d -> %d",
        reindexed_count,
        failed_count,
        chunks_before,
        chunks_after,
    )

    # 6. Write ingest_config.json
    write_ingest_config(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        total_chunk_count=chunks_after,
    )


async def run_ingest(
    manifest_path: Path,
    tickets_path: Path | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> None:
    """Ingest documents from manifest and tickets, then print counts."""
    if not manifest_path.is_file():
        candidates = [
            Path("corpus/manifest.csv"),
            Path("/app/corpus/manifest.csv"),
            Path(__file__).resolve().parent.parent.parent.parent / "corpus" / "manifest.csv",
        ]
        found = False
        for c in candidates:
            if c.is_file():
                manifest_path = c
                found = True
                break
        if not found:
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
                alt_candidates = [
                    Path("corpus") / filename,
                    Path("/app/corpus") / filename,
                ]
                for alt in alt_candidates:
                    if alt.is_file():
                        target_path = alt
                        break

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
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
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
        else:
            for alt in [Path("corpus/tickets.csv"), Path("/app/corpus/tickets.csv")]:
                if alt.is_file():
                    tickets_path = alt
                    break

    if tickets_path and tickets_path.is_file():
        total_docs += 1
        try:
            doc, is_new = await ingest_file(
                path=tickets_path,
                doc_type="ticket",
                min_role_level=2,
                title="Customer Support Tickets",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
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

        # 4. Write ingest_config.json
        total_chunks = await session.scalar(select(func.count(DocumentChunk.id))) or 0

    write_ingest_config(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        total_chunk_count=total_chunks,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into R.E.S.A RAG database")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("corpus/manifest.csv"),
        help="Path to manifest CSV (default: corpus/manifest.csv)",
    )
    parser.add_argument(
        "--tickets",
        type=Path,
        default=None,
        help="Optional path to tickets CSV (defaults to tickets.csv in manifest directory)",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        default=False,
        help="Reindex all manifest documents (re-chunk and re-embed in place)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Chunk size in characters (default: 800)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=120,
        help="Chunk overlap in characters (default: 120)",
    )
    args = parser.parse_args()

    if args.chunk_overlap >= args.chunk_size:
        parser.error(
            f"--chunk-overlap ({args.chunk_overlap}) must be smaller than --chunk-size ({args.chunk_size})"
        )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if args.reindex:
        asyncio.run(
            run_reindex(
                manifest_path=args.manifest,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
        )
    else:
        asyncio.run(
            run_ingest(
                manifest_path=args.manifest,
                tickets_path=args.tickets,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
        )


if __name__ == "__main__":
    main()
