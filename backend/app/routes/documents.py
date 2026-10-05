import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from app.database.mongodb import get_db
from app.models.document import new_document_doc
from app.auth.authentication import get_current_user, parse_object_id
from app.config import settings
from app.services.ingestion.document_loader import (
    SUPPORTED_EXTENSIONS,
    extract_document,
)
from app.services.ingestion.text_cleaner import strip_repeated_headers_footers
from app.services.chunking.adaptive_chunker import chunk_and_embed
from app.services import vector_store
from bson import ObjectId

router = APIRouter(prefix="/api/documents", tags=["documents"])


async def _process_document(document_id: str, filepath: str):
    """Runs after upload responds -- extraction, cleaning, chunking, embedding, indexing."""
    db = get_db()

    try:
        raw_pages = extract_document(filepath)
        cleaned_pages = strip_repeated_headers_footers(raw_pages)
        chunks, embeddings = chunk_and_embed(cleaned_pages)

        if len(chunks) > 0:
            chunk_meta = [
                {
                    "chunk_id": c["chunk_id"],
                    "document_id": document_id,
                    "text": c["text"],
                    "page_start": c["page_start"],
                    "page_end": c["page_end"],
                    "section": c["section"],
                }
                for c in chunks
            ]

            vector_store.save_document_index(
                document_id,
                embeddings,
                chunk_meta,
            )

        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"status": "ready"}},
        )

    except Exception:
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"status": "failed"}},
        )
        raise


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file format: {extension or 'unknown'}. "
                f"Supported formats: {supported}"
            ),
        )

    os.makedirs(settings.upload_dir, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(
        settings.upload_dir,
        saved_name,
    )

    with open(filepath, "wb") as f:
        f.write(await file.read())

    try:
        raw_pages = extract_document(filepath)
        pages = len(raw_pages)
    except Exception as exc:
        if os.path.exists(filepath):
            os.remove(filepath)

        raise HTTPException(
            status_code=400,
            detail=f"Could not read the uploaded file: {exc}",
        )

    db = get_db()

    doc = new_document_doc(
        current_user["id"],
        filename,
        pages,
        filepath,
    )

    result = await db.documents.insert_one(doc)
    document_id = str(result.inserted_id)

    background_tasks.add_task(
        _process_document,
        document_id,
        filepath,
    )

    return {
        "id": document_id,
        "filename": filename,
        "pages": pages,
        "status": "processing",
    }


@router.get("")
async def list_documents(
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    cursor = db.documents.find(
        {"user_id": current_user["id"]}
    ).sort("uploaded_at", -1)

    docs = []

    async for d in cursor:
        docs.append(
            {
                "id": str(d["_id"]),
                "filename": d["filename"],
                "pages": d["pages"],
                "status": d["status"],
                "uploaded_at": d["uploaded_at"].isoformat(),
            }
        )

    return docs


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    doc_oid = parse_object_id(document_id)

    doc = (
        await db.documents.find_one({"_id": doc_oid})
        if doc_oid
        else None
    )

    if not doc or doc["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    await db.documents.delete_one(
        {"_id": doc_oid}
    )

    # Also remove this document's chat messages
    # and the feedback attached to them.
    message_ids = [
        str(m["_id"])
        async for m in db.messages.find(
            {
                "user_id": current_user["id"],
                "document_id": document_id,
            },
            {"_id": 1},
        )
    ]

    if message_ids:
        await db.feedback.delete_many(
            {
                "user_id": current_user["id"],
                "message_id": {
                    "$in": message_ids
                },
            }
        )

    await db.messages.delete_many(
        {
            "user_id": current_user["id"],
            "document_id": document_id,
        }
    )

    if os.path.exists(doc["filepath"]):
        os.remove(doc["filepath"])

    for ext in (".index", ".json"):
        p = os.path.join(
            settings.vector_store_dir,
            document_id + ext,
        )

        if os.path.exists(p):
            os.remove(p)

    return {"detail": "Document deleted"}