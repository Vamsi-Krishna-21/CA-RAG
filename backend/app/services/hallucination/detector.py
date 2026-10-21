"""
Feature: Hallucination Detection.

Splits the generated answer into individual factual claims, checks each
against the validated evidence pool, and removes unsupported claims before
the answer is returned.
"""
import re
from app.services.embeddings import embed_text
from app.utils.similarity import cosine_similarity
from app.services.hallucination.confidence import compute_confidence, status_for_confidence

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
CLAIM_SUPPORT_THRESHOLD = 0.5
NO_EVIDENCE_ANSWER = "Insufficient evidence was found in the uploaded documents."


def _split_claims(answer: str):
    return [c.strip() for c in _SENT_SPLIT_RE.split(answer) if len(c.strip()) > 3]


def analyze(answer: str, validated_evidence: list) -> dict:
    if not validated_evidence:
        return {
            "confidence": 0,
            "status": "INSUFFICIENT_EVIDENCE",
            "hallucination_risk": 1.0,
            "verification": {
                "confidence_available": False,
                "reason": "No supporting evidence was retrieved.",
                "claims_checked": 0,
                "claims_supported": 0,
                "unsupported_claims": [],
                "evidence_coverage": 0.0,
            },
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
    supported_claims = sum(
        1 for score in claim_scores
        if score >= CLAIM_SUPPORT_THRESHOLD
    )
    evidence_coverage = supported_claims / len(claim_scores) if claim_scores else 0.0
    unsupported_claims = [
        {
            "claim": claim,
            "support": round(float(score), 3),
        }
        for claim, score in zip(claims, claim_scores)
        if score < CLAIM_SUPPORT_THRESHOLD
    ]
    claim_results = [
        {
            "claim": claim,
            "support": round(float(score), 3),
            "supported": score >= CLAIM_SUPPORT_THRESHOLD,
        }
        for claim, score in zip(claims, claim_scores)
    ]

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
    needs_revision = bool(unsupported_claims)

    return {
        "confidence": confidence,
        "status": status,
        "hallucination_risk": hallucination_risk,
        "needs_revision": needs_revision,
        # User-facing numeric breakdown of the values that fed compute_confidence().
        # Purely informational -- these are the same numbers, just reported.
        "verification": {
            "confidence_available": True,
            "evidence_alignment": round(float(average_evidence_similarity), 3),
            "claim_support": round(float(claim_support), 3),
            "evidence_coverage": round(float(evidence_coverage), 3),
            "source_agreement": round(float(source_agreement), 3),
            "claims_checked": len(claim_scores),
            "claims_supported": supported_claims,
            "claims": claim_results,
            "unsupported_claims": unsupported_claims,
        },
    }


def ground_answer(answer: str, validated_evidence: list) -> tuple[str, dict]:
    """Remove unsupported claims without introducing new information."""
    if not validated_evidence:
        return NO_EVIDENCE_ANSWER, analyze(answer, validated_evidence)

    analysis = analyze(answer, validated_evidence)
    claim_results = analysis["verification"]["claims"]
    supported_claims = [
        result["claim"]
        for result in claim_results
        if result["supported"]
    ]

    if len(supported_claims) == len(claim_results):
        analysis.pop("needs_revision", None)
        return answer, analysis

    grounded_answer = " ".join(supported_claims).strip()
    if not grounded_answer:
        grounded_answer = NO_EVIDENCE_ANSWER

    grounded_analysis = analyze(
        grounded_answer if supported_claims else "",
        validated_evidence,
    )
    grounded_analysis["verification"]["answer_revised"] = True
    grounded_analysis["verification"]["unsupported_claims_removed"] = True
    grounded_analysis["verification"]["unsupported_claims"] = analysis[
        "verification"
    ]["unsupported_claims"]
    grounded_analysis["verification"]["claims_checked"] = analysis[
        "verification"
    ]["claims_checked"]
    grounded_analysis["verification"]["claims_supported"] = len(
        supported_claims
    )
    grounded_analysis["verification"]["claims"] = claim_results
    grounded_analysis.pop("needs_revision", None)
    return grounded_answer, grounded_analysis
