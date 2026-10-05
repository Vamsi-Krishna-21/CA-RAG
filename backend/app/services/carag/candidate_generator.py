"""
Generates a candidate answer for one retrieved chunk.

The model is strictly instructed to use only the supplied chunk.
It must not use outside knowledge.

The question supplied here should preferably be the query variant
that retrieved the chunk, rather than an unnecessarily large
multi-question user request.
"""

from app.services.llm_client import generate


SYSTEM_PROMPT = (
    "Answer the question using ONLY the provided text excerpt. "
    "Do not use outside knowledge. "
    "Do not invent information that is not present in the excerpt. "
    "If the excerpt does not contain enough information to answer "
    "the question, say that the excerpt does not contain enough "
    "information."
)


async def generate_candidate_answer(
    question: str,
    chunk_text: str,
) -> str:
    """
    Generate a chunk-grounded candidate answer.
    """

    question = str(
        question or ""
    ).strip()

    chunk_text = str(
        chunk_text or ""
    ).strip()

    if not question:
        return ""

    if not chunk_text:
        return ""

    prompt = (
        "Excerpt:\n"
        f"{chunk_text}\n\n"
        "Question:\n"
        f"{question}"
    )

    answer = await generate(
        prompt,
        system=SYSTEM_PROMPT,
    )

    return str(
        answer or ""
    ).strip()