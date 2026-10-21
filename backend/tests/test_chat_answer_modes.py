import asyncio
import json

from bson import ObjectId

from app.routes import chat
from app.schemas.chat_schema import ChatRequest


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _Messages:
    def __init__(self):
        self.inserted = []

    async def insert_one(self, message):
        message_id = ObjectId()
        self.inserted.append((message_id, message))
        return _InsertResult(message_id)

    def find(self, query):
        return _EmptyCursor()


class _EmptyCursor:
    def sort(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _Collection:
    def __init__(self):
        self.documents = {}

    async def find_one(self, query):
        return self.documents.get(query.get("_id"))

    async def insert_one(self, document):
        inserted_id = ObjectId()
        self.documents[inserted_id] = document
        return _InsertResult(inserted_id)


class _Database:
    def __init__(self, document_id):
        self.documents = _Collection()
        self.documents.documents[ObjectId(document_id)] = {
            "_id": ObjectId(document_id),
            "user_id": "user-1",
            "status": "ready",
            "filename": "source.pdf",
        }
        self.conversations = _Collection()
        self.messages = _Messages()


def _candidate(chunk_id, answer, similarity):
    return {
        "document_id": DOCUMENT_ID,
        "chunk_id": chunk_id,
        "page_start": 1,
        "page_end": 1,
        "section": None,
        "text": answer,
        "answer": answer,
        "similarity": similarity,
        "status": "VALIDATED",
    }


DOCUMENT_ID = str(ObjectId())
VALIDATED = [
    _candidate("best", "Best validated candidate.", 0.92),
    _candidate("second", "Second candidate.", 0.81),
]


def _install_route_mocks(monkeypatch, mode_calls):
    db = _Database(DOCUMENT_ID)
    monkeypatch.setattr(chat, "get_db", lambda: db)

    async def retrieve_candidates(document_ids, query_bundle, mode):
        mode_calls["retrieval"] += 1
        mode_calls["retrieval_mode"] = mode
        return [
            {
                "document_id": DOCUMENT_ID,
                "chunk_id": "retrieved",
                "text": "source",
                "semantic_score": 0.8,
                "page_start": 1,
                "page_end": 1,
                "section": None,
            }
        ]

    async def run_validation(question, candidates, on_progress=None):
        mode_calls["validation"] += 1
        return VALIDATED

    async def rewrite_query(question, conversation_history=None):
        mode_calls["rewrite"] += 1
        return {
            "original_query": question,
            "rewritten_queries": ["rewritten query"],
            "keywords": [],
        }

    async def synthesize_answer(question, evidence):
        mode_calls["synthesis"] += 1
        return "Traditional synthesis."

    async def synthesize_answer_stream(question, evidence):
        mode_calls["synthesis"] += 1
        yield "Traditional synthesis."

    def ground_answer(answer, evidence):
        mode_calls["ground"] += 1
        return answer, {
            "confidence": 90,
            "status": "HIGHLY_SUPPORTED",
            "hallucination_risk": 0.1,
            "verification": {"confidence_available": True},
        }

    def build_citations(document_name, evidence):
        mode_calls["citations"] += 1
        return [
            {
                "document_name": document_name,
                "page": 1,
                "chunk_id": item["chunk_id"],
                "snippet": item["text"],
            }
            for item in evidence
        ]

    monkeypatch.setattr(chat, "retrieve_candidates", retrieve_candidates)
    monkeypatch.setattr(chat, "run_carag_validation", run_validation)
    monkeypatch.setattr(chat, "rewrite_query", rewrite_query)
    monkeypatch.setattr(chat, "synthesize_answer", synthesize_answer)
    monkeypatch.setattr(chat, "synthesize_answer_stream", synthesize_answer_stream)
    monkeypatch.setattr(chat, "ground_answer", ground_answer)
    monkeypatch.setattr(chat, "build_citations", build_citations)
    return db


def _mode_payload(mode):
    return ChatRequest(
        document_ids=[DOCUMENT_ID],
        query="Question?",
        mode=mode,
    )


def test_chat_selects_best_candidate_only_for_carag_modes(monkeypatch):
    for mode in ("enhanced_carag", "carag", "traditional_rag"):
        calls = {
            "retrieval": 0,
            "retrieval_mode": None,
            "validation": 0,
            "rewrite": 0,
            "synthesis": 0,
            "ground": 0,
            "citations": 0,
        }
        _install_route_mocks(monkeypatch, calls)

        response = asyncio.run(
            chat.chat(_mode_payload(mode), {"id": "user-1"})
        )

        if mode == "traditional_rag":
            assert response["answer"] == "Traditional synthesis."
            assert calls["synthesis"] == 1
            assert calls["validation"] == 0
            assert calls["rewrite"] == 0
            assert calls["ground"] == 1
            assert calls["citations"] == 1
            assert len(response["citations"]) == 1
        elif mode == "carag":
            assert response["answer"] == "Best validated candidate."
            assert calls["synthesis"] == 0
            assert calls["validation"] == 1
            assert calls["rewrite"] == 0
            assert calls["ground"] == 0
            assert calls["citations"] == 0
            assert response["citations"] == []
            assert response["verification"] is None
        else:
            assert response["answer"] == "Traditional synthesis."
            assert calls["synthesis"] == 1
            assert calls["validation"] == 1
            assert calls["rewrite"] == 1
            assert calls["ground"] == 1
            assert calls["citations"] == 1
            assert len(response["citations"]) == 2
        assert calls["retrieval_mode"] == mode


def test_chat_stream_emits_final_candidate_and_preserves_mode_dispatch(monkeypatch):
    for mode in ("enhanced_carag", "carag", "traditional_rag"):
        calls = {
            "retrieval": 0,
            "retrieval_mode": None,
            "validation": 0,
            "rewrite": 0,
            "synthesis": 0,
            "ground": 0,
            "citations": 0,
        }
        _install_route_mocks(monkeypatch, calls)
        response = asyncio.run(
            chat.chat_stream(_mode_payload(mode), {"id": "user-1"})
        )

        async def collect():
            chunks = [chunk async for chunk in response.body_iterator]
            return "".join(
                chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                for chunk in chunks
            )

        frames = asyncio.run(collect())
        events = []
        for frame in frames.split("\n\n"):
            if not frame.startswith("event:"):
                continue
            event_line, data_line = frame.split("\n", 1)
            events.append((event_line[7:], json.loads(data_line[6:])))

        token_text = "".join(
            data["text"] for event, data in events if event == "token"
        )
        done = next(data for event, data in events if event == "done")
        expected = (
            "Best validated candidate."
            if mode == "carag"
            else "Traditional synthesis."
        )
        assert token_text == expected
        assert done["answer"] == expected
        if mode == "traditional_rag":
            assert calls["validation"] == 0
            assert calls["rewrite"] == 0
            assert calls["ground"] == 1
            assert calls["citations"] == 1
            assert len(done["citations"]) == 1
        elif mode == "carag":
            assert calls["validation"] == 1
            assert calls["rewrite"] == 0
            assert calls["ground"] == 0
            assert calls["citations"] == 0
            assert done["citations"] == []
            assert done["verification"] is None
        else:
            assert calls["validation"] == 1
            assert calls["rewrite"] == 1
            assert calls["ground"] == 1
            assert calls["citations"] == 1
            assert len(done["citations"]) == 2
        assert calls["retrieval_mode"] == mode
