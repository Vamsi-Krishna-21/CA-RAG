from fastapi import APIRouter, Depends, HTTPException
from app.schemas.chat_schema import FeedbackRequest
from app.database.mongodb import get_db
from app.auth.authentication import get_current_user, parse_object_id
from app.models.feedback import new_feedback_doc

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(payload: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()

    # The rated message must be an assistant answer that belongs to the caller.
    message_oid = parse_object_id(payload.message_id)
    message = None
    if message_oid is not None:
        message = await db.messages.find_one(
            {"_id": message_oid, "user_id": current_user["id"], "role": "assistant"}
        )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # used_chunks must be chunks that were actually part of that answer -- otherwise a user
    # could attach ratings to arbitrary chunk ids and skew feedback learning.
    content = message.get("content") or {}
    allowed_chunks = {e.get("chunk_id") for e in content.get("evidence", [])}
    allowed_chunks |= {c.get("chunk_id") for c in content.get("citations", [])}
    if any(chunk_id not in allowed_chunks for chunk_id in payload.used_chunks):
        raise HTTPException(status_code=400, detail="used_chunks must come from the rated answer")

    doc = new_feedback_doc(current_user["id"], payload.message_id, payload.rating, payload.used_chunks)
    await db.feedback.insert_one(doc)
    return {"detail": "Feedback recorded"}
