import numpy as np


def cosine_similarity(a, b) -> float:
    """
    Embeddings from embed_text/embed_batch are already L2-normalized,
    so this is just a dot product -- kept as a named cosine_similarity()
    for clarity everywhere else in the pipeline that calls it.
    """
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-8
    return float(np.dot(a, b) / denom)
