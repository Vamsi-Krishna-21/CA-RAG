"""
Feature: Feedback Learning (lightweight, no ML training / no RL --
just a bounded ranking nudge based on past thumbs up/down per chunk).
"""
from app.database.mongodb import get_db

FEEDBACK_BOOST_CAP = 0.15  # keep influence bounded so feedback can never dominate relevance


async def get_feedback_boost(chunk_id: str) -> float:
    db = get_db()
    cursor = db.feedback.find({"used_chunks": chunk_id})
    positive = 0
    negative = 0
    async for doc in cursor:
        if doc["rating"] == "positive":
            positive += 1
        else:
            negative += 1

    feedback_score = (positive + 1) / (positive + negative + 2)  # Laplace-smoothed
    # Map [0,1] score to a small signed boost around 0, capped.
    boost = (feedback_score - 0.5) * 2 * FEEDBACK_BOOST_CAP
    return boost
