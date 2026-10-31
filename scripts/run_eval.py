"""run_eval.py – Run retrieval evaluation over eval/questions.jsonl.

Usage:
    python scripts/run_eval.py
    docker exec resa-backend-1 python scripts/run_eval.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if backend_dir.is_dir() and str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.retrieval.retriever import retrieve


def load_questions() -> list[dict]:
    candidate_paths = [
        repo_root / "eval" / "questions.jsonl",
        backend_dir / "eval" / "questions.jsonl",
        Path("/app/eval/questions.jsonl"),
    ]
    for p in candidate_paths:
        if p.is_file():
            questions = []
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        questions.append(json.loads(line))
            return questions
    raise FileNotFoundError("Could not locate eval/questions.jsonl")


async def evaluate():
    questions = load_questions()
    print("=" * 70)
    print(f"R.E.S.A Support – Evaluation Suite (Total Questions: {len(questions)})")
    print("=" * 70)

    answerable = [q for q in questions if q.get("answerable") is True]
    out_of_scope = [q for q in questions if not q.get("answerable") and not q.get("gold_doc_ids")]
    rbac_leak = [q for q in questions if not q.get("answerable") and q.get("gold_doc_ids")]

    print(f"  • Answerable queries:           {len(answerable)}")
    print(f"  • Out-of-scope queries:         {len(out_of_scope)}")
    print(f"  • RBAC access denial queries:   {len(rbac_leak)}")
    print("-" * 70)

    # 1. Answerable metrics
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    answerable_scores = []

    for q in answerable:
        gold_id = q["gold_doc_ids"][0]
        chunks = await retrieve(q["question"], user_level=q["min_role"], k=5)
        retrieved_ids = [str(c.document_id) for c in chunks]

        top_score = chunks[0].score if chunks else 0.0
        answerable_scores.append(top_score)

        if gold_id in retrieved_ids:
            rank = retrieved_ids.index(gold_id) + 1
            reciprocal_ranks.append(1.0 / rank)
            if rank == 1:
                hits_at_1 += 1
            if rank <= 3:
                hits_at_3 += 1
            if rank <= 5:
                hits_at_5 += 1
        else:
            reciprocal_ranks.append(0.0)

    total_ans = len(answerable)
    hit_rate_1 = hits_at_1 / total_ans
    hit_rate_3 = hits_at_3 / total_ans
    hit_rate_5 = hits_at_5 / total_ans
    mrr = sum(reciprocal_ranks) / total_ans

    # 2. Out-of-scope metrics
    oos_scores = []
    for q in out_of_scope:
        chunks = await retrieve(q["question"], user_level=q["min_role"], k=5)
        top_score = chunks[0].score if chunks else 0.0
        oos_scores.append(top_score)

    # 3. RBAC isolation metrics
    rbac_passed = 0
    rbac_scores = []
    for q in rbac_leak:
        forbidden_gold_id = q["gold_doc_ids"][0]
        chunks = await retrieve(q["question"], user_level=q["min_role"], k=5)
        retrieved_ids = [str(c.document_id) for c in chunks]
        top_score = chunks[0].score if chunks else 0.0
        rbac_scores.append(top_score)

        # Ensure forbidden doc is not retrieved AND no chunk exceeds user_level
        leaked = (forbidden_gold_id in retrieved_ids) or any(c.min_role_level > q["min_role"] for c in chunks)
        if not leaked:
            rbac_passed += 1

    print("\n[1] RETRIEVAL QUALITY (Answerable Questions)")
    print(f"  • Hit-rate@1:  {hit_rate_1:.4f} ({hits_at_1}/{total_ans})")
    print(f"  • Hit-rate@3:  {hit_rate_3:.4f} ({hits_at_3}/{total_ans})")
    print(f"  • Hit-rate@5:  {hit_rate_5:.4f} ({hits_at_5}/{total_ans})")
    print(f"  • MRR:         {mrr:.4f}")
    print(f"  • Top score range: min={min(answerable_scores):.4f}, avg={sum(answerable_scores)/total_ans:.4f}, max={max(answerable_scores):.4f}")

    print("\n[2] RBAC SECURITY ENFORCEMENT (Role Level 1 callers against L2/L3 Docs)")
    print(f"  • Leakage prevention rate: {rbac_passed}/{len(rbac_leak)} ({(rbac_passed/len(rbac_leak))*100:.1f}%)")
    print(f"  • Highest retrieved (allowed) score: max={max(rbac_scores):.4f}, avg={sum(rbac_scores)/len(rbac_scores):.4f}")

    print("\n[3] OUT-OF-SCOPE QUERIES (Threshold Calibration)")
    print(f"  • Score range: min={min(oos_scores):.4f}, avg={sum(oos_scores)/len(oos_scores):.4f}, max={max(oos_scores):.4f}")

    print("\n[4] THRESHOLD RECOMMENDATION")
    suggested_threshold = round((min(answerable_scores) + max(oos_scores)) / 2.0, 2)
    print(f"  • Lowest Answerable Top-1:     {min(answerable_scores):.4f}")
    print(f"  • Highest Out-Of-Scope Top-1:  {max(oos_scores):.4f}")
    print(f"  • Optimal Separation Threshold: {suggested_threshold} (Current env default: 0.35 -> Calibrated: {suggested_threshold})")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(evaluate())
