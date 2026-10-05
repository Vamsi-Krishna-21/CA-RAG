"""
Wraps sentence-transformers so the rest of the app just calls embed_text() /
embed_batch() without knowing which model is loaded. Model loads once and is
reused (loading it per-request would be far too slow).
"""
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings


@lru_cache(maxsize=1)
def _get_model():
    return SentenceTransformer(settings.embedding_model)


@lru_cache(maxsize=4096)
def _embed_text_cached(text: str) -> np.ndarray:
    return _get_model().encode(text, normalize_embeddings=True)


def embed_text(text: str) -> np.ndarray:
    # The same text always yields the same embedding, so repeated calls within a
    # request (chunk text is embedded during validation AND hallucination
    # detection; the query is embedded once per rewrite) are served from cache.
    # Hand out a copy so no caller can mutate the cached vector (FAISS and numpy
    # helpers are free to work in place on what they receive).
    return _embed_text_cached(text).copy()


def embed_batch(texts):
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
