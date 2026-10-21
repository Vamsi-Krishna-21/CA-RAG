from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection, init_db_indexes
from app.routes import auth, documents, chat, feedback, conversations
from app.services.llm_client import close_llm_client

app = FastAPI(title="Enhance CA-RAG Research Paper QA System")

cors_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
if settings.frontend_url:
    cors_origins.add(settings.frontend_url.rstrip("/"))
if settings.cors_origins:
    for o in settings.cors_origins.split(","):
        cleaned = o.strip().rstrip("/")
        if cleaned:
            cors_origins.add(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    connect_to_mongo()
    await init_db_indexes()


@app.on_event("shutdown")
async def on_shutdown():
    close_mongo_connection()
    await close_llm_client()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(conversations.router)
