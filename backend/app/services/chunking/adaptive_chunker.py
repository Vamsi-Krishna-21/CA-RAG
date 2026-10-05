"""
Adaptive chunking (Feature: Adaptive Chunking).

Pipeline: pages -> paragraphs -> sentences -> sentence embeddings ->
group consecutive sentences while semantically coherent -> chunks.

A chunk boundary is cut when ANY of:
  - a new heading/section is detected
  - similarity between the running chunk and the next sentence drops
    below SEMANTIC_THRESHOLD
  - the chunk would exceed MAX_CHUNK_TOKENS

MIN_CHUNK_TOKENS prevents tiny leftover fragments (they get merged
into the previous chunk instead of standing alone).
"""
import re
import uuid
import numpy as np

from app.config import settings
from app.services.embeddings import embed_batch
from app.utils.similarity import cosine_similarity

HEADING_RE = re.compile(
    r"^\s*(\d+(\.\d+)*\.?\s+[A-Z][A-Za-z ]{2,60}|"
    r"(ABSTRACT|INTRODUCTION|METHODOLOGY|METHODS|RELATED WORK|"
    r"RESULTS|DISCUSSION|CONCLUSION|REFERENCES|EXPERIMENTS)\b)",
    re.IGNORECASE,
)

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _approx_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _split_sentences(paragraph: str):
    return [s.strip() for s in _SENT_SPLIT_RE.split(paragraph) if s.strip()]


def _detect_section(line: str):
    return line.strip() if HEADING_RE.match(line.strip()) else None


def chunk_document(pages: list):
    units = []
    current_section = "Introduction"

    for page in pages:
        for para in page["text"].split("\n\n"):
            para = para.strip()
            if not para:
                continue
            heading = _detect_section(para.splitlines()[0]) if para.splitlines() else None
            if heading:
                current_section = heading
            for sentence in _split_sentences(para):
                if len(sentence) < 3:
                    continue
                units.append({"page": page["page"], "section": current_section, "text": sentence})

    if not units:
        return []

    sentence_embeddings = embed_batch([u["text"] for u in units])

    chunks = []
    current_sentences = [units[0]]
    current_emb_sum = sentence_embeddings[0].copy()

    def flush(sentences):
        text = " ".join(u["text"] for u in sentences)
        return {
            "chunk_id": f"c_{uuid.uuid4().hex[:8]}",
            "text": text,
            "page_start": sentences[0]["page"],
            "page_end": sentences[-1]["page"],
            "section": sentences[0]["section"],
        }

    for i in range(1, len(units)):
        unit = units[i]
        prev_avg_emb = current_emb_sum / len(current_sentences)
        sim = cosine_similarity(prev_avg_emb, sentence_embeddings[i])

        running_text = " ".join(u["text"] for u in current_sentences)
        would_exceed_max = _approx_tokens(running_text + " " + unit["text"]) > settings.max_chunk_tokens
        section_changed = unit["section"] != current_sentences[-1]["section"]
        below_threshold = sim < settings.semantic_threshold

        should_cut = (
            would_exceed_max
            or (section_changed and _approx_tokens(running_text) >= settings.min_chunk_tokens)
            or (below_threshold and _approx_tokens(running_text) >= settings.min_chunk_tokens)
        )

        if should_cut:
            chunks.append(flush(current_sentences))
            current_sentences = [unit]
            current_emb_sum = sentence_embeddings[i].copy()
        else:
            current_sentences.append(unit)
            current_emb_sum += sentence_embeddings[i]

    if current_sentences:
        chunks.append(flush(current_sentences))

    if len(chunks) > 1 and _approx_tokens(chunks[-1]["text"]) < settings.min_chunk_tokens:
        last = chunks.pop()
        chunks[-1]["text"] += " " + last["text"]
        chunks[-1]["page_end"] = last["page_end"]

    return chunks


def chunk_and_embed(pages: list):
    chunks = chunk_document(pages)
    if not chunks:
        return [], np.zeros((0, 384))
    embeddings = embed_batch([c["text"] for c in chunks])
    return chunks, embeddings
