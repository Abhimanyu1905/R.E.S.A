PROJECT: R.E.S.A Support, a RAG support assistant. Solo build, 6 weeks.

STACK: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, psycopg 3,
PostgreSQL 16 + pgvector (HNSW, cosine), sentence-transformers
BAAI/bge-small-en-v1.5 (384 dims, normalized; query prefix
'Represent this sentence for searching relevant passages: ' for queries only),
Gemini (gemini-flash-latest) via the google-genai SDK behind an LLMClient interface,
React 18 + Vite + TypeScript + TanStack Query + Zustand + Recharts,
Docker Compose, pytest, ruff, mypy, GitHub Actions.

LAYOUT: backend/app/{main.py,config.py,deps.py,db.py,models/,schemas/,
routers/,retrieval/,ingest/,rag/,llm/}, backend/tests, backend/eval,
frontend/, db/init.sql, metrics/, docs/devlog.md.

RULES:
1. RBAC: roles employee=1, agent=2, admin=3. A chunk is visible only if
   chunk.min_role_level <= user level, enforced in the retrieval SQL WHERE
   clause. user_level is a required argument with no default. Role level is
   always read from the DB, never from the client.
2. Guardrail: if top cosine score < CONFIDENCE_THRESHOLD (env, default 0.35),
   refuse WITHOUT calling the LLM and log to unanswered_questions.
3. Answers cite with [C1]..[C5] tags. Drop invalid tags. Zero valid citations
   means refusal.
4. Secrets only via env (pydantic-settings). Never commit .env.
5. Unit tests mock the LLM and embedder. Integration tests use real Postgres.
6. Do only what the prompt asks. List files changed. For RBAC, guardrail and
   endpoints, write the failing test first.
7. All routes under /api/v1. Error body: {detail: str, code: str}.
8. Only record metrics from real command output. Never invent numbers.