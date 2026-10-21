import numpy as np

from app.schemas.chat_schema import ChatResponse
from app.services.hallucination import detector
from app.services.hallucination.confidence import compute_confidence


def _embedding(text):
    if "Supported fact" in text:
        return np.array([1.0, 0.0])
    if "Unsupported claim" in text:
        return np.array([0.0, 1.0])
    return np.array([1.0, 0.0])


def test_ground_answer_removes_unsupported_claims(monkeypatch):
    monkeypatch.setattr(detector, "embed_text", _embedding)
    evidence = [
        {
            "text": "Supported fact is documented.",
            "similarity": 0.9,
        }
    ]

    answer, analysis = detector.ground_answer(
        "Supported fact is documented. Unsupported claim is not in the source.",
        evidence,
    )

    assert answer == "Supported fact is documented."
    assert analysis["verification"]["answer_revised"] is True
    assert analysis["verification"]["unsupported_claims_removed"] is True
    assert analysis["verification"]["claims_checked"] == 2
    assert analysis["verification"]["claims_supported"] == 1
    assert analysis["verification"]["unsupported_claims"][0]["claim"].startswith(
        "Unsupported claim"
    )


def test_ground_answer_returns_insufficient_when_no_claim_is_supported(monkeypatch):
    monkeypatch.setattr(
        detector,
        "embed_text",
        lambda text: np.array([0.0, 1.0]) if "Unsupported" in text else np.array([1.0, 0.0]),
    )

    answer, analysis = detector.ground_answer(
        "Unsupported claim is not documented.",
        [{"text": "A source with unrelated facts.", "similarity": 0.8}],
    )

    assert answer == detector.NO_EVIDENCE_ANSWER
    assert analysis["verification"]["unsupported_claims_removed"] is True


def test_confidence_uses_existing_dynamic_formula_with_evidence(monkeypatch):
    monkeypatch.setattr(detector, "embed_text", _embedding)
    analysis = detector.analyze(
        "Supported fact is documented.",
        [{"text": "Supported fact is documented.", "similarity": 0.8}],
    )

    expected = compute_confidence(0.8, 1.0, 1.0, 0.6)
    assert analysis["confidence"] == expected
    assert analysis["verification"]["confidence_available"] is True


def test_no_evidence_confidence_is_explicit_and_response_schema_compatible():
    analysis = detector.analyze("An answer.", [])

    response = ChatResponse(
        answer=detector.NO_EVIDENCE_ANSWER,
        confidence=analysis["confidence"],
        status=analysis["status"],
        hallucination_risk=analysis["hallucination_risk"],
        citations=[],
        evidence=[],
        verification=analysis["verification"],
    )

    assert response.confidence == 0
    assert response.hallucination_risk == 1.0
    assert response.verification["confidence_available"] is False
    assert response.verification["reason"] == "No supporting evidence was retrieved."
