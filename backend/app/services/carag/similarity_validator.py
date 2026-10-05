"""
Validates a candidate answer against the source chunk.

The candidate answer is embedded and compared with the source chunk
using cosine similarity.

The validator preserves the complete source metadata so downstream
evidence synthesis and citation generation can identify the exact
document and chunk from which the evidence originated.
"""

from app.config import settings
from app.services.embeddings import embed_text
from app.utils.similarity import cosine_similarity


def validate_candidate(
    chunk: dict,
    candidate_answer: str,
) -> dict:
    """
    Validate one candidate answer against its source chunk.

    Returns the validation result together with all important source
    metadata required by downstream CA-RAG stages.
    """

    chunk_text = str(
        chunk.get("text", "")
        or ""
    ).strip()

    candidate_answer = str(
        candidate_answer or ""
    ).strip()

    # ---------------------------------------------------------------
    # Empty content cannot be valid evidence.
    # ---------------------------------------------------------------

    if not chunk_text or not candidate_answer:
        return {
            "document_id":
                chunk.get("document_id"),

            "chunk_id":
                chunk.get("chunk_id"),

            "matched_query":
                chunk.get("matched_query"),

            "answer":
                candidate_answer,

            "similarity":
                0.0,

            "status":
                "REJECTED",

            "retrieval_score":
                chunk.get(
                    "retrieval_score"
                ),

            "semantic_score":
                chunk.get(
                    "semantic_score"
                ),

            "page_start":
                chunk.get(
                    "page_start"
                ),

            "page_end":
                chunk.get(
                    "page_end"
                ),

            "section":
                chunk.get(
                    "section"
                ),

            "text":
                chunk_text,
        }

    # ---------------------------------------------------------------
    # Embed candidate answer and source chunk.
    # ---------------------------------------------------------------

    answer_embedding = embed_text(
        candidate_answer
    )

    chunk_embedding = embed_text(
        chunk_text
    )

    similarity = cosine_similarity(
        answer_embedding,
        chunk_embedding,
    )

    similarity = float(
        similarity
    )

    threshold = float(
        settings.validation_similarity_threshold
    )

    status = (
        "VALIDATED"
        if similarity >= threshold
        else "REJECTED"
    )

    # ---------------------------------------------------------------
    # Preserve ALL retrieval/source metadata.
    # ---------------------------------------------------------------

    return {
        "document_id":
            chunk.get("document_id"),

        "chunk_id":
            chunk.get("chunk_id"),

        "matched_query":
            chunk.get("matched_query"),

        "answer":
            candidate_answer,

        "similarity":
            round(
                similarity,
                4,
            ),

        "status":
            status,

        "retrieval_score":
            chunk.get(
                "retrieval_score"
            ),

        "semantic_score":
            chunk.get(
                "semantic_score"
            ),

        "page_start":
            chunk.get(
                "page_start"
            ),

        "page_end":
            chunk.get(
                "page_end"
            ),

        "section":
            chunk.get(
                "section"
            ),

        "text":
            chunk_text,
    }