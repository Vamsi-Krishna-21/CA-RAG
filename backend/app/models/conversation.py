from datetime import datetime


def new_conversation_doc(
    user_id: str,
    title: str,
    document_ids: list[str] | None = None,
) -> dict:
    now = datetime.utcnow()

    return {
        "user_id": user_id,
        "title": title,
        "document_ids": document_ids or [],
        "pinned": False,
        "archived": False,
        "share_token": None,
        "created_at": now,
        "updated_at": now,
    }


def new_message_doc(
    user_id: str,
    document_id: str | None,
    role: str,
    content: dict,
    conversation_id: str | None = None,
) -> dict:
    return {
        "user_id": user_id,
        "document_id": document_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": datetime.utcnow(),
    }