import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger("uvicorn.error")

client = None
db = None


def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    return db


def close_mongo_connection():
    global client
    if client:
        client.close()


def get_db():
    global db
    if db is None:
        connect_to_mongo()
    return db


async def init_db_indexes():
    """Create essential MongoDB indexes asynchronously on startup."""
    database = get_db()
    try:
        # Messages collection indexes
        await database.messages.create_index(
            [("conversation_id", 1), ("created_at", 1)]
        )
        await database.messages.create_index(
            [("user_id", 1), ("document_id", 1)]
        )

        # Conversations collection indexes
        await database.conversations.create_index(
            [("user_id", 1), ("pinned", -1), ("updated_at", -1)]
        )

        # Documents collection indexes
        await database.documents.create_index(
            [("user_id", 1), ("uploaded_at", -1)]
        )

        # Feedback collection indexes
        await database.feedback.create_index(
            [("used_chunks", 1)]
        )
        await database.feedback.create_index(
            [("message_id", 1)]
        )

        # Chunks collection indexes
        await database.chunks.create_index(
            [("document_id", 1), ("chunk_index", 1)],
            unique=True,
        )
        await database.chunks.create_index(
            [("chunk_id", 1)]
        )
        await database.chunks.create_index(
            [("document_id", 1)]
        )
    except Exception as exc:
        logger.warning("Could not initialize MongoDB indexes: %s", exc)
