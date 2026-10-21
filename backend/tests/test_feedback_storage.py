import asyncio

import pytest
from bson import ObjectId

from app.routes import feedback
from app.schemas.chat_schema import FeedbackRequest


class _Messages:
    def __init__(self, message_id, content):
        self.message_id = message_id
        self.content = content

    async def find_one(self, query):
        if (
            query.get("_id") == self.message_id
            and query.get("user_id") == "user"
            and query.get("role") == "assistant"
        ):
            return {"content": self.content}
        return None


class _Feedback:
    def __init__(self):
        self.records = []

    async def insert_one(self, document):
        self.records.append(document)


class _Database:
    def __init__(self, message_id):
        self.messages = _Messages(
            message_id,
            {"evidence": [{"chunk_id": "chunk"}], "citations": []},
        )
        self.feedback = _Feedback()


@pytest.mark.parametrize("mode", ["traditional_rag", "carag", "enhanced_carag"])
def test_feedback_storage_remains_available_independent_of_mode(monkeypatch, mode):
    message_id = ObjectId()
    db = _Database(message_id)
    monkeypatch.setattr(feedback, "get_db", lambda: db)

    result = asyncio.run(
        feedback.submit_feedback(
            FeedbackRequest(
                message_id=str(message_id),
                rating="positive",
                used_chunks=["chunk"],
            ),
            {"id": "user"},
        )
    )

    assert result == {"detail": "Feedback recorded"}
    assert len(db.feedback.records) == 1
    assert db.feedback.records[0]["rating"] == "positive"
    assert db.feedback.records[0]["used_chunks"] == ["chunk"]
