"""
Thin abstraction over the LLM backend so the rest of the pipeline never
cares whether it's talking to Ollama (local) or an OpenAI-compatible API.
Swap providers by changing LLM_PROVIDER in .env -- no other code changes.
"""
import json
from typing import AsyncIterator, Optional

import httpx
from app.config import settings

# One long-lived client (connection pooling / keep-alive) instead of building a
# new client, and a new connection, for every LLM call. The pipeline makes
# 1 + N + 1 calls per question, so this removes a lot of connection overhead.
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=settings.llm_timeout)
    return _client


async def close_llm_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def generate(prompt: str, system: str = "", json_mode: bool = False) -> str:
    if settings.llm_provider == "ollama":
        return await _ollama_generate(prompt, system, json_mode)
    elif settings.llm_provider == "openai_compatible":
        return await _openai_generate(prompt, system, json_mode)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


async def _ollama_generate(prompt: str, system: str, json_mode: bool) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"

    client = _get_client()
    resp = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


async def _openai_generate(prompt: str, system: str, json_mode: bool) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": settings.openai_model, "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    client = _get_client()
    resp = await client.post(
        f"{settings.openai_base_url}/chat/completions", json=payload, headers=headers
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def generate_stream(prompt: str, system: str = "") -> AsyncIterator[str]:
    """
    Same request as generate(), but yields the completion incrementally as the
    provider produces it (real token streaming, not a replay of a finished
    answer). Concatenating everything yielded equals what generate() returns.
    """
    if settings.llm_provider == "ollama":
        async for piece in _ollama_stream(prompt, system):
            yield piece
    elif settings.llm_provider == "openai_compatible":
        async for piece in _openai_stream(prompt, system):
            yield piece
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


async def _ollama_stream(prompt: str, system: str) -> AsyncIterator[str]:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": system,
        "stream": True,
    }
    client = _get_client()
    async with client.stream(
        "POST", f"{settings.ollama_base_url}/api/generate", json=payload
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("error"):
                raise RuntimeError(f"LLM error: {data['error']}")
            piece = data.get("response", "")
            if piece:
                yield piece
            if data.get("done"):
                break


async def _openai_stream(prompt: str, system: str) -> AsyncIterator[str]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": settings.openai_model, "messages": messages, "stream": True}
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    client = _get_client()
    async with client.stream(
        "POST", f"{settings.openai_base_url}/chat/completions", json=payload, headers=headers
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            body = line[len("data:"):].strip()
            if body == "[DONE]":
                break
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            piece = (choices[0].get("delta") or {}).get("content")
            if piece:
                yield piece


def safe_json_parse(text: str, fallback: dict) -> dict:
    """LLMs sometimes wrap JSON in markdown fences or add stray text -- clean and parse defensively."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return fallback
