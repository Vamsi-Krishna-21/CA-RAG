from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    pages: int
    status: str
    uploaded_at: str
