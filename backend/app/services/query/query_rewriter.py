"""
Feature: Query Rewriting.

Produces up to 3 alternative phrasings of the user's question plus a
keyword list, to widen retrieval recall WITHOUT changing user intent.
This is a single constrained LLM call -- not an autonomous agent.
"""
from app.services.llm_client import generate, safe_json_parse

SYSTEM_PROMPT = (
    "You rewrite search queries for a document retrieval system. "
    "Produce at most 3 alternative phrasings that preserve the EXACT same "
    "intent as the original question -- do not answer the question, do not "
    "add assumptions, do not broaden or narrow the meaning. "
    'Respond ONLY with JSON: {"rewritten_queries": ["...", "..."], "keywords": ["...", "..."]}'
)


async def rewrite_query(original_query: str) -> dict:
    prompt = f"Original question: {original_query}"
    raw = await generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
    fallback = {"rewritten_queries": [], "keywords": original_query.lower().split()}
    parsed = safe_json_parse(raw, fallback)

    rewritten = parsed.get("rewritten_queries", [])[:3]
    keywords = parsed.get("keywords", [])

    return {
        "original_query": original_query,
        "rewritten_queries": rewritten,
        "keywords": keywords,
    }
