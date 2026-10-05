"""
Minimal starter tests. Run with `pytest` from the backend/ directory.
Extend these with cases for the adaptive chunker and the CA-RAG
validation threshold as the project grows.
"""
import numpy as np
from app.utils.similarity import cosine_similarity
from app.services.hallucination.confidence import compute_confidence, status_for_confidence


def test_cosine_similarity_identical_vectors():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) > 0.999


def test_cosine_similarity_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_confidence_formula_bounds():
    score = compute_confidence(1.0, 1.0, 1.0, 1.0)
    assert score == 100
    score = compute_confidence(0.0, 0.0, 0.0, 0.0)
    assert score == 0


def test_status_thresholds():
    assert status_for_confidence(90) == "HIGHLY_SUPPORTED"
    assert status_for_confidence(75) == "SUPPORTED"
    assert status_for_confidence(55) == "PARTIALLY_SUPPORTED"
    assert status_for_confidence(30) == "INSUFFICIENT_EVIDENCE"
