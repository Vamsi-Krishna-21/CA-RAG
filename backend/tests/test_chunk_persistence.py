import asyncio
import os
import tempfile
import numpy as np
import pytest
from bson import Binary, ObjectId

from app.models.document import new_chunk_doc
from app.services import vector_store
from app.services.retrieval import retriever
from app.routes import documents


class _FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, str):
            reverse = direction == -1
            self.items.sort(key=lambda x: x.get(key_or_list, 0), reverse=reverse)
        return self

    def __aiter__(self):
        self._iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _MockCollection:
    def __init__(self, data=None):
        self.data = list(data or [])
        self.deleted_queries = []
        self.inserted_docs = []

    def find(self, query=None, projection=None):
        query = query or {}
        matches = []
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                matches.append(item)
        return _FakeCursor(matches)

    async def find_one(self, query):
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return item
        return None

    async def insert_many(self, docs, ordered=True):
        self.inserted_docs.extend(docs)
        self.data.extend(docs)
        return type("InsertManyResult", (), {"inserted_ids": [d.get("_id", ObjectId()) for d in docs]})()

    async def delete_many(self, filter_query):
        self.deleted_queries.append(filter_query)
        initial_len = len(self.data)
        self.data = [
            item for item in self.data
            if not all(item.get(k) == v for k, v in filter_query.items())
        ]
        return type("DeleteResult", (), {"deleted_count": initial_len - len(self.data)})()

    async def update_one(self, filter_query, update_doc):
        for item in self.data:
            match = True
            for k, v in filter_query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                if "$set" in update_doc:
                    item.update(update_doc["$set"])
                return type("UpdateResult", (), {"modified_count": 1})()
        return type("UpdateResult", (), {"modified_count": 0})()

    async def create_index(self, keys, **kwargs):
        return "index_created"


class _MockDB:
    def __init__(self):
        self.documents = _MockCollection()
        self.chunks = _MockCollection()
        self.messages = _MockCollection()
        self.conversations = _MockCollection()
        self.feedback = _MockCollection()


def test_embedding_binary_serialization_is_lossless():
    rng = np.random.RandomState(42)
    raw = rng.randn(5, 384).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    original_embeddings = raw / norms

    for i in range(len(original_embeddings)):
        vec = original_embeddings[i]
        b = vec.tobytes()
        assert len(b) == 1536
        binary_obj = Binary(b)
        restored = np.frombuffer(binary_obj, dtype=np.float32)
        assert np.array_equal(vec, restored)


def test_faiss_reconstructed_search_invariance():
    import faiss

    rng = np.random.RandomState(123)
    raw = rng.randn(8, 384).astype(np.float32)
    embeddings = raw / np.linalg.norm(raw, axis=1, keepdims=True)

    query = rng.randn(1, 384).astype(np.float32)
    query = query / np.linalg.norm(query)

    # 1. Original FAISS index
    orig_index = faiss.IndexFlatIP(384)
    orig_index.add(embeddings)
    orig_scores, orig_idxs = orig_index.search(query, 5)

    # 2. Serialize to bytes as stored in MongoDB
    serialized_chunks = [embeddings[i].tobytes() for i in range(len(embeddings))]

    # 3. Reconstruct FAISS index from deserialized bytes
    restored_vectors = [np.frombuffer(b, dtype=np.float32) for b in serialized_chunks]
    restored_embeddings = np.vstack(restored_vectors).astype(np.float32)

    recon_index = faiss.IndexFlatIP(384)
    recon_index.add(restored_embeddings)
    recon_scores, recon_idxs = recon_index.search(query, 5)

    assert np.array_equal(orig_idxs, recon_idxs)
    assert np.allclose(orig_scores, recon_scores, atol=1e-7)


def test_ensure_document_index_hydrates_when_files_missing(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = vector_store.settings.vector_store_dir
        vector_store.settings.vector_store_dir = tmpdir
        try:
            doc_id = str(ObjectId())
            doc_oid = ObjectId(doc_id)

            rng = np.random.RandomState(42)
            raw = rng.randn(3, 384).astype(np.float32)
            embs = raw / np.linalg.norm(raw, axis=1, keepdims=True)

            db = _MockDB()
            db.documents.data.append({
                "_id": doc_oid,
                "status": "ready",
                "chunk_count": 3,
            })
            for i in range(3):
                db.chunks.data.append({
                    "document_id": doc_id,
                    "chunk_id": f"c_{i}",
                    "chunk_index": i,
                    "text": f"Chunk text {i}",
                    "page_start": i + 1,
                    "page_end": i + 1,
                    "section": "Section",
                    "embedding": Binary(embs[i].tobytes()),
                })

            monkeypatch.setattr(vector_store, "get_db", lambda: db)

            index_path, meta_path = vector_store._paths(doc_id)
            assert not os.path.exists(index_path)
            assert not os.path.exists(meta_path)

            success = asyncio.run(vector_store.ensure_document_index(doc_id))
            assert success is True

            assert os.path.exists(index_path)
            assert os.path.exists(meta_path)

            idx, meta = vector_store.load_document_index(doc_id)
            assert idx is not None
            assert len(meta) == 3
            assert meta[0]["chunk_id"] == "c_0"
            assert meta[2]["chunk_id"] == "c_2"
        finally:
            vector_store.settings.vector_store_dir = original_dir


def test_ensure_document_index_rejects_non_contiguous_chunks(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = vector_store.settings.vector_store_dir
        vector_store.settings.vector_store_dir = tmpdir
        try:
            doc_id = str(ObjectId())
            doc_oid = ObjectId(doc_id)

            db = _MockDB()
            db.documents.data.append({
                "_id": doc_oid,
                "status": "ready",
                "chunk_count": 3,
            })
            # Indices are 0, 2, 3 (index 1 is missing)
            rng = np.random.RandomState(42)
            for idx in [0, 2, 3]:
                vec = rng.randn(384).astype(np.float32)
                db.chunks.data.append({
                    "document_id": doc_id,
                    "chunk_id": f"c_{idx}",
                    "chunk_index": idx,
                    "text": f"Text {idx}",
                    "embedding": Binary(vec.tobytes()),
                })

            monkeypatch.setattr(vector_store, "get_db", lambda: db)

            success = asyncio.run(vector_store.ensure_document_index(doc_id))
            assert success is False

            index_path, meta_path = vector_store._paths(doc_id)
            assert not os.path.exists(index_path)
        finally:
            vector_store.settings.vector_store_dir = original_dir


def test_ensure_document_index_rejects_unready_document(monkeypatch):
    doc_id = str(ObjectId())
    doc_oid = ObjectId(doc_id)

    db = _MockDB()
    db.documents.data.append({
        "_id": doc_oid,
        "status": "processing",
        "chunk_count": 2,
    })
    monkeypatch.setattr(vector_store, "get_db", lambda: db)

    success = asyncio.run(vector_store.ensure_document_index(doc_id))
    assert success is False


def test_concurrent_hydration_is_safe(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = vector_store.settings.vector_store_dir
        vector_store.settings.vector_store_dir = tmpdir
        try:
            doc_id = str(ObjectId())
            doc_oid = ObjectId(doc_id)

            rng = np.random.RandomState(99)
            raw = rng.randn(4, 384).astype(np.float32)
            embs = raw / np.linalg.norm(raw, axis=1, keepdims=True)

            db = _MockDB()
            db.documents.data.append({
                "_id": doc_oid,
                "status": "ready",
                "chunk_count": 4,
            })
            for i in range(4):
                db.chunks.data.append({
                    "document_id": doc_id,
                    "chunk_id": f"c_{i}",
                    "chunk_index": i,
                    "text": f"Chunk text {i}",
                    "page_start": 1,
                    "page_end": 1,
                    "section": "Sec",
                    "embedding": Binary(embs[i].tobytes()),
                })

            monkeypatch.setattr(vector_store, "get_db", lambda: db)

            async def run_parallel():
                tasks = [vector_store.ensure_document_index(doc_id) for _ in range(8)]
                return await asyncio.gather(*tasks)

            results = asyncio.run(run_parallel())
            assert all(r is True for r in results)

            idx, meta = vector_store.load_document_index(doc_id)
            assert idx is not None
            assert len(meta) == 4
        finally:
            vector_store.settings.vector_store_dir = original_dir


def test_retriever_ensures_index_before_searching(monkeypatch):
    ensured_docs = []

    async def fake_ensure(document_id):
        ensured_docs.append(document_id)
        return True

    monkeypatch.setattr(retriever.vector_store, "ensure_document_index", fake_ensure)
    monkeypatch.setattr(retriever, "embed_text", lambda _q: np.ones(384, dtype=np.float32))
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda doc_id, _q, **_k: [
            {
                "chunk_id": f"c_{doc_id}",
                "text": "text",
                "semantic_score": 0.8,
            }
        ],
    )

    results = asyncio.run(
        retriever.retrieve_candidates(
            ["doc-1", "doc-2"],
            {"original_query": "hello", "keywords": []},
            mode="traditional_rag",
        )
    )

    assert set(ensured_docs) == {"doc-1", "doc-2"}
    assert len(results) == 2
