"""
Thin FAISS wrapper: one flat index per document, persisted to disk under
VECTOR_STORE_DIR alongside a JSON sidecar of chunk metadata. Kept simple
(IndexFlatIP over normalized vectors == cosine similarity search) rather
than pulling in a full vector-DB client -- appropriate at the scale of a
handful of papers per user.

Restores missing local indexes from MongoDB Atlas asynchronously when
ephemeral cloud container storage resets.
"""
import asyncio
import json
import logging
import os
import faiss
import numpy as np
from bson import ObjectId

from app.config import settings
from app.database.mongodb import get_db

logger = logging.getLogger("uvicorn.error")

_INDEX_CACHE: dict = {}
_INDEX_CACHE_MAX = 16

_HYDRATION_LOCKS: dict[str, asyncio.Lock] = {}
_HYDRATION_MASTER_LOCK = asyncio.Lock()


async def _get_hydration_lock(document_id: str) -> asyncio.Lock:
    async with _HYDRATION_MASTER_LOCK:
        if document_id not in _HYDRATION_LOCKS:
            _HYDRATION_LOCKS[document_id] = asyncio.Lock()
        return _HYDRATION_LOCKS[document_id]


def _paths(document_id: str):
    base = os.path.join(settings.vector_store_dir, document_id)
    return base + ".index", base + ".json"


def _file_stamp(path: str):
    st = os.stat(path)
    return (st.st_mtime_ns, st.st_size)


def save_document_index(document_id: str, embeddings: np.ndarray, chunk_meta: list):
    os.makedirs(settings.vector_store_dir, exist_ok=True)
    dim = embeddings.shape[1] if embeddings.ndim > 1 and embeddings.shape[1] > 0 else 384
    index = faiss.IndexFlatIP(dim)
    if embeddings.shape[0] > 0:
        index.add(np.ascontiguousarray(embeddings, dtype="float32"))

    index_path, meta_path = _paths(document_id)
    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunk_meta, f)

    stamp = (_file_stamp(index_path), _file_stamp(meta_path))
    if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    _INDEX_CACHE[document_id] = (stamp, index, chunk_meta)


def invalidate_cache(document_id: str) -> None:
    """Remove document from memory cache and remove local files if present."""
    _INDEX_CACHE.pop(document_id, None)
    index_path, meta_path = _paths(document_id)
    for p in (index_path, meta_path):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def load_document_index(document_id: str):
    index_path, meta_path = _paths(document_id)
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        _INDEX_CACHE.pop(document_id, None)
        return None, []

    try:
        stamp = (_file_stamp(index_path), _file_stamp(meta_path))
    except OSError:
        _INDEX_CACHE.pop(document_id, None)
        return None, []

    cached = _INDEX_CACHE.get(document_id)
    if cached is not None and cached[0] == stamp:
        return cached[1], cached[2]

    try:
        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            chunk_meta = json.load(f)
    except Exception as exc:
        logger.warning("Failed loading index or metadata from disk for %s: %s", document_id, exc)
        _INDEX_CACHE.pop(document_id, None)
        return None, []

    if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    _INDEX_CACHE[document_id] = (stamp, index, chunk_meta)
    return index, chunk_meta


async def ensure_document_index(document_id: str) -> bool:
    """
    Asynchronously ensures that the local FAISS index and JSON metadata exist
    and are valid on disk and in _INDEX_CACHE.

    If files are missing or corrupt, hydrates from MongoDB chunks collection.
    Handles concurrent requests safely via per-document locks.
    """
    index_path, meta_path = _paths(document_id)

    # Fast path: check if local files exist and are readable
    if os.path.exists(index_path) and os.path.exists(meta_path):
        idx, meta = load_document_index(document_id)
        if idx is not None:
            return True

    # Hydration path: synchronize concurrent requests for the same document
    lock = await _get_hydration_lock(document_id)
    async with lock:
        # Re-check fast path under lock in case another request already hydrated it
        if os.path.exists(index_path) and os.path.exists(meta_path):
            idx, meta = load_document_index(document_id)
            if idx is not None:
                return True

        db = get_db()
        try:
            doc_oid = ObjectId(document_id)
        except Exception:
            logger.warning("ensure_document_index: invalid document_id format %s", document_id)
            return False

        doc = await db.documents.find_one({"_id": doc_oid})
        if not doc:
            logger.warning("ensure_document_index: document %s not found in DB", document_id)
            return False

        if doc.get("status") != "ready":
            logger.warning(
                "ensure_document_index: document %s is not ready (status: %s)",
                document_id,
                doc.get("status"),
            )
            return False

        expected_count = doc.get("chunk_count")

        cursor = db.chunks.find({"document_id": document_id}).sort("chunk_index", 1)
        chunk_records = [c async for c in cursor]

        if not chunk_records:
            if expected_count == 0:
                save_document_index(document_id, np.zeros((0, 384), dtype=np.float32), [])
                return True
            logger.warning("ensure_document_index: no chunks found for document %s", document_id)
            return False

        # Validation: chunk count
        if expected_count is not None and len(chunk_records) != expected_count:
            logger.error(
                "ensure_document_index: chunk count mismatch for %s: expected %d, got %d",
                document_id,
                expected_count,
                len(chunk_records),
            )
            return False

        # Validation: contiguous indices [0, 1, ..., N-1]
        indices = [c.get("chunk_index") for c in chunk_records]
        if indices != list(range(len(chunk_records))):
            logger.error(
                "ensure_document_index: non-contiguous chunk indices for %s: %s",
                document_id,
                indices,
            )
            return False

        # Validation: embedding vectors and metadata
        raw_vectors = []
        chunk_meta = []
        for c in chunk_records:
            emb_data = c.get("embedding")
            if not emb_data:
                logger.error("ensure_document_index: missing embedding in chunk %s", c.get("chunk_id"))
                return False

            if isinstance(emb_data, (bytes, bytearray)):
                if len(emb_data) != 384 * 4:
                    logger.error(
                        "ensure_document_index: invalid byte size %d for embedding in chunk %s",
                        len(emb_data),
                        c.get("chunk_id"),
                    )
                    return False
                vec = np.frombuffer(emb_data, dtype=np.float32)
            elif isinstance(emb_data, list):
                if len(emb_data) != 384:
                    logger.error(
                        "ensure_document_index: invalid list length %d for embedding in chunk %s",
                        len(emb_data),
                        c.get("chunk_id"),
                    )
                    return False
                vec = np.array(emb_data, dtype=np.float32)
            else:
                logger.error("ensure_document_index: unexpected embedding type %s", type(emb_data))
                return False

            raw_vectors.append(vec)
            chunk_meta.append({
                "chunk_id": c.get("chunk_id"),
                "document_id": document_id,
                "text": c.get("text", ""),
                "page_start": c.get("page_start", 1),
                "page_end": c.get("page_end", 1),
                "section": c.get("section", ""),
            })

        embeddings = np.vstack(raw_vectors).astype("float32")

        # Atomic file write to avoid partial reads by concurrent processes
        os.makedirs(settings.vector_store_dir, exist_ok=True)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(np.ascontiguousarray(embeddings, dtype="float32"))

        tmp_index = index_path + ".tmp"
        tmp_meta = meta_path + ".tmp"
        try:
            faiss.write_index(index, tmp_index)
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump(chunk_meta, f)
            os.replace(tmp_index, index_path)
            os.replace(tmp_meta, meta_path)
        except Exception as exc:
            for p in (tmp_index, tmp_meta):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            logger.error("ensure_document_index: failed writing files for %s: %s", document_id, exc)
            return False

        stamp = (_file_stamp(index_path), _file_stamp(meta_path))
        if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
            _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
        _INDEX_CACHE[document_id] = (stamp, index, chunk_meta)

        return True


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
