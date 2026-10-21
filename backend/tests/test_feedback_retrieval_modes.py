import asyncio

import pytest

from app.services.retrieval import retriever


def _search_results():
    return [
        {
            "chunk_id": "semantic-best",
            "text": "first",
            "semantic_score": 0.8,
        },
        {
            "chunk_id": "feedback-best",
            "text": "second",
            "semantic_score": 0.7,
        },
    ]


@pytest.mark.parametrize("mode", ["traditional_rag", "carag"])
def test_non_enhanced_modes_do_not_read_feedback_or_apply_boost(monkeypatch, mode):
    calls = []
    monkeypatch.setattr(retriever, "embed_text", lambda _query: [1.0])
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda *_args, **_kwargs: _search_results(),
    )

    async def get_feedback_boost(chunk_id):
        calls.append(chunk_id)
        return 0.15

    monkeypatch.setattr(retriever, "get_feedback_boost", get_feedback_boost)

    results = asyncio.run(
        retriever.retrieve_candidates(
            ["document"],
            {"original_query": "query", "keywords": []},
            mode=mode,
        )
    )

    assert calls == []
    assert [result["chunk_id"] for result in results] == [
        "semantic-best",
        "feedback-best",
    ]
    assert [result["retrieval_score"] for result in results] == pytest.approx(
        [0.56, 0.49]
    )


def test_enhanced_mode_applies_feedback_boost_to_ranking(monkeypatch):
    calls = []
    monkeypatch.setattr(retriever, "embed_text", lambda _query: [1.0])
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda *_args, **_kwargs: _search_results(),
    )

    async def get_feedback_boost(chunk_id):
        calls.append(chunk_id)
        return 0.15 if chunk_id == "feedback-best" else 0.0

    monkeypatch.setattr(retriever, "get_feedback_boost", get_feedback_boost)

    results = asyncio.run(
        retriever.retrieve_candidates(
            ["document"],
            {"original_query": "query", "keywords": []},
            mode="enhanced_carag",
        )
    )

    assert calls == ["semantic-best", "feedback-best"]
    assert [result["chunk_id"] for result in results] == [
        "feedback-best",
        "semantic-best",
    ]
    assert [result["retrieval_score"] for result in results] == pytest.approx(
        [0.64, 0.56]
    )


def test_enhanced_mode_alias_enables_feedback_boost(monkeypatch):
    calls = []
    monkeypatch.setattr(retriever, "embed_text", lambda _query: [1.0])
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda *_args, **_kwargs: [_search_results()[0]],
    )

    async def get_feedback_boost(chunk_id):
        calls.append(chunk_id)
        return 0.1

    monkeypatch.setattr(retriever, "get_feedback_boost", get_feedback_boost)

    asyncio.run(
        retriever.retrieve_candidates(
            ["document"],
            {"original_query": "query", "keywords": []},
            mode="enhance_ca_rag",
        )
    )

    assert calls == ["semantic-best"]
