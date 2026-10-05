"""
Retrieves candidate chunks for a query (+ its rewrites) from the FAISS
indexes of one or more documents, ranks them globally, and returns
the top N.

These are CANDIDATES ONLY -- CA-RAG validation decides which candidates
actually count as evidence.

Supports:
- Single-document retrieval
- Multi-document retrieval
- Original query + rewritten queries
- Keyword scoring
- Feedback-based ranking
- Global ranking across all selected documents
- Preserving the query variant that matched each chunk
"""

from app.services.embeddings import embed_text
from app.services import vector_store
from app.services.retrieval.ranking import (
    keyword_score,
    combine_scores,
)
from app.services.feedback.feedback_learning import (
    get_feedback_boost,
)


async def retrieve_candidates(
    document_ids: str | list[str],
    query_bundle: dict,
    top_k: int = 12,
):
    """
    Retrieve candidate chunks from one or more documents.

    Parameters
    ----------
    document_ids:
        A single document ID or a list of document IDs.

    query_bundle:
        Contains:
        - original_query
        - rewritten_queries
        - keywords

    top_k:
        Maximum number of candidates returned globally.

    Returns
    -------
    list[dict]
        Globally ranked candidate chunks from all selected documents.

    Each candidate preserves:
        - document_id
        - chunk_id
        - matched_query
        - semantic_score
        - retrieval_score
        - page information
        - section
        - text
    """

    # ------------------------------------------------------------------
    # Normalize document IDs
    # ------------------------------------------------------------------

    if isinstance(document_ids, str):
        document_ids = [document_ids]

    document_ids = list(
        dict.fromkeys(
            str(document_id)
            for document_id in document_ids
            if document_id
        )
    )

    if not document_ids:
        return []

    # ------------------------------------------------------------------
    # Build query variants
    # ------------------------------------------------------------------

    original_query = (
        query_bundle.get("original_query")
        or ""
    ).strip()

    rewritten_queries = [
        str(query).strip()
        for query in (
            query_bundle.get(
                "rewritten_queries",
                [],
            )
            or []
        )
        if str(query).strip()
    ]

    all_queries = []

    if original_query:
        all_queries.append(
            original_query
        )

    all_queries.extend(
        rewritten_queries
    )

    # Remove duplicate queries while preserving order.
    all_queries = list(
        dict.fromkeys(all_queries)
    )

    if not all_queries:
        return []

    keywords = (
        query_bundle.get(
            "keywords",
            [],
        )
        or []
    )

    # ------------------------------------------------------------------
    # Retrieval state
    # ------------------------------------------------------------------

    seen = {}

    boost_cache = {}

    # ------------------------------------------------------------------
    # Search every query against every selected document
    # ------------------------------------------------------------------

    for query in all_queries:

        # Embed each query only once.
        query_embedding = embed_text(
            query
        )

        for document_id in document_ids:

            results = vector_store.search(
                document_id,
                query_embedding,
                top_k=top_k,
            )

            if not results:
                continue

            for result in results:

                # Make a copy so that modifying the result does not
                # unexpectedly mutate a vector-store object.
                candidate = dict(
                    result
                )

                # ------------------------------------------------------
                # Source document
                # ------------------------------------------------------

                candidate[
                    "document_id"
                ] = document_id

                # ------------------------------------------------------
                # IMPORTANT:
                # Remember which query variant retrieved this chunk.
                # ------------------------------------------------------

                candidate[
                    "matched_query"
                ] = query

                # ------------------------------------------------------
                # Keyword relevance
                # ------------------------------------------------------

                keyword_relevance = (
                    keyword_score(
                        candidate.get(
                            "text",
                            "",
                        ),
                        keywords,
                    )
                )

                # ------------------------------------------------------
                # Feedback boost
                # ------------------------------------------------------

                chunk_id = candidate.get(
                    "chunk_id"
                )

                if not chunk_id:
                    continue

                boost_key = (
                    document_id,
                    chunk_id,
                )

                if (
                    boost_key
                    not in boost_cache
                ):
                    boost_cache[
                        boost_key
                    ] = await get_feedback_boost(
                        chunk_id
                    )

                feedback_boost = (
                    boost_cache[
                        boost_key
                    ]
                )

                # ------------------------------------------------------
                # Combined retrieval score
                # ------------------------------------------------------

                semantic_score = float(
                    candidate.get(
                        "semantic_score",
                        0.0,
                    )
                    or 0.0
                )

                candidate[
                    "retrieval_score"
                ] = combine_scores(
                    semantic_score,
                    keyword_relevance,
                    feedback_boost,
                )

                # ------------------------------------------------------
                # Deduplicate by document + chunk.
                #
                # A chunk can be retrieved by:
                #   - original query
                #   - rewritten query 1
                #   - rewritten query 2
                #   - etc.
                #
                # Keep the highest scoring occurrence and therefore
                # preserve the query variant responsible for that score.
                # ------------------------------------------------------

                candidate_key = (
                    document_id,
                    chunk_id,
                )

                existing = seen.get(
                    candidate_key
                )

                if (
                    existing is None
                    or candidate[
                        "retrieval_score"
                    ]
                    > existing[
                        "retrieval_score"
                    ]
                ):
                    seen[
                        candidate_key
                    ] = candidate

    # ------------------------------------------------------------------
    # Global ranking across ALL selected documents
    # ------------------------------------------------------------------

    ranked = sorted(
        seen.values(),
        key=lambda candidate:
            candidate.get(
                "retrieval_score",
                0.0,
            ),
        reverse=True,
    )

    # ------------------------------------------------------------------
    # Return global top-k candidates
    # ------------------------------------------------------------------

    return ranked[:top_k]