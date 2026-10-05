from datetime import datetime


def new_feedback_doc(user_id: str, message_id: str, rating: str, used_chunks: list) -> dict:
    return {
        "user_id": user_id,
        "message_id": message_id,
        "rating": rating,
        "used_chunks": used_chunks,
        "created_at": datetime.utcnow(),
    }
