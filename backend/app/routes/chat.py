import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId

from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.database.mongodb import get_db
from app.auth.authentication import get_current_user, parse_object_id
from app.models.conversation import new_message_doc, new_conversation_doc
from app.services.query.query_rewriter import rewrite_query
from app.services.retrieval.retriever import retrieve_candidates
from app.services.carag.carag_pipeline import run_carag_validation
from app.services.synthesis.evidence_synthesis import (
    synthesize_answer,
    synthesize_answer_stream,
)
from app.services.hallucination.detector import analyze
from app.services.citation.citation_generator import (
    build_citations,
    build_evidence_list,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])

async def _get_or_create_conversation(
    db,
    current_user: dict,
    payload,
    document_ids: list[str],
):
    user_id = current_user["id"]

    # Existing conversation
    if payload.conversation_id:
        conversation = await db.conversations.find_one(
            {
                "_id": ObjectId(payload.conversation_id),
                "user_id": user_id,
            }
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        return conversation

    # Create a new conversation for the first message
    title = payload.query.strip()
    if len(title) > 80:
        title = title[:77] + "..."

    conversation = new_conversation_doc(
        user_id=user_id,
        title=title or "New chat",
        document_ids=document_ids,
    )

    result = await db.conversations.insert_one(conversation)
    conversation["_id"] = result.inserted_id

    return conversation


# ---------------------------------------------------------------------------
# Normal POST /api/chat
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    # Preserve the conversation context that the frontend sends, while still
    # supporting the legacy single-document request format.
    target_document_ids = list(payload.document_ids or [])
    if not target_document_ids and payload.document_id:
        target_document_ids = [payload.document_id]

    if not target_document_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one document is required.",
        )

    documents = []
    document_ids = []
    for document_id in target_document_ids:
        doc_oid = parse_object_id(document_id)
        if not doc_oid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document ID: {document_id}",
            )

        doc = await db.documents.find_one({"_id": doc_oid})
        if not doc or doc["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {document_id}",
            )
        if doc["status"] != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"Document is still {doc['status']}",
            )
        document_ids.append(str(doc["_id"]))
        documents.append(doc)

    primary_document_id = document_ids[0]
    conversation = await _get_or_create_conversation(
        db,
        current_user,
        payload,
        document_ids,
    )
    conversation_id = str(conversation["_id"])

    # Save user message.
    await db.messages.insert_one(
        new_message_doc(
            current_user["id"],
            primary_document_id,
            "user",
            {
                "query": payload.query,
                "document_ids": document_ids,
            },
            conversation_id=conversation_id,
        )
    )

    # ------------------------------------------------------------------
    # Traditional RAG
    # ------------------------------------------------------------------

    if payload.mode == "traditional":
        # Plain retrieval -> LLM -> answer.
        # No query rewriting.
        # No CA-RAG validation gate.
        query_bundle = {
            "original_query": payload.query,
            "rewritten_queries": [],
            "keywords": [],
        }

        candidates = await retrieve_candidates(
            document_ids,
            query_bundle,
        )

        validated = [
            {
                **c,
                "similarity": c["semantic_score"],
                "status": "VALIDATED",
            }
            for c in candidates[:5]
        ]

        rewritten_queries = []

    # ------------------------------------------------------------------
    # Full CA-RAG
    # ------------------------------------------------------------------

    else:
        # Query rewriting.
        query_bundle = await rewrite_query(payload.query)

        rewritten_queries = query_bundle.get(
            "rewritten_queries",
            [],
        )

        # Retrieval.
        candidates = await retrieve_candidates(
            document_ids,
            query_bundle,
        )

        # CA-RAG candidate generation + similarity validation.
        validated = await run_carag_validation(
            payload.query,
            candidates,
        )

    # ------------------------------------------------------------------
    # Evidence synthesis
    # ------------------------------------------------------------------

    answer = await synthesize_answer(
        payload.query,
        validated,
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    analysis = analyze(
        answer,
        validated,
    )

    # ------------------------------------------------------------------
    # Citations and evidence
    # ------------------------------------------------------------------

    citations = []
    for document in documents:
        document_candidates = [
            candidate
            for candidate in validated
            if candidate.get("document_id") == str(document["_id"])
        ]
        if document_candidates:
            citations.extend(
                build_citations(
                    document["filename"],
                    document_candidates,
                )
            )

    evidence = build_evidence_list(
        validated,
    )

    # ------------------------------------------------------------------
    # Final response
    # ------------------------------------------------------------------

    response = ChatResponse(
        answer=answer,
        confidence=analysis["confidence"],
        status=analysis["status"],
        hallucination_risk=analysis["hallucination_risk"],
        citations=citations,
        evidence=evidence,
        mode=payload.mode,
        verification=analysis.get("verification"),
        conversation_id=conversation_id,
        rewritten_queries=rewritten_queries,
    )

    # Save assistant response.
    saved = await db.messages.insert_one(
        new_message_doc(
            current_user["id"],
            primary_document_id,
            "assistant",
            response.model_dump(),
            conversation_id=conversation_id,
        )
    )

    response_dict = response.model_dump()
    response_dict["message_id"] = str(saved.inserted_id)
    return response_dict


# ---------------------------------------------------------------------------
# Streaming variant of POST /api/chat
#
# Same CA-RAG pipeline:
#
# rewrite
#     ↓
# retrieve
#     ↓
# CA-RAG validation
#     ↓
# evidence synthesis
#     ↓
# hallucination detection / confidence
#     ↓
# citations / evidence
#
# Difference:
# The final synthesis answer is streamed token by token.
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_PING_INTERVAL = 10.0


def _sse(event: str, data: dict) -> str:
    """
    Create one Server-Sent Event frame.
    """
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


_PING = ": ping\n\n"


async def _wait_for(
    task: "asyncio.Task",
    queue: "asyncio.Queue | None" = None,
):
    """
    Yield SSE progress frames or keep-alive pings
    until the supplied task finishes.
    """

    while not task.done():

        if queue is not None:
            try:
                item = await asyncio.wait_for(
                    queue.get(),
                    timeout=_PING_INTERVAL,
                )

                yield _sse(
                    "progress",
                    item,
                )

                continue

            except asyncio.TimeoutError:
                yield _PING

        else:
            await asyncio.wait(
                [task],
                timeout=_PING_INTERVAL,
            )

            if not task.done():
                yield _PING

    # Flush any remaining progress messages.
    if queue is not None:
        while not queue.empty():
            yield _sse(
                "progress",
                queue.get_nowait(),
            )

# ---------------------------------------------------------------------------
# POST /api/chat/stream
# ---------------------------------------------------------------------------

@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    # Resolve document scope.
    document_ids = list(payload.document_ids or [])
    # Backward compatibility with the existing single-document API.
    if not document_ids and payload.document_id:
        document_ids = [payload.document_id]

    if not document_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one document is required.",
        )

    # Validate every selected document belongs to the current user
    # and is ready for querying.
    documents = []

    for document_id in document_ids:
        doc_oid = parse_object_id(document_id)

        if not doc_oid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document ID: {document_id}",
            )

        doc = await db.documents.find_one({"_id": doc_oid})

        if not doc or doc["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {document_id}",
            )

        if doc["status"] != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"Document '{doc['filename']}' is still {doc['status']}",
            )

        documents.append(doc)

    # Get the existing conversation or create one for a new chat.
    conversation = await _get_or_create_conversation(
        db,
        current_user,
        payload,
        document_ids,
    )

    conversation_id = str(conversation["_id"])

    # Keep the first document_id for backward compatibility.
    primary_document_id = document_ids[0]

    # Save user message.
    await db.messages.insert_one(
        new_message_doc(
            current_user["id"],
            primary_document_id,
            "user",
            {
                "query": payload.query,
                "document_ids": document_ids,
            },
            conversation_id=conversation_id,
        )
    )

    async def event_stream():

        pending: list = []

        try:

            # ==========================================================
            # TRADITIONAL RAG
            # ==========================================================

            if payload.mode == "traditional":

                yield _sse(
                    "stage",
                    {
                        "stage": "retrieving",
                    },
                )

                query_bundle = {
                    "original_query": payload.query,
                    "rewritten_queries": [],
                    "keywords": [],
                }

                task = asyncio.create_task(
                    retrieve_candidates(
                        document_ids,
                        query_bundle,
                    )
                )

                pending.append(task)

                async for frame in _wait_for(task):
                    yield frame

                candidates = task.result()

                validated = [
                    {
                        **c,
                        "similarity": c["semantic_score"],
                        "status": "VALIDATED",
                    }
                    for c in candidates[:5]
                ]

                rewritten_queries = []

            # ==========================================================
            # CA-RAG
            # ==========================================================

            else:

                # ------------------------------------------------------
                # 1. Query rewriting
                # ------------------------------------------------------

                yield _sse(
                    "stage",
                    {
                        "stage": "rewriting",
                    },
                )

                task = asyncio.create_task(
                    rewrite_query(
                        payload.query,
                    )
                )

                pending.append(task)

                async for frame in _wait_for(task):
                    yield frame

                query_bundle = task.result()

                # ------------------------------------------------------
                # Send the actual rewritten query to frontend.
                #
                # This happens BEFORE retrieval.
                # ------------------------------------------------------

                rewritten_queries = query_bundle.get(
                    "rewritten_queries",
                    [],
                )

                if rewritten_queries:
                    yield _sse(
                        "query_rewrite",
                        {
                            "rewritten_queries": rewritten_queries,
                        },
                    )

                # ------------------------------------------------------
                # 2. Retrieval
                # ------------------------------------------------------

                yield _sse(
                    "stage",
                    {
                        "stage": "retrieving",
                    },
                )

                task = asyncio.create_task(
                    retrieve_candidates(
                        document_ids,
                        query_bundle,
                    )
                )

                pending.append(task)

                async for frame in _wait_for(task):
                    yield frame

                candidates = task.result()

                # ------------------------------------------------------
                # 3. CA-RAG validation
                # ------------------------------------------------------

                yield _sse(
                    "stage",
                    {
                        "stage": "validating",
                        "total": len(candidates),
                    },
                )

                queue: asyncio.Queue = asyncio.Queue()

                task = asyncio.create_task(
                    run_carag_validation(
                        payload.query,
                        candidates,
                        on_progress=lambda done, total:
                            queue.put_nowait(
                                {
                                    "done": done,
                                    "total": total,
                                }
                            ),
                    )
                )

                pending.append(task)

                async for frame in _wait_for(
                    task,
                    queue,
                ):
                    yield frame

                validated = task.result()

            # ==========================================================
            # 4. Answer generation
            # ==========================================================

            yield _sse(
                "stage",
                {
                    "stage": "generating",
                },
            )

            parts: list = []

            async for piece in synthesize_answer_stream(
                payload.query,
                validated,
            ):
                parts.append(piece)

                # Send answer token immediately.
                yield _sse(
                    "token",
                    {
                        "text": piece,
                    },
                )

            answer = "".join(parts)

            # ==========================================================
            # 5. Verification
            # ==========================================================

            yield _sse(
                "stage",
                {
                    "stage": "verifying",
                },
            )

            analysis = analyze(
                answer,
                validated,
            )

            # ==========================================================
            # 6. Citations
            # ==========================================================

            citations = []

            for document in documents:
                document_candidates = [
                    candidate
                    for candidate in validated
                    if candidate.get("document_id") == str(document["_id"])
                ]

                if document_candidates:
                    citations.extend(
                        build_citations(
                            document["filename"],
                            document_candidates,
                        )
                    )

            # ==========================================================
            # 7. Evidence
            # ==========================================================

            evidence = build_evidence_list(
                validated,
            )

            # ==========================================================
            # 8. Final response
            # ==========================================================

            response = ChatResponse(
                answer=answer,
                confidence=analysis["confidence"],
                status=analysis["status"],
                hallucination_risk=analysis["hallucination_risk"],
                citations=citations,
                evidence=evidence,
                mode=payload.mode,
                verification=analysis.get("verification"),
                rewritten_queries=rewritten_queries,
            )

            # ==========================================================
            # 9. Save assistant response
            # ==========================================================

            saved = await db.messages.insert_one(
                new_message_doc(
                    current_user["id"],
                    primary_document_id,
                    "assistant",
                    response.model_dump(),
                    conversation_id=conversation_id,
                )
            )

            # ==========================================================
            # 10. Final SSE event
            # ==========================================================

            response_dict = response.model_dump()
            response_dict["conversation_id"] = conversation_id
            response_dict["message_id"] = str(saved.inserted_id)

            yield _sse(
                "done",
                response_dict,
            )

        # ==============================================================
        # Client disconnected / stream cancelled
        # ==============================================================

        except asyncio.CancelledError:

            # Client went away.
            # Do not save an incomplete assistant answer.
            raise

        # ==============================================================
        # Unexpected error
        # ==============================================================

        except Exception:

            logger.exception(
                "Streaming chat failed"
            )

            yield _sse(
                "error",
                {
                    "detail": (
                        "Something went wrong while "
                        "generating the answer."
                    )
                },
            )

        # ==============================================================
        # Cleanup
        # ==============================================================

        finally:

            for task in pending:

                if not task.done():
                    task.cancel()


    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

@router.get("/history")
async def chat_history(
    document_id: str,
    conversation_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    query = {
        "user_id": current_user["id"],
        "document_id": document_id,
    }

    # If a conversation ID is supplied, return only
    # messages belonging to that conversation.
    if conversation_id:
        query["conversation_id"] = conversation_id

    cursor = db.messages.find(query).sort(
        "created_at",
        1,
    )

    history = []

    async for message in cursor:
        history.append(
            {
                "id": str(message["_id"]),
                "role": message["role"],
                "content": message["content"],
                "created_at": message["created_at"].isoformat(),
            }
        )

    return history