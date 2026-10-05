from datetime import datetime


def new_document_doc(user_id: str, filename: str, pages: int, filepath: str) -> dict:
    return {
        "user_id": user_id,
        "filename": filename,
        "pages": pages,
        "filepath": filepath,
        "status": "processing",
        "uploaded_at": datetime.utcnow(),
    }
