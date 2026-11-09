"""make_review.py – Generate human-readable review.md from questions.jsonl.

Reads backend/eval/questions.jsonl, queries pgvector for each question's gold document
and best-matching chunk, and writes backend/eval/review.md.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
eval_dir = Path(__file__).resolve().parent
backend_dir = eval_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.ingest.embedder import embed_query
from app.models.document import Document, DocumentChunk


async def main() -> None:
    questions_file = eval_dir / "questions.jsonl"
    review_file = eval_dir / "review.md"

    if not questions_file.is_file():
        raise FileNotFoundError(f"Could not find questions file at {questions_file}")

    questions: list[dict] = []
    with open(questions_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))

    print(f"Loaded {len(questions)} questions from {questions_file}")

    blocks: list[str] = [
        "# R.E.S.A Support – Evaluation Questions Manual Review",
        "",
        f"Generated review blocks for {len(questions)} evaluation questions.",
        "",
        "---",
        "",
    ]

    async with AsyncSessionLocal() as session:
        for idx, q in enumerate(questions, start=1):
            qid = q.get("id", f"q{idx}")
            question_text = q.get("question", "")
            min_role = q.get("min_role")
            answerable = q.get("answerable")
            gold_doc_ids = q.get("gold_doc_ids", [])

            block_lines = [
                f"## Question {idx}: {qid}",
                "",
                f"- **ID:** `{qid}`",
                f"- **Question:** {question_text}",
                f"- **Min Role:** `{min_role}`",
                f"- **Answerable:** `{answerable}`",
            ]

            if not gold_doc_ids:
                block_lines.append("- **Gold Document:** OUT OF SCOPE")
                block_lines.append("")
                block_lines.append("> OUT OF SCOPE")
            else:
                gold_doc_id_str = gold_doc_ids[0]
                gold_uuid = uuid.UUID(gold_doc_id_str)

                # Fetch gold document info
                doc = await session.get(Document, gold_uuid)
                doc_title = doc.title if doc else "UNKNOWN TITLE"
                doc_role = doc.min_role_level if doc else "UNKNOWN"

                block_lines.append(f"- **Gold Document Title:** {doc_title}")
                block_lines.append(f"- **Gold Document Min Role Level:** `{doc_role}`")
                block_lines.append(f"- **Gold Document ID:** `{gold_doc_id_str}`")

                # Compute query embedding and get best-matching chunk from the gold doc
                qvec = embed_query(question_text)
                dist_expr = DocumentChunk.embedding.cosine_distance(qvec)
                similarity_expr = (1.0 - dist_expr).label("score")

                stmt = (
                    select(
                        DocumentChunk.content,
                        similarity_expr,
                        DocumentChunk.chunk_index,
                    )
                    .where(DocumentChunk.document_id == gold_uuid)
                    .order_by(dist_expr.asc())
                    .limit(1)
                )

                chunk_result = await session.execute(stmt)
                row = chunk_result.first()

                if row:
                    best_content = row.content.strip()
                    score = float(row.score)
                    block_lines.append(f"- **Highest Cosine Score:** `{score:.4f}` (Chunk Index: {row.chunk_index})")
                    block_lines.append("")
                    block_lines.append("**Best-Matching Chunk Text:**")
                    block_lines.append("")
                    # Indent or quote chunk content
                    quoted = "\n".join(f"> {line}" for line in best_content.splitlines())
                    block_lines.append(quoted)
                else:
                    block_lines.append("")
                    block_lines.append("> [No chunks found for this document in the database]")

            block_lines.append("")
            block_lines.append("---")
            block_lines.append("")
            blocks.append("\n".join(block_lines))

            print(f"[{idx}/{len(questions)}] Processed {qid}")

    review_content = "\n".join(blocks)
    with open(review_file, "w", encoding="utf-8") as f:
        f.write(review_content)

    print(f"\nSuccessfully wrote {len(questions)} review blocks to {review_file}")


if __name__ == "__main__":
    asyncio.run(main())
