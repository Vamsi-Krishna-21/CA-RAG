import asyncio

from app.services.carag import carag_pipeline
from app.services.carag import similarity_validator


def test_validation_filters_rejected_and_ranks_candidates(monkeypatch):
    async def generate_candidate_answer(question, chunk_text):
        return f"answer for {chunk_text}"

    def validate_candidate(chunk, answer):
        status = "REJECTED" if chunk["chunk_id"] == "rejected" else "VALIDATED"
        return {
            **chunk,
            "answer": answer,
            "status": status,
            "similarity": chunk["similarity"],
        }

    monkeypatch.setattr(
        carag_pipeline,
        "generate_candidate_answer",
        generate_candidate_answer,
    )
    monkeypatch.setattr(carag_pipeline, "validate_candidate", validate_candidate)

    validated = asyncio.run(
        carag_pipeline.run_carag_validation(
            "question",
            [
                {"chunk_id": "lower", "text": "lower", "similarity": 0.7},
                {"chunk_id": "rejected", "text": "rejected", "similarity": 1.0},
                {"chunk_id": "best", "text": "best", "similarity": 0.9},
            ],
        )
    )

    assert [candidate["chunk_id"] for candidate in validated] == ["best", "lower"]
    assert carag_pipeline.select_best_validated_candidate(validated) == validated[0]
    assert carag_pipeline.select_best_validated_candidate([]) is None
    assert validated[0]["answer"] == "answer for best"


def test_candidate_generation_uses_matched_query(monkeypatch):
    captured = []

    async def generate_candidate_answer(question, chunk_text):
        captured.append((question, chunk_text))
        return "candidate answer"

    monkeypatch.setattr(
        carag_pipeline,
        "generate_candidate_answer",
        generate_candidate_answer,
    )
    monkeypatch.setattr(
        carag_pipeline,
        "validate_candidate",
        lambda chunk, answer: {**chunk, "answer": answer, "status": "VALIDATED", "similarity": 0.8},
    )

    result = asyncio.run(
        carag_pipeline.run_carag_validation(
            "original question",
            [
                {
                    "chunk_id": "chunk",
                    "text": "source",
                    "matched_query": "focused query",
                }
            ],
        )
    )

    assert captured == [("focused query", "source")]
    assert result[0]["answer"] == "candidate answer"


def test_similarity_validator_rejects_candidate_below_existing_threshold(monkeypatch):
    embeddings = {
        "candidate answer": [1.0, 0.0],
        "source text": [0.0, 1.0],
    }
    monkeypatch.setattr(
        similarity_validator,
        "embed_text",
        lambda text: embeddings[text],
    )

    result = similarity_validator.validate_candidate(
        {
            "document_id": "document",
            "chunk_id": "chunk",
            "page_start": 3,
            "page_end": 3,
            "section": "section",
            "text": "source text",
        },
        "candidate answer",
    )

    assert result["status"] == "REJECTED"
    assert result["similarity"] < similarity_validator.settings.validation_similarity_threshold
    assert result["document_id"] == "document"
    assert result["chunk_id"] == "chunk"
    assert result["page_start"] == 3
