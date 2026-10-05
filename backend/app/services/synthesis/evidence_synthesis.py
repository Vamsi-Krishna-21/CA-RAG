"""
Replaces agentic reasoning with a simple, non-agentic synthesis step:
takes ONLY the validated evidence chunks and asks the LLM to produce one
final answer grounded strictly in them. No planning loop, no tool use,
no multi-step reasoning graph.
"""
from app.services.llm_client import generate, generate_stream

SYSTEM_PROMPT = (
    "Answer the question using only the supplied evidence. "
    "Do not introduce information that is not supported by the evidence. "
    "If the evidence is insufficient, explicitly say so."
)


NO_EVIDENCE_ANSWER = "Insufficient evidence was found in the uploaded documents."


def _build_prompt(question: str, validated_evidence: list) -> str:
    evidence_block = "\n\n".join(
        f"[Evidence {i+1} | page {e['page_start']}] {e['text']}"
        for i, e in enumerate(validated_evidence)
    )
    return f"Evidence:\n{evidence_block}\n\nQuestion: {question}"


async def synthesize_answer(question: str, validated_evidence: list) -> str:
    if not validated_evidence:
        return NO_EVIDENCE_ANSWER

    prompt = _build_prompt(question, validated_evidence)
    return await generate(prompt, system=SYSTEM_PROMPT)


async def synthesize_answer_stream(question: str, validated_evidence: list):
    """Same prompt and system message as synthesize_answer(), streamed."""
    if not validated_evidence:
        yield NO_EVIDENCE_ANSWER
        return

    prompt = _build_prompt(question, validated_evidence)
    async for piece in generate_stream(prompt, system=SYSTEM_PROMPT):
        yield piece
