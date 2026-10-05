"""
Feature: Hallucination Detection.

Splits the synthesized answer into individual factual claims, checks each
against the validated evidence pool, and feeds the results into the
confidence formula (confidence.py).
"""
import re
from app.services.embeddings import embed_text
from app.utils.similarity import cosine_similarity
from app.services.hallucination.confidence import compute_confidence, status_for_confidence

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _split_claims(answer: str):
    return [c.strip() for c in _SENT_SPLIT_RE.split(answer) if len(c.strip()) > 3]


def analyze(answer: str, validated_evidence: list) -> dict:
    if not validated_evidence:
        return {
            "confidence": 20,
            "status": "INSUFFICIENT_EVIDENCE",
            "hallucination_risk": 0.9,
        }

    claims = _split_claims(answer)
    evidence_embs = [embed_text(e["text"]) for e in validated_evidence]

    claim_scores = []
    for claim in claims:
        claim_emb = embed_text(claim)
        best = max(cosine_similarity(claim_emb, ev) for ev in evidence_embs)
        claim_scores.append(best)

    claim_support = sum(claim_scores) / len(claim_scores) if claim_scores else 0.0
    average_evidence_similarity = sum(e["similarity"] for e in validated_evidence) / len(validated_evidence)

    # Coverage: fraction of claims that clear a basic support bar.
    supported_claims = sum(1 for s in claim_scores if s >= 0.5)
    evidence_coverage = supported_claims / len(claim_scores) if claim_scores else 0.0

    # Source agreement: how tightly the validated chunks agree with each other
    # (multiple independent sources saying the same thing is a stronger signal
    # than one isolated chunk).
    if len(evidence_embs) > 1:
        pair_sims = [
            cosine_similarity(evidence_embs[i], evidence_embs[j])
            for i in range(len(evidence_embs))
            for j in range(i + 1, len(evidence_embs))
        ]
        source_agreement = sum(pair_sims) / len(pair_sims)
    else:
        source_agreement = 0.6  # single source: neutral-ish default

    confidence = compute_confidence(average_evidence_similarity, claim_support, evidence_coverage, source_agreement)
    status = status_for_confidence(confidence)
    hallucination_risk = round(1 - (confidence / 100), 2)

    return {
        "confidence": confidence,
        "status": status,
        "hallucination_risk": hallucination_risk,
        # User-facing numeric breakdown of the values that fed compute_confidence().
        # Purely informational -- these are the same numbers, just reported.
        "verification": {
            "evidence_alignment": round(float(average_evidence_similarity), 3),
            "claim_support": round(float(claim_support), 3),
            "evidence_coverage": round(float(evidence_coverage), 3),
            "source_agreement": round(float(source_agreement), 3),
            "claims_checked": len(claim_scores),
            "claims_supported": supported_claims,
        },
    }
