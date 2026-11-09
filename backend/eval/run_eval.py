"""run_eval.py – Run retrieval evaluation over questions.jsonl.

Usage:
    python -m eval.run_eval --k 5
    python -m eval.run_eval --k 5 --label "baseline" --use-cache
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys

from sqlalchemy import select, text

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models.document import Document, DocumentChunk
from app.retrieval.retriever import retrieve
from eval.paths import get_eval_dir, get_metrics_dir


def load_questions() -> list[dict]:
    eval_dir = get_eval_dir()
    q_file = eval_dir / "questions.jsonl"
    if not q_file.is_file():
        raise FileNotFoundError(f"Questions file not found: {q_file}")
    questions = []
    with open(q_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


async def get_document_filenames() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Document.id, Document.source_filename))
        return {str(row.id): row.source_filename for row in res.all()}


async def get_database_fingerprint() -> str:
    hasher = hashlib.sha256()
    async with AsyncSessionLocal() as session:
        stmt = select(DocumentChunk.id, DocumentChunk.content).order_by(DocumentChunk.id)
        result = await session.execute(stmt)
        for chunk_id, content in result.all():
            hasher.update(str(chunk_id).encode("utf-8"))
            hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()


def get_git_sha() -> str:
    # 1. git rev-parse --short HEAD
    try:
        repo_dir = get_eval_dir().parent.parent
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=repo_dir,
        ).decode().strip()
        if out:
            return out
    except Exception:
        pass

    # 2. GIT_SHA environment variable
    env_sha = os.environ.get("GIT_SHA", "").strip()
    if env_sha:
        return env_sha

    # 3. 'unknown'
    return "unknown"


def get_chunking_constants() -> tuple[str | int, str | int]:
    try:
        from app.ingest import chunking
        size = getattr(chunking, "CHUNK_SIZE", None)
        if size is None and hasattr(chunking, "_SPLITTER"):
            size = chunking._SPLITTER.chunk_size
        overlap = getattr(chunking, "CHUNK_OVERLAP", None)
        if overlap is None and hasattr(chunking, "_SPLITTER"):
            overlap = chunking._SPLITTER.chunk_overlap
        return (size if size is not None else "unknown", overlap if overlap is not None else "unknown")
    except Exception:
        return ("unknown", "unknown")


def calc_stats(scores: list[float]) -> dict:
    if not scores:
        return {"min": 0.0, "median": 0.0, "max": 0.0}
    return {
        "min": round(min(scores), 4),
        "median": round(statistics.median(scores), 4),
        "max": round(max(scores), 4),
    }


def append_eval_log(k: int, hit_rate: float, mrr: float, n: int, label: str = "") -> None:
    metrics_dir = get_metrics_dir()
    log_file = metrics_dir / "eval_log.csv"

    timestamp = datetime.now(timezone.utc).isoformat()
    git_sha = get_git_sha()
    chunk_size, chunk_overlap = get_chunking_constants()
    settings = get_settings()
    conf_threshold = settings.CONFIDENCE_THRESHOLD

    header = "timestamp,git_sha,chunk_size,chunk_overlap,k,confidence_threshold,hit_rate,mrr,n,label\n"
    new_row = f"{timestamp},{git_sha},{chunk_size},{chunk_overlap},{k},{conf_threshold:.4f},{hit_rate:.4f},{mrr:.4f},{n},{label}\n"

    if not log_file.is_file():
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(new_row)
    else:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        if lines:
            header_cols = [c.strip() for c in lines[0].split(",")]
            if "label" not in header_cols:
                new_lines = [lines[0].rstrip() + ",label"]
                for line in lines[1:]:
                    if line.strip():
                        new_lines.append(line.rstrip() + ",")
                new_lines.append(new_row.rstrip())
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines) + "\n")
            else:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(new_row)
        else:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(new_row)

    print(f"Wrote {log_file.resolve()}")


def write_scores_csv(records: list[dict]) -> None:
    eval_dir = get_eval_dir()
    scores_file = eval_dir / "scores.csv"
    with open(scores_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "question", "min_role", "answerable", "top1_score", "hit", "reciprocal_rank"])
        for r in records:
            writer.writerow([
                r["id"],
                r["question"],
                r["min_role"],
                r["answerable"],
                f"{r['top1_score']:.4f}",
                r["hit"] if r["answerable"] else "",
                f"{r['reciprocal_rank']:.4f}" if r["answerable"] else "",
            ])
    print(f"Wrote {scores_file.resolve()}")


def write_failures_md(failures: list[dict], k: int, n_answerable: int) -> None:
    eval_dir = get_eval_dir()
    out_file = eval_dir / "failures.md"
    lines = [
        f"# Evaluation Failures (k={k})",
        "",
        f"Total answerable questions evaluated: {n_answerable}",
        f"Total missed questions: {len(failures)}",
        "",
    ]
    if not failures:
        lines.append("No failures encountered. All answerable questions successfully retrieved in the top k.")
        lines.append("")
    else:
        for f in failures:
            lines.append(f"## Question `{f['id']}`: {f['question']}")
            lines.append(f"- **Gold Document(s):** {', '.join(f['gold_filenames'])}")
            lines.append(f"- **Top {len(f['top_chunks'])} Retrieved Chunks:**")
            for rank, chunk in enumerate(f["top_chunks"], start=1):
                lines.append(f"  {rank}. `{chunk['filename']}` (Score: {chunk['score']:.4f}): {chunk['snippet']}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_file.resolve()}")


async def run_evaluation(k: int = 5, label: str = "", use_cache: bool = False) -> dict:
    questions = load_questions()
    doc_filenames = await get_document_filenames()
    db_fingerprint = await get_database_fingerprint()

    eval_dir = get_eval_dir()
    cache_path = eval_dir / ".eval_cache.json"

    cached_records = None
    if use_cache and cache_path.is_file():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            if (
                cache_data.get("fingerprint") == db_fingerprint
                and cache_data.get("k") == k
                and len(cache_data.get("all_records", [])) == len(questions)
            ):
                cached_records = cache_data["all_records"]
        except Exception:
            cached_records = None

    hits = 0
    reciprocal_ranks = []
    rbac_violations = 0

    all_records = []
    ans_scores = []
    oos_scores = []
    res_scores = []
    failures = []

    if cached_records is not None:
        for rec in cached_records:
            qid = rec["id"]
            q_text = rec["question"]
            min_role = rec["min_role"]
            is_answerable = rec["answerable"]
            gold_ids = set(rec["gold_doc_ids"])
            top1_score = rec["top1_score"]
            chunks_data = rec.get("chunks", [])

            for c in chunks_data:
                if c["min_role_level"] > min_role:
                    rbac_violations += 1

            hit_val = 0
            rr_val = 0.0

            if is_answerable:
                ans_scores.append(top1_score)
                retrieved_doc_ids = [str(c["document_id"]) for c in chunks_data]
                first_hit_rank = None
                for rank_idx, doc_id in enumerate(retrieved_doc_ids, start=1):
                    if doc_id in gold_ids:
                        first_hit_rank = rank_idx
                        break

                if first_hit_rank is not None:
                    hits += 1
                    hit_val = 1
                    rr_val = 1.0 / first_hit_rank
                    reciprocal_ranks.append(rr_val)
                else:
                    reciprocal_ranks.append(0.0)
                    failures.append({
                        "id": qid,
                        "question": q_text,
                        "gold_filenames": [doc_filenames.get(gid, gid) for gid in gold_ids],
                        "top_chunks": [
                            {
                                "filename": doc_filenames.get(str(c["document_id"]), "unknown"),
                                "score": c["score"],
                                "snippet": c["content"][:120].replace("\n", " "),
                            }
                            for c in chunks_data[:5]
                        ],
                    })
            elif not gold_ids:
                oos_scores.append(top1_score)
            else:
                res_scores.append(top1_score)

            all_records.append({
                "id": qid,
                "question": q_text,
                "min_role": min_role,
                "answerable": is_answerable,
                "gold_doc_ids": list(gold_ids),
                "top1_score": top1_score,
                "hit": hit_val,
                "reciprocal_rank": rr_val,
                "chunks": chunks_data,
            })
    else:
        for q in questions:
            qid = q["id"]
            q_text = q["question"]
            min_role = q["min_role"]
            is_answerable = q.get("answerable", False)
            gold_ids = set(q.get("gold_doc_ids", []))

            chunks = await retrieve(q_text, user_level=min_role, k=k)
            top1_score = chunks[0].score if chunks else 0.0

            for c in chunks:
                if c.min_role_level > min_role:
                    rbac_violations += 1

            chunks_data = [
                {
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                    "min_role_level": c.min_role_level,
                    "title": c.title,
                    "score": c.score,
                    "content": c.content.strip(),
                }
                for c in chunks
            ]

            hit_val = 0
            rr_val = 0.0

            if is_answerable:
                ans_scores.append(top1_score)
                retrieved_doc_ids = [str(c.document_id) for c in chunks]

                first_hit_rank = None
                for rank_idx, doc_id in enumerate(retrieved_doc_ids, start=1):
                    if doc_id in gold_ids:
                        first_hit_rank = rank_idx
                        break

                if first_hit_rank is not None:
                    hits += 1
                    hit_val = 1
                    rr_val = 1.0 / first_hit_rank
                    reciprocal_ranks.append(rr_val)
                else:
                    reciprocal_ranks.append(0.0)
                    failures.append({
                        "id": qid,
                        "question": q_text,
                        "gold_filenames": [doc_filenames.get(gid, gid) for gid in gold_ids],
                        "top_chunks": [
                            {
                                "filename": doc_filenames.get(str(c.document_id), "unknown"),
                                "score": c.score,
                                "snippet": c.content.strip()[:120].replace("\n", " "),
                            }
                            for c in chunks[:5]
                        ],
                    })
            elif not gold_ids:
                oos_scores.append(top1_score)
            else:
                res_scores.append(top1_score)

            all_records.append({
                "id": qid,
                "question": q_text,
                "min_role": min_role,
                "answerable": is_answerable,
                "gold_doc_ids": list(gold_ids),
                "top1_score": top1_score,
                "hit": hit_val,
                "reciprocal_rank": rr_val,
                "chunks": chunks_data,
            })

        # Save cache
        cache_data = {
            "fingerprint": db_fingerprint,
            "k": k,
            "all_records": all_records,
            "ans_scores": ans_scores,
            "oos_scores": oos_scores,
            "res_scores": res_scores,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

    total_ans = len(ans_scores)
    hit_rate_at_k = hits / total_ans if total_ans > 0 else 0.0
    mrr = sum(reciprocal_ranks) / total_ans if total_ans > 0 else 0.0

    summary = {
        "n_answerable": total_ans,
        "hit_rate_at_k": round(hit_rate_at_k, 4),
        "mrr": round(mrr, 4),
        "rbac_violations": rbac_violations,
        "top_score_stats": {
            "answerable": calc_stats(ans_scores),
            "out_of_scope": calc_stats(oos_scores),
            "restricted": calc_stats(res_scores),
        },
    }

    # Print JSON summary
    print(json.dumps(summary, indent=2))

    # Print 5 lowest-scoring answerable questions
    ans_records = [r for r in all_records if r["answerable"]]
    sorted_ans = sorted(ans_records, key=lambda x: x["top1_score"])
    print("\n5 Lowest-Scoring Answerable Questions:")
    for rank, r in enumerate(sorted_ans[:5], start=1):
        print(f"  {rank}. [{r['id']}] score={r['top1_score']:.4f} | {r['question']}")

    # Print 5 highest-scoring unanswerable questions
    unans_records = [r for r in all_records if not r["answerable"]]
    sorted_unans = sorted(unans_records, key=lambda x: x["top1_score"], reverse=True)
    print("\n5 Highest-Scoring Unanswerable Questions:")
    for rank, r in enumerate(sorted_unans[:5], start=1):
        kind = "restricted" if r["gold_doc_ids"] else "out-of-scope"
        print(f"  {rank}. [{r['id']}] score={r['top1_score']:.4f} ({kind}) | {r['question']}")
    print()

    # Write scores.csv
    write_scores_csv(all_records)

    # Write failures.md
    write_failures_md(failures=failures, k=k, n_answerable=total_ans)

    # Append exactly one row to metrics/eval_log.csv
    append_eval_log(k=k, hit_rate=hit_rate_at_k, mrr=mrr, n=total_ans, label=label)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate RBAC vector retrieval on evaluation questions.")
    parser.add_argument("--k", "-k", type=int, default=5, help="Number of retrieved chunks (default: 5)")
    parser.add_argument("--label", type=str, default="", help="Optional run label for eval_log.csv")
    parser.add_argument("--use-cache", action="store_true", default=False, help="Use cached retrieval results if valid cache exists")
    args = parser.parse_args()

    asyncio.run(run_evaluation(k=args.k, label=args.label, use_cache=args.use_cache))


if __name__ == "__main__":
    main()
