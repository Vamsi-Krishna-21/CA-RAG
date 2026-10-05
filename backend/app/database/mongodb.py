from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

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
