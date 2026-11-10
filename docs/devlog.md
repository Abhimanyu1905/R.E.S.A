# R.E.S.A Support – Dev Log

| Date | Phase | What changed | What moved | Next |
|------|-------|--------------|------------|------|
| 2026-10-29 | 1: Scaffold | Monorepo, FastAPI health route, Docker Compose, pgvector, Alembic baseline schema | Stack runs; health returns ok on :8001 | Phase 2: corpus |
| 2026-10-30 | 2: Corpus | 42 policy/FAQ docs, tickets.csv (200 rows), markers.csv, manifest.csv, conflicts.md in corpus/ | Knowledge base exists at access levels 1, 2 and 3; leak-test markers ready | Phase 3: ingestion |
| 2026-10-31 | 3: Ingestion | Parsers, cleaning, chunking, BGE embedder, ingest pipeline, manifest CLI, inspect_search script; 28 unit tests pass | Corpus documents are chunked, embedded and indexed in the database | Phase 4: RBAC retrieval |
| 2026-10-31 | 4: RBAC retrieval | RBAC-filtered retriever, leak tests, row-level security | Employees can no longer retrieve level 2 or 3 chunks; tests prove it | Phase 5: eval set and threshold calibration |
| 2026-11-09 | 5: Eval | 70-question eval set (50 answerable), eval runner, threshold calibration, chunk and k experiments | Chunk 500/75 raised MRR from 0.964 to 0.990 (hit-rate@5 stayed 1.0); chunk 1200 gave no gain; k=3 was worse; k=5 kept. Threshold calibrated on 500/75 chunks: script optimum 0.71, chosen 0.69 for margin and to block all restricted questions at the score gate | Phase 6: auth |
| 2026-11-10 | 6: Auth | Register, login, refresh and /auth/me endpoints; bcrypt password hashing; JWT access (30 min) and refresh (7 day) tokens; role level loaded from the database on every request; require_role dependency; admin-only user list and update; login rate limit; seed script for employee, agent and admin users; auth tests (8 passed>) | Users can log in as all three roles; a role change takes effect without logging in again; employees get 403 on admin routes | Phase 7: LLM client, /query, guardrail and citations |
## Notes for future sessions
- Run the stack: `docker compose up -d --build`; health at http://localhost:8001/api/v1/health
- Run tests from `backend/`: `pytest -q`
- Never edit `eval/questions.jsonl` after it is frozen.
- Only record metrics from real command output. Never estimate numbers.
- Docker image has no pytest yet (pytest-asyncio pin conflict between requirements.txt and requirements-dev.txt). If you recreate the container, run: docker exec resa-backend-1 pip install pytest pytest-asyncio
