-- db/init.sql  – runs once when the Postgres container is first created.
-- Requires: pgvector extension available in the image (pgvector/pgvector:pg16)

CREATE EXTENSION IF NOT EXISTS vector;
