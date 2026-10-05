from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database.mongodb import get_db
from app.auth.authentication import (
    get_current_user,
    parse_object_id,
)
from app.models.conversation import (
    new_conversation_doc,
)


router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateConversationRequest(BaseModel):
    title: str = "New chat"
    document_ids: list[str] = Field(
        default_factory=list,
    )


class RenameConversationRequest(BaseModel):
    title: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_document_ids(
    document_ids: list[str],
) -> list[str]:
    """
    Remove duplicates while preserving order.
    """
    return list(
        dict.fromkeys(
            str(document_id)
            for document_id in document_ids
            if document_id is not None
            and str(document_id).strip()
        )
    )


def conversation_response(
    conversation: dict,
) -> dict:
    """
    Convert MongoDB conversation document into
    the API response format.
    """
    return {
        "id": str(
            conversation["_id"]
        ),
        "title": conversation.get(
            "title",
            "New chat",
        ),
        "document_ids":
            conversation.get(
                "document_ids",
                [],
            ),
        "pinned":
            conversation.get(
                "pinned",
                False,
            ),
        "archived":
            conversation.get(
                "archived",
                False,
            ),
        "created_at":
            conversation[
                "created_at"
            ].isoformat(),
        "updated_at":
            conversation[
                "updated_at"
            ].isoformat(),
    }


# ---------------------------------------------------------------------------
# List conversations
# ---------------------------------------------------------------------------

@router.get("")
async def list_conversations(
    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    cursor = (
        db.conversations
        .find(
            {
                "user_id":
                    current_user["id"],

                "archived":
                    False,
            }
        )
        .sort(
            [
                (
                    "pinned",
                    -1,
                ),
                (
                    "updated_at",
                    -1,
                ),
            ]
        )
    )

    conversations = []

    async for conversation in cursor:
        conversations.append(
            conversation_response(
                conversation
            )
        )

    return conversations


# ---------------------------------------------------------------------------
# Create conversation
# ---------------------------------------------------------------------------

@router.post("")
async def create_conversation(
    payload:
        CreateConversationRequest,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    title = (
        payload.title.strip()
        or "New chat"
    )

    document_ids = (
        normalize_document_ids(
            payload.document_ids
        )
    )

    # ---------------------------------------------------------------
    # Validate document IDs
    # ---------------------------------------------------------------

    object_ids = []

    for document_id in document_ids:
        object_id = parse_object_id(
            document_id
        )

        if object_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid document ID: "
                    f"{document_id}"
                ),
            )

        object_ids.append(
            object_id
        )

    # ---------------------------------------------------------------
    # Verify that every document belongs
    # to the authenticated user.
    # ---------------------------------------------------------------

    if object_ids:
        valid_documents = (
            await db.documents.count_documents(
                {
                    "user_id":
                        current_user["id"],

                    "_id": {
                        "$in":
                            object_ids,
                    },
                }
            )
        )

        if (
            valid_documents
            != len(object_ids)
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    "One or more documents "
                    "were not found"
                ),
            )

    # ---------------------------------------------------------------
    # Create conversation
    # ---------------------------------------------------------------

    conversation = new_conversation_doc(
        current_user["id"],
        title,
        document_ids,
    )

    result = (
        await db.conversations.insert_one(
            conversation
        )
    )

    conversation["_id"] = (
        result.inserted_id
    )

    return conversation_response(
        conversation
    )


# ---------------------------------------------------------------------------
# Rename conversation
# ---------------------------------------------------------------------------

@router.patch(
    "/{conversation_id}"
)
async def rename_conversation(
    conversation_id: str,

    payload:
        RenameConversationRequest,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail=(
                "Conversation title "
                "cannot be empty"
            ),
        )

    result = (
        await db.conversations.update_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            },
            {
                "$set": {
                    "title": title,
                    "updated_at":
                        datetime.utcnow(),
                }
            },
        )
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    return {
        "id": conversation_id,
        "title": title,
    }


# ---------------------------------------------------------------------------
# Toggle pin
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/pin"
)
async def toggle_pin(
    conversation_id: str,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    conversation = (
        await db.conversations.find_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            }
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    new_value = not conversation.get(
        "pinned",
        False,
    )

    await db.conversations.update_one(
        {
            "_id": oid,
            "user_id":
                current_user["id"],
        },
        {
            "$set": {
                "pinned": new_value,
                "updated_at":
                    datetime.utcnow(),
            }
        },
    )

    return {
        "id": conversation_id,
        "pinned": new_value,
    }


# ---------------------------------------------------------------------------
# Toggle archive
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/archive"
)
async def toggle_archive(
    conversation_id: str,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    conversation = (
        await db.conversations.find_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            }
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    new_value = not conversation.get(
        "archived",
        False,
    )

    await db.conversations.update_one(
        {
            "_id": oid,
            "user_id":
                current_user["id"],
        },
        {
            "$set": {
                "archived": new_value,
                "updated_at":
                    datetime.utcnow(),
            }
        },
    )

    return {
        "id": conversation_id,
        "archived": new_value,
    }


# ---------------------------------------------------------------------------
# Delete conversation
# ---------------------------------------------------------------------------

@router.delete(
    "/{conversation_id}"
)
async def delete_conversation(
    conversation_id: str,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    conversation = (
        await db.conversations.find_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            }
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    # ---------------------------------------------------------------
    # Delete messages belonging to this conversation.
    # ---------------------------------------------------------------

    await db.messages.delete_many(
        {
            "user_id":
                current_user["id"],

            "conversation_id":
                conversation_id,
        }
    )

    # ---------------------------------------------------------------
    # Delete the conversation itself.
    # ---------------------------------------------------------------

    await db.conversations.delete_one(
        {
            "_id": oid,
            "user_id":
                current_user["id"],
        }
    )

    return {
        "detail":
            "Conversation deleted",
    }


# ---------------------------------------------------------------------------
# Create/reuse share token
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/share"
)
async def share_conversation(
    conversation_id: str,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    conversation = (
        await db.conversations.find_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            }
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    share_token = conversation.get(
        "share_token"
    )

    # ---------------------------------------------------------------
    # Generate a token only once.
    # ---------------------------------------------------------------

    if not share_token:
        share_token = (
            secrets.token_urlsafe(32)
        )

        await db.conversations.update_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            },
            {
                "$set": {
                    "share_token":
                        share_token,

                    "updated_at":
                        datetime.utcnow(),
                }
            },
        )

    return {
        "id":
            conversation_id,

        "share_token":
            share_token,
    }


# ---------------------------------------------------------------------------
# Get one conversation
# ---------------------------------------------------------------------------

@router.get(
    "/{conversation_id}"
)
async def get_conversation(
    conversation_id: str,

    current_user: dict = Depends(
        get_current_user
    ),
):
    db = get_db()

    oid = parse_object_id(
        conversation_id
    )

    if oid is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID",
        )

    conversation = (
        await db.conversations.find_one(
            {
                "_id": oid,
                "user_id":
                    current_user["id"],
            }
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found"
            ),
        )

    return conversation_response(
        conversation
    )