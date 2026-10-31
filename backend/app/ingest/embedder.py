"""embedder.py – text embedding utilities for R.E.S.A ingest pipeline.

Loads BAAI/bge-small-en-v1.5 once, encodes passages with normalize_embeddings=True
and batch_size=32 (no prefix).
Provides a separate embed_query() that prepends the BGE query prefix:
'Represent this sentence for searching relevant passages: '
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load BAAI/bge-small-en-v1.5 model once."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Encode a list of passages with normalize_embeddings=True and batch_size=32 (no prefix)."""
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(e) for e in embeddings]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Alias for embed_passages."""
    return embed_passages(texts)


def embed_query(query: str) -> list[float]:
    """Encode a search query with the BGE query prefix and normalize_embeddings=True."""
    model = get_model()
    prefixed = f"{QUERY_PREFIX}{query}"
    embedding = model.encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    if hasattr(embedding, "tolist"):
        return embedding.tolist()
    return list(embedding)
