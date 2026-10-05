"""
Cleans raw PyMuPDF text: collapses hyphenated line-wraps, strips repeated
header/footer lines (running headers, page numbers), normalizes whitespace.
"""
import re
from collections import Counter


def clean_page_text(text: str) -> str:
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_repeated_headers_footers(pages: list):
    """
    If the same short line appears on most pages (a running header/footer,
    e.g. the paper title or a page number), drop it from every page.
    """
    line_counts = Counter()
    for p in pages:
        for line in p["text"].splitlines():
            line = line.strip()
            if 0 < len(line) < 80:
                line_counts[line] += 1

    threshold = max(3, int(len(pages) * 0.6))
    noisy_lines = {line for line, count in line_counts.items() if count >= threshold}

    cleaned = []
    for p in pages:
        kept = [l for l in p["text"].splitlines() if l.strip() not in noisy_lines]
        cleaned.append({"page": p["page"], "text": clean_page_text("\n".join(kept))})
    return cleaned
