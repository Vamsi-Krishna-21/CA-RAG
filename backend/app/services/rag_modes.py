from __future__ import annotations

from typing import Any

from fastapi import HTTPException

ENHANCED_CARAG_MODE = "enhanced_carag"
CARAG_MODE = "carag"
TRADITIONAL_RAG_MODE = "traditional_rag"

VALID_RAG_MODES = {
    ENHANCED_CARAG_MODE,
    CARAG_MODE,
    TRADITIONAL_RAG_MODE,
}

MODE_ALIASES = {
    "enhanced": ENHANCED_CARAG_MODE,
    "enhanced_carag": ENHANCED_CARAG_MODE,
    "enhance_ca_rag": ENHANCED_CARAG_MODE,
    "ca_rag": CARAG_MODE,
    "carag": CARAG_MODE,
    "traditional": TRADITIONAL_RAG_MODE,
    "traditional_rag": TRADITIONAL_RAG_MODE,
}


def normalize_rag_mode(mode: Any) -> str:
    if mode is None:
        return "enhanced_carag"

    value = str(mode).strip().lower()
    if not value:
        return "enhanced_carag"

    canonical = MODE_ALIASES.get(value)
    if canonical is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported RAG mode: {mode}",
        )

    return canonical
