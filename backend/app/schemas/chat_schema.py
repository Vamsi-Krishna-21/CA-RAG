from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    query: str
    mode: str = "carag"


class Citation(BaseModel):
    document_name: str
    page: int
    section: Optional[str] = None
    chunk_id: str
    snippet: str


class EvidenceItem(BaseModel):
    chunk_id: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    confidence: int
    status: str
    hallucination_risk: float
    citations: List[Citation]
    evidence: List[EvidenceItem]

    mode: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

    # Actual query rewrites used for this request.
    # Traditional RAG returns an empty list.
    rewritten_queries: List[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str
    used_chunks: List[str]