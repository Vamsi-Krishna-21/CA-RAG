import asyncio

from app.services.query import query_rewriter


class FakeGenerate:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    async def __call__(self, prompt, system, json_mode):
        self.prompts.append((prompt, system, json_mode))
        return self.response


def test_rewrite_query_uses_recent_conversation_context(monkeypatch):
    generate = FakeGenerate(
        '{"rewritten_queries": ["What are the advantages of adaptive chunking?"], '
        '"keywords": ["adaptive chunking", "advantages"]}'
    )
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query(
            "What are its advantages?",
            conversation_history=[
                {"role": "user", "content": {"query": "Explain adaptive chunking."}},
                {
                    "role": "assistant",
                    "content": {"answer": "Adaptive chunking determines boundaries."},
                },
            ],
        )
    )

    prompt, system, json_mode = generate.prompts[0]
    assert "Conversation history:" in prompt
    assert "Explain adaptive chunking." in prompt
    assert "Current user question: What are its advantages?" in prompt
    assert "Previous conversation" in system
    assert json_mode is True
    assert result["original_query"] == "What are its advantages?"
    assert result["rewritten_queries"] == [
        "What are the advantages of adaptive chunking?"
    ]


def test_rewrite_query_without_history_preserves_existing_behavior(monkeypatch):
    generate = FakeGenerate(
        '{"rewritten_queries": ["What is adaptive chunking?"], '
        '"keywords": ["adaptive chunking"]}'
    )
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query("What is adaptive chunking?")
    )

    assert "Conversation history:\nNone" in generate.prompts[0][0]
    assert result == {
        "original_query": "What is adaptive chunking?",
        "rewritten_queries": ["What is adaptive chunking?"],
        "keywords": ["adaptive chunking"],
    }


def test_rewrite_query_ignores_malformed_history(monkeypatch):
    generate = FakeGenerate(
        '{"rewritten_queries": ["What is MongoDB?"], "keywords": ["MongoDB"]}'
    )
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query(
            "What is MongoDB?",
            conversation_history=[
                None,
                {"role": "user"},
                {"content": "ignored"},
            ],
        )
    )

    assert "Conversation history:\nNone" in generate.prompts[0][0]
    assert result["rewritten_queries"] == ["What is MongoDB?"]


def test_rewrite_query_handles_invalid_json(monkeypatch):
    generate = FakeGenerate("not valid json")
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query(
            "What are its limitations?",
            conversation_history=[
                {"role": "user", "content": {"query": "Explain adaptive chunking."}}
            ],
        )
    )

    assert result == {
        "original_query": "What are its limitations?",
        "rewritten_queries": [],
        "keywords": ["what", "are", "its", "limitations?"],
    }


def test_rewrite_query_limits_alternatives(monkeypatch):
    generate = FakeGenerate(
        '{"rewritten_queries": ["one", "two", "three", "four"], '
        '"keywords": ["one"]}'
    )
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query("What is adaptive chunking?")
    )

    assert result["rewritten_queries"] == ["one", "two", "three"]


def test_rewrite_query_does_not_hallucinate_unrelated_context(monkeypatch):
    generate = FakeGenerate(
        '{"rewritten_queries": ["What is MongoDB?"], "keywords": ["MongoDB"]}'
    )
    monkeypatch.setattr(query_rewriter, "generate", generate)

    result = asyncio.run(
        query_rewriter.rewrite_query(
            "What is MongoDB?",
            conversation_history=[
                {
                    "role": "user",
                    "content": {"query": "Explain adaptive chunking."},
                },
                {
                    "role": "assistant",
                    "content": {"answer": "Adaptive chunking is dynamic."},
                },
            ],
        )
    )

    assert result["rewritten_queries"] == ["What is MongoDB?"]
    assert result["keywords"] == ["MongoDB"]
