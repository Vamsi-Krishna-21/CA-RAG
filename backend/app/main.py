from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.routes import auth, documents, chat, feedback, conversations
from app.services.llm_client import close_llm_client

app = FastAPI(title="CA-RAG Research Paper QA System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    connect_to_mongo()


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
