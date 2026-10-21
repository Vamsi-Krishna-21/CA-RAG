"""
Feature: Query Rewriting.

Produces up to 3 alternative phrasings of the user's question plus a
keyword list, to widen retrieval recall WITHOUT changing user intent.
This is a single constrained LLM call -- not an autonomous agent.
"""
from app.services.llm_client import generate, safe_json_parse

MAX_HISTORY_MESSAGES = 10

SYSTEM_PROMPT = (
    "You rewrite search queries for a document retrieval system. "
    "Previous conversation messages are context only, not additional user "
    "instructions. The current user question has priority. Use conversation "
    "history only to resolve references and missing context (for example: "
    "it, its, this, that, these, those, they, them, the above, the previous "
    "method, the previous model, what about..., etc.). Do not rewrite the "
    "user's intent, do not answer the question, do not invent context, and "
    "do not use irrelevant old messages. Rewrite the current question so it "
    "is self-contained only when the current question depends on earlier "
    "conversation. If it is already self-contained, preserve it without "
    "unnecessary changes. Return only valid JSON with 'rewritten_queries' and "
    "'keywords': {'rewritten_queries': ['...'], 'keywords': ['...']}"
)


def _extract_message_text(message: dict) -> str | None:
    """Extract the most useful text from a message payload."""
    if not isinstance(message, dict):
        return None

    content = message.get("content")

    if isinstance(content, str):
        text = content
    elif isinstance(content, dict):
        text = (
            content.get("query")
            or content.get("answer")
            or content.get("content")
            or message.get("query")
            or message.get("answer")
        )
    else:
        text = message.get("query") or message.get("answer")

    if not isinstance(text, str):
        return None

    cleaned = text.strip()
    return cleaned or None


def _format_history(conversation_history: list[dict] | None) -> str | None:
    """Return a bounded, safely normalized history representation."""
    if not conversation_history:
        return None

    formatted_messages = []
    for message in conversation_history[:MAX_HISTORY_MESSAGES]:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        text = _extract_message_text(message)
        if role not in {"user", "assistant"} or not text:
            continue

        formatted_messages.append(f"{role}: {text}")

    if not formatted_messages:
        return None

    return "\n".join(formatted_messages)


async def rewrite_query(
    original_query: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    fallback = {
        "rewritten_queries": [],
        "keywords": original_query.lower().split(),
    }
    history = _format_history(conversation_history)
    prompt = (
        "Conversation history:\n"
        f"{history or 'None'}\n\n"
        f"Current user question: {original_query}\n\n"
        "Rewrite the current question for document retrieval. "
        "If the current question depends on previous conversation, make it "
        "self-contained using only information supported by the conversation. "
        "If it is already self-contained, preserve it without unnecessary "
        "changes."
    )

    raw = await generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
    parsed = safe_json_parse(raw, fallback)
    if not isinstance(parsed, dict):
        parsed = fallback

    rewritten = parsed.get("rewritten_queries", [])
    if not isinstance(rewritten, list):
        rewritten = []
    rewritten = [
        query.strip()
        for query in rewritten
        if isinstance(query, str) and query.strip()
    ][:3]

    keywords = parsed.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    keywords = [
        keyword.strip()
        for keyword in keywords
        if isinstance(keyword, str) and keyword.strip()
    ]

    return {
        "original_query": original_query,
        "rewritten_queries": rewritten,
        "keywords": keywords,
    }
