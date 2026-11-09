"""calibrate_threshold.py – Calibrate confidence threshold using eval retrieval scores.

Usage:
    python -m eval.calibrate_threshold
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import statistics
import sys
from typing import Any

from sqlalchemy import func, select

from app.db import AsyncSessionLocal
from app.models.document import DocumentChunk
from app.retrieval.retriever import retrieve
from eval.paths import get_eval_dir, get_metrics_dir
from eval.run_eval import load_questions


def compute_group_stats(scores: list[float]) -> dict[str, Any]:
    if not scores:
        return {"min": 0.0, "median": 0.0, "max": 0.0, "deciles": []}
    s_sorted = sorted(scores)
    # 9 decile cut points (10th percentile to 90th percentile)
    if len(s_sorted) >= 2:
        deciles = [round(d, 4) for d in statistics.quantiles(s_sorted, n=10)]
    else:
        deciles = [round(s_sorted[0], 4)] * 9

    return {
        "min": round(min(scores), 4),
        "median": round(statistics.median(scores), 4),
        "max": round(max(scores), 4),
        "deciles": deciles,
    }


def get_ingest_config() -> tuple[str | int, str | int]:
    """Read chunk_size and chunk_overlap from metrics/ingest_config.json."""
    try:
        metrics_dir = get_metrics_dir()
        config_path = metrics_dir / "ingest_config.json"
        if config_path.is_file():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cs = data.get("chunk_size")
            co = data.get("chunk_overlap")
            if cs is not None and co is not None:
                return (cs, co)
    except Exception:
        pass

    try:
        from app.ingest import chunking
        cs = getattr(chunking, "CHUNK_SIZE", 800)
        co = getattr(chunking, "CHUNK_OVERLAP", 120)
        return (cs, co)
    except Exception:
        return (800, 120)


async def get_db_chunk_count() -> int:
    """Query current total chunk count from database."""
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(DocumentChunk.id)))
        return count or 0


async def compute_live_scores() -> tuple[list[float], list[float], list[float]]:
    """Recompute top-1 scores live for every question using retrieve() with no cache."""
    questions = load_questions()
    ans_scores = []
    oos_scores = []
    res_scores = []

    for q in questions:
        chunks = await retrieve(q["question"], user_level=q["min_role"], k=5)
        top1_score = chunks[0].score if chunks else 0.0
        if q.get("answerable") is True:
            ans_scores.append(top1_score)
        elif not q.get("gold_doc_ids"):
            oos_scores.append(top1_score)
        else:
            res_scores.append(top1_score)

    return ans_scores, oos_scores, res_scores


def write_threshold_calibration_json(data: dict[str, Any]) -> None:
    metrics_dir = get_metrics_dir()
    p = metrics_dir / "threshold_calibration.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {p.resolve()}")


async def run_calibration() -> None:
    # 1. Database chunk count and ingest config
    chunk_count = await get_db_chunk_count()
    chunk_size, chunk_overlap = get_ingest_config()

    # Print database chunk count and ingest config at the top of console output
    print("=" * 70)
    print("INGEST CONFIGURATION & DATABASE CHUNKS")
    print("=" * 70)
    print(f"Database Chunk Count: {chunk_count}")
    print(f"Chunk Size:           {chunk_size}")
    print(f"Chunk Overlap:        {chunk_overlap}")
    print("=" * 70)
    print()

    # 2. Live recomputation of top-1 scores (never use cache)
    ans_scores, oos_scores, res_scores = await compute_live_scores()
    unans_scores = oos_scores + res_scores

    ans_stats = compute_group_stats(ans_scores)
    oos_stats = compute_group_stats(oos_scores)
    res_stats = compute_group_stats(res_scores)

    print("=" * 70)
    print("RETRIEVAL TOP-1 SCORE DISTRIBUTIONS")
    print("=" * 70)
    print(f"Answerable (n={len(ans_scores)}):")
    print(f"  Min:    {ans_stats['min']:.4f}")
    print(f"  Median: {ans_stats['median']:.4f}")
    print(f"  Max:    {ans_stats['max']:.4f}")
    print(f"  Deciles (10%..90%): {ans_stats['deciles']}")
    print()
    print(f"Out-of-Scope (n={len(oos_scores)}):")
    print(f"  Min:    {oos_stats['min']:.4f}")
    print(f"  Median: {oos_stats['median']:.4f}")
    print(f"  Max:    {oos_stats['max']:.4f}")
    print(f"  Deciles (10%..90%): {oos_stats['deciles']}")
    print()
    print(f"Restricted (n={len(res_scores)}):")
    print(f"  Min:    {res_stats['min']:.4f}")
    print(f"  Median: {res_stats['median']:.4f}")
    print(f"  Max:    {res_stats['max']:.4f}")
    print(f"  Deciles (10%..90%): {res_stats['deciles']}")
    print("=" * 70)

    # Threshold sweep: 0.20 to 0.90 step 0.01
    sweep_results = []
    n_unans = len(unans_scores)
    n_ans = len(ans_scores)

    thresholds = [round(t * 0.01, 2) for t in range(20, 91)]

    for t in thresholds:
        refusals = sum(1 for s in unans_scores if s < t)
        refusal_rate = refusals / n_unans if n_unans > 0 else 0.0

        false_refusals = sum(1 for s in ans_scores if s < t)
        false_refusal_rate = false_refusals / n_ans if n_ans > 0 else 0.0

        sweep_results.append({
            "threshold": t,
            "refusal_rate": round(refusal_rate, 4),
            "false_refusal_rate": round(false_refusal_rate, 4),
            "unanswerable_refused": refusals,
            "answerable_false_refused": false_refusals,
        })

    # Recommendation rule:
    # highest refusal rate where false refusals stay at or below 10%.
    # If several tie, choose the lowest threshold.
    eligible = [r for r in sweep_results if r["false_refusal_rate"] <= 0.10]
    if not eligible:
        eligible = sweep_results

    max_refusal = max(r["refusal_rate"] for r in eligible)
    best_candidates = [r for r in eligible if r["refusal_rate"] == max_refusal]
    recommended = min(best_candidates, key=lambda r: r["threshold"])

    print("\nTHRESHOLD CALIBRATION RESULTS")
    print("-" * 70)
    print(f"Total Questions Evaluated:    {n_ans + n_unans}")
    print(f"  - Answerable:               {n_ans}")
    print(f"  - Out-of-scope:             {len(oos_scores)}")
    print(f"  - Restricted:               {len(res_scores)}")
    print(f"  - Total Unanswerable:       {n_unans}")
    print()
    print(f"Recommended Threshold:        {recommended['threshold']:.2f}")
    print(f"  - Refusal Rate (Unanswerable):  {recommended['refusal_rate'] * 100:.2f}% ({recommended['unanswerable_refused']}/{n_unans})")
    print(f"  - False Refusal Rate (Answerable): {recommended['false_refusal_rate'] * 100:.2f}% ({recommended['answerable_false_refused']}/{n_ans})")
    print("-" * 70)

    # Save to metrics/threshold_calibration.json
    output_data = {
        "chunk_count": chunk_count,
        "total_chunk_count": chunk_count,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "recommended_threshold": recommended["threshold"],
        "refusal_rate_at_recommended": recommended["refusal_rate"],
        "false_refusal_rate_at_recommended": recommended["false_refusal_rate"],
        "group_sizes": {
            "answerable": n_ans,
            "out_of_scope": len(oos_scores),
            "restricted": len(res_scores),
            "unanswerable_total": n_unans,
            "total": n_ans + n_unans,
        },
        "group_statistics": {
            "answerable": ans_stats,
            "out_of_scope": oos_stats,
            "restricted": res_stats,
        },
        "sweep_results": sweep_results,
    }

    write_threshold_calibration_json(output_data)


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_calibration())


if __name__ == "__main__":
    main()
