# R.E.S.A Support – Dev Log

| Date | Phase | What changed | What moved | Next |
|------|-------|--------------|------------|------|
| 2026-10-29 | 1: Scaffold | Monorepo, FastAPI health route, Docker Compose, pgvector, Alembic baseline schema | Stack runs; health returns ok on :8001 | Phase 2: corpus |
| 2026-10-30 | 2: Corpus | 42 policy/FAQ docs, tickets.csv (200 rows), markers.csv, manifest.csv, conflicts.md in corpus/ | Knowledge base exists at access levels 1, 2 and 3; leak-test markers ready | Phase 3: ingestion |
| 2026-10-31 | 3: Ingestion | Parsers, cleaning, chunking, BGE embedder, ingest pipeline, manifest CLI, inspect_search script; 28 unit tests pass | Corpus documents are chunked, embedded and indexed in the database | Phase 4: RBAC retrieval |
| 2026-10-31 | 4: RBAC retrieval | RBAC-filtered retriever, leak tests, row-level security | Employees can no longer retrieve level 2 or 3 chunks; tests prove it | Phase 5: eval set and threshold calibration |
| 2026-10-31 | 5: Eval set & threshold | Frozen 58-question eval set in eval/questions.jsonl, scripts/run_eval.py runner | Hit-rate@5: 1.0000, MRR: 0.9383, 100% RBAC isolation, optimal threshold calibrated to 0.67 | Phase 6: RAG generation & guardrail |

## Notes for future sessions
- Run the stack: `docker compose up -d --build`; health at http://localhost:8001/api/v1/health
- Run tests from `backend/`: `pytest -q`
- Never edit `eval/questions.jsonl` after it is frozen.
- Only record metrics from real command output. Never estimate numbers.