"""
Combines semantic similarity, keyword overlap, and the (bounded) feedback
signal from past user ratings into one retrieval score.
"""


def keyword_score(text: str, keywords: list) -> float:
    if not keywords:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return hits / len(keywords)


def combine_scores(semantic_score: float, kw_score: float, feedback_boost: float = 0.0) -> float:
    base = 0.7 * semantic_score + 0.3 * kw_score
    return base + feedback_boost
