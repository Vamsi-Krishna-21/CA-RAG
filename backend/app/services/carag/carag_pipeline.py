"""
CA-RAG validation pipeline.

Pipeline:

candidate chunks
        ↓
generate a candidate answer for each chunk
        ↓
validate candidate answer against its source chunk
        ↓
keep only VALIDATED evidence
        ↓
strongest evidence first

For multi-document retrieval, every candidate can contain
"matched_query".

That query is used for candidate generation so that a chunk
retrieved for a focused rewritten query is not incorrectly asked
to answer the entire original multi-question request.
"""

import asyncio

from app.config import settings

from app.services.carag.candidate_generator import (
    generate_candidate_answer,
)

from app.services.carag.similarity_validator import (
    validate_candidate,
)


async def run_carag_validation(
    question: str,
    candidate_chunks: list,
    on_progress=None,
) -> list:
    """
    Generate and validate candidate answers.

    Parameters
    ----------
    question:
        Original user question.

    candidate_chunks:
        Retrieved candidate chunks.

    on_progress:
        Optional callback receiving:
            done, total

    Returns
    -------
    list[dict]
        Only validated evidence, sorted by similarity descending.
    """

    total = len(
        candidate_chunks
    )

    if total == 0:
        return []

    concurrency = max(
        1,
        int(
            settings.carag_validation_concurrency
        ),
    )

    semaphore = asyncio.Semaphore(
        concurrency
    )

    done = 0

    async def process_chunk(
        chunk: dict,
    ) -> dict:
        nonlocal done

        async with semaphore:

            # -------------------------------------------------------
            # IMPORTANT:
            #
            # If the retriever found this chunk using a rewritten
            # query, use that focused query.
            #
            # Otherwise fall back to the original question.
            # -------------------------------------------------------

            focused_question = (
                chunk.get(
                    "matched_query"
                )
                or question
            )

            candidate_answer = (
                await generate_candidate_answer(
                    focused_question,
                    chunk.get(
                        "text",
                        "",
                    ),
                )
            )

        result = validate_candidate(
            chunk,
            candidate_answer,
        )

        done += 1

        if on_progress is not None:
            on_progress(
                done,
                total,
            )

        return result

    # ---------------------------------------------------------------
    # Process candidates concurrently.
    # ---------------------------------------------------------------

    results = await asyncio.gather(
        *(
            process_chunk(
                chunk
            )
            for chunk in candidate_chunks
        )
    )

    # ---------------------------------------------------------------
    # Keep only validated evidence.
    # ---------------------------------------------------------------

    validated = [
        result
        for result in results
        if result.get(
            "status"
        ) == "VALIDATED"
    ]

    # ---------------------------------------------------------------
    # Strongest evidence first.
    # ---------------------------------------------------------------

    validated.sort(
        key=lambda result:
            float(
                result.get(
                    "similarity",
                    0.0,
                )
                or 0.0
            ),
        reverse=True,
    )

    return validated