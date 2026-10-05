"""
Transparent, explainable confidence formula (deliberately not a black-box
classifier -- this needs to be defensible in a viva).
"""


def compute_confidence(
    average_evidence_similarity: float,
    claim_support: float,
    evidence_coverage: float,
    source_agreement: float,
) -> int:
    score = (
        0.45 * average_evidence_similarity
        + 0.30 * claim_support
        + 0.15 * evidence_coverage
        + 0.10 * source_agreement
    )
    return round(max(0.0, min(1.0, score)) * 100)


def status_for_confidence(confidence: int) -> str:
    if confidence >= 85:
        return "HIGHLY_SUPPORTED"
    if confidence >= 70:
        return "SUPPORTED"
    if confidence >= 50:
        return "PARTIALLY_SUPPORTED"
    return "INSUFFICIENT_EVIDENCE"
