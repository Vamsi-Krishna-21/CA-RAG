import asyncio
import os
import tempfile
import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routes import chat, documents
from app.schemas.chat_schema import ChatRequest
from app.services import vector_store
from app.services.ingestion import document_loader


class _FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, *_args):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


class _MockCollection:
    def __init__(self, data=None):
        self.data = list(data or [])
        self.pulled = []
        self.deleted_queries = []

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

    async def update_many(self, filter_query, update_doc):
        if "$pull" in update_doc:
            self.pulled.append((filter_query, update_doc["$pull"]))
        return type("UpdateResult", (), {"modified_count": 1})()

    async def delete_many(self, filter_query):
        self.deleted_queries.append(filter_query)
        return type("DeleteResult", (), {"deleted_count": 1})()

    async def delete_one(self, filter_query):
        self.deleted_queries.append(filter_query)
        return type("DeleteResult", (), {"deleted_count": 1})()


class _MockDB:
    def __init__(self):
        self.messages = _MockCollection()
        self.conversations = _MockCollection()
        self.documents = _MockCollection()
        self.feedback = _MockCollection()
        self.chunks = _MockCollection()


def test_invalid_conversation_id_raises_400():
    db = _MockDB()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            chat._get_or_create_conversation(
                db,
                current_user={"id": "user-123"},
                payload=ChatRequest(
                    query="hello",
                    mode="carag",
                    conversation_id="invalid-not-an-objectid",
                ),
                document_ids=["doc-1"],
            )
        )
    assert exc_info.value.status_code == 400
    assert "Invalid conversation ID" in exc_info.value.detail


def test_vector_store_missing_json_returns_none_cleanly():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = vector_store.settings.vector_store_dir
        vector_store.settings.vector_store_dir = tmpdir
        try:
            doc_id = "test_doc_without_json"
            # Create ONLY .index file, leave .json missing
            index_path = os.path.join(tmpdir, f"{doc_id}.index")
            with open(index_path, "wb") as f:
                f.write(b"mock index")

            # Must return (None, []) cleanly instead of raising FileNotFoundError on .json
            index, meta = vector_store.load_document_index(doc_id)
            assert index is None
            assert meta == []
        finally:
            vector_store.settings.vector_store_dir = original_dir


def test_chat_history_requires_either_document_or_conversation():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            chat.chat_history(
                document_id=None,
                conversation_id=None,
                current_user={"id": "user-1"},
            )
        )
    assert exc_info.value.status_code == 400


def test_chat_history_scopes_to_conversation_or_unthreaded(monkeypatch):
    db = _MockDB()
    monkeypatch.setattr(chat, "get_db", lambda: db)

    # 1. With conversation_id
    asyncio.run(
        chat.chat_history(
            document_id="doc-1",
            conversation_id="conv-123",
            current_user={"id": "user-1"},
        )
    )

    # 2. Without conversation_id (should filter conversation_id: None)
    captured_queries = []
    original_find = db.messages.find

    def tracked_find(query=None, projection=None):
        captured_queries.append(query)
        return original_find(query, projection)

    db.messages.find = tracked_find

    asyncio.run(
        chat.chat_history(
            document_id="doc-1",
            conversation_id=None,
            current_user={"id": "user-1"},
        )
    )

    assert len(captured_queries) == 1
    assert captured_queries[0]["conversation_id"] is None
    assert captured_queries[0]["document_id"] == "doc-1"


def test_delete_document_cascades_to_conversations(monkeypatch):
    db = _MockDB()
    doc_id = str(ObjectId())
    doc_oid = ObjectId(doc_id)
    db.documents.data.append({
        "_id": doc_oid,
        "user_id": "user-1",
        "filepath": "/nonexistent/path/doc.pdf",
    })
    monkeypatch.setattr(documents, "get_db", lambda: db)

    res = asyncio.run(
        documents.delete_document(doc_id, current_user={"id": "user-1"})
    )
    assert res == {"detail": "Document deleted"}

    # Verify conversation references were pulled
    pulled_ops = [pull for filter_q, pull in db.conversations.pulled]
    assert any("document_ids" in pull and pull["document_ids"] == doc_id for pull in pulled_ops)

    # Verify empty conversations cleanup was triggered
    deleted_ops = db.conversations.deleted_queries
    assert any("document_ids" in q and q["document_ids"] == {"$size": 0} for q in deleted_ops)


def test_document_loader_missing_libreoffice(monkeypatch):
    monkeypatch.setattr(document_loader, "LIBREOFFICE_PATH", r"C:\NonExistent\soffice.exe")
    with pytest.raises(RuntimeError) as exc_info:
        document_loader._convert_ppt_to_pptx("sample.ppt")
    assert "LibreOffice was not found" in str(exc_info.value)
