"""
Feature: Source Citations.

Maps validated evidence back to real chunk metadata -- every citation must
point at an actual chunk that was actually validated. Never fabricated.
"""


def build_citations(document_name: str, validated_evidence: list) -> list:
    citations = []
    for e in validated_evidence:
        snippet = e["text"][:220] + ("..." if len(e["text"]) > 220 else "")
        citations.append(
            {
                "document_name": document_name,
                "page": e["page_start"],
                "section": e.get("section"),
                "chunk_id": e["chunk_id"],
                "snippet": snippet,
            }
        )
    return citations


def build_evidence_list(validated_evidence: list) -> list:
    return [{"chunk_id": e["chunk_id"], "similarity": e["similarity"]} for e in validated_evidence]
