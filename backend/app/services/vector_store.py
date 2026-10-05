"""
Thin FAISS wrapper: one flat index per document, persisted to disk under
VECTOR_STORE_DIR alongside a JSON sidecar of chunk metadata. Kept simple
(IndexFlatIP over normalized vectors == cosine similarity search) rather
than pulling in a full vector-DB client -- appropriate at the scale of a
handful of papers per user.
"""
import json
import os
import faiss
import numpy as np
from app.config import settings


def _paths(document_id: str):
    base = os.path.join(settings.vector_store_dir, document_id)
    return base + ".index", base + ".json"


def save_document_index(document_id: str, embeddings: np.ndarray, chunk_meta: list):
    os.makedirs(settings.vector_store_dir, exist_ok=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(np.ascontiguousarray(embeddings, dtype="float32"))

    index_path, meta_path = _paths(document_id)
    faiss.write_index(index, index_path)
    with open(meta_path, "w") as f:
        json.dump(chunk_meta, f)


# Small in-memory cache of loaded indexes. Keyed by document and invalidated
# whenever either file changes on disk (re-processing rewrites them).
_INDEX_CACHE: dict = {}
_INDEX_CACHE_MAX = 16


def _file_stamp(path: str):
    st = os.stat(path)
    return (st.st_mtime_ns, st.st_size)


def load_document_index(document_id: str):
    index_path, meta_path = _paths(document_id)
    if not os.path.exists(index_path):
        _INDEX_CACHE.pop(document_id, None)
        return None, []

    stamp = (_file_stamp(index_path), _file_stamp(meta_path))
    cached = _INDEX_CACHE.get(document_id)
    if cached is not None and cached[0] == stamp:
        return cached[1], cached[2]

    index = faiss.read_index(index_path)
    with open(meta_path) as f:
        chunk_meta = json.load(f)

    if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    _INDEX_CACHE[document_id] = (stamp, index, chunk_meta)
    return index, chunk_meta


def search(document_id: str, query_embedding: np.ndarray, top_k: int = 10):
    index, chunk_meta = load_document_index(document_id)
    if index is None:
        return []
    query_embedding = np.ascontiguousarray(query_embedding.reshape(1, -1), dtype="float32")
    scores, idxs = index.search(query_embedding, min(top_k, index.ntotal))
    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        meta = dict(chunk_meta[idx])
        meta["semantic_score"] = float(score)
        results.append(meta)
    return results
