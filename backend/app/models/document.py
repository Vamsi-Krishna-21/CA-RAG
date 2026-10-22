from datetime import datetime


def new_document_doc(user_id: str, filename: str, pages: int, filepath: str) -> dict:
    return {
        "user_id": user_id,
        "filename": filename,
        "pages": pages,
        "filepath": filepath,
        "status": "processing",
        "chunk_count": 0,
        "uploaded_at": datetime.utcnow(),
    }


def new_chunk_doc(
    document_id: str,
    chunk_id: str,
    chunk_index: int,
    text: str,
    page_start: int,
    page_end: int,
    section: str,
    embedding_bytes: bytes,
) -> dict:
    from bson.binary import Binary

    return {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "text": text,
        "page_start": page_start,
        "page_end": page_end,
        "section": section,
        "embedding": Binary(embedding_bytes),
        "created_at": datetime.utcnow(),
    }

