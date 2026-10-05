"""
Extracts text from a PDF page-by-page using PyMuPDF, preserving page numbers
-- required later for citations to point at a real page.
"""
import fitz  # PyMuPDF


def extract_pages(filepath: str):
    """Returns [{"page": 1, "text": "..."}, ...], 1-indexed pages."""
    doc = fitz.open(filepath)
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text("text")})
    doc.close()
    return pages


def page_count(filepath: str) -> int:
    doc = fitz.open(filepath)
    n = doc.page_count
    doc.close()
    return n
