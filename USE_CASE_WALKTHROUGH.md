# CA-RAG System — End-to-End Use Case Walkthrough

**Scenario:** A CS research student uploads a paper on transformer attention mechanisms and asks the system a technical question about it.

---

## Setup

| | |
|---|---|
| **User** | Priya, a CS student researching attention mechanisms |
| **Document** | `attention_transformers.pdf` (14 pages) |
| **Question** | "How does the attention mechanism reduce computational complexity compared to recurrent models?" |

---

## Step 0 — Document Upload & Adaptive Chunking

**Frontend (Documents page):**
Priya drags `attention_transformers.pdf` into the `UploadBox` component. A progress indicator shows "Processing…" while the backend works, then the `DocumentCard` updates to show page count and status: `Ready`.

**Backend, internally:**

```
POST /api/documents/upload
```

1. `pdf_loader.py` (PyMuPDF) extracts raw text page-by-page, preserving `page_number`.
2. `text_cleaner.py` strips headers/footers, fixes broken line breaks from PDF extraction.
3. `adaptive_chunker.py` walks the cleaned text:
   - Splits into paragraphs → sentences → computes sentence embeddings.
   - Groups sentences into a chunk while consecutive-sentence cosine similarity stays above `SEMANTIC_THRESHOLD = 0.30`.
   - Cuts a chunk when: a new heading appears (e.g. "3. Methodology"), similarity drops below threshold, or `MAX_CHUNK_TOKENS = 500` is hit.
   - Enforces `MIN_CHUNK_TOKENS = 100` so it doesn't produce tiny fragments.

Example resulting chunk:

```json
{
  "chunk_id": "c_014",
  "document_id": "doc_9a2f",
  "text": "Self-attention allows the model to relate positions of a
           single sequence... unlike recurrent models which process
           tokens sequentially, attention computes relationships in
           parallel across the full sequence...",
  "page_start": 3,
  "page_end": 3,
  "section": "3. Model Architecture",
  "embedding": [0.021, -0.114, ...]
}
```

4. Each chunk's embedding is stored in FAISS/Chroma with metadata (`document_id`, `chunk_id`, `page`, `section`); chunk text and document metadata go into MongoDB.

**What Priya sees:** `attention_transformers.pdf · 14 pages · Uploaded 2 min ago · Status: Ready`

---

## Step 1 — Asking the Question

**Frontend (Chat page):**
Priya types her question into the chat box and hits send. Her message appears immediately as a `ChatMessage` bubble; a typing/loading indicator appears for the assistant's reply.

```
POST /api/chat
{ "document_id": "doc_9a2f", "query": "How does the attention mechanism
  reduce computational complexity compared to recurrent models?" }
```

---

## Step 2 — Query Rewriting

**Backend:** `query_rewriter.py` sends the query to the LLM with a constrained prompt ("do not change intent, max 3 rewrites").

```json
{
  "original_query": "How does the attention mechanism reduce computational complexity compared to recurrent models?",
  "rewritten_queries": [
    "Why is self-attention more computationally efficient than RNNs?",
    "Parallelization advantage of attention over sequential recurrent processing"
  ],
  "keywords": ["attention", "computational complexity", "recurrent", "parallelization"]
}
```

Nothing is shown to Priya yet — this stage is invisible, purely internal.

---

## Step 3 — Retrieval

**Backend:** `retriever.py` embeds the original query + rewrites, searches FAISS for nearest chunks, and combines with keyword overlap:

```
retrieval_score = 0.7 * semantic_score + 0.3 * keyword_score
```

Top ~10 candidate chunks come back, e.g. chunks from pages 3, 3, 4, and 9 (all discussing attention vs. recurrence). These are only *candidates* — not yet trusted as evidence.

---

## Step 4 — CA-RAG Validation (the core contribution)

**Backend:** `carag_pipeline.py`, for **each** candidate chunk:

1. `candidate_generator.py` asks the LLM: *"Given this chunk, answer the question."* → produces a candidate answer per chunk.
2. `similarity_validator.py` embeds that candidate answer and computes:

```
cosine_similarity(embedding(candidate_answer), embedding(chunk))
```

3. Chunks below the similarity threshold are **rejected** (the candidate answer didn't actually align with what the chunk says — a sign of drift/hallucination at the chunk level).

Example validation results:

| chunk_id | page | similarity | status |
|---|---|---|---|
| c_014 | 3 | 0.87 | ✅ VALIDATED |
| c_015 | 3 | 0.81 | ✅ VALIDATED |
| c_031 | 9 | 0.42 | ❌ REJECTED |
| c_022 | 4 | 0.29 | ❌ REJECTED |

Only `c_014` and `c_015` survive as trusted evidence. This is the step that distinguishes CA-RAG from plain RAG — plain RAG would have handed all 4 chunks straight to the answer generator.

---

## Step 5 — Evidence Synthesis

**Backend:** `evidence_synthesis.py` receives *only* the validated chunks (`c_014`, `c_015`) and prompts:

> "Answer the question using only the supplied evidence. Do not introduce information that is not supported by the evidence. If the evidence is insufficient, explicitly say so."

Produces a draft final answer grounded strictly in those two chunks.

---

## Step 6 — Hallucination Detection & Confidence Scoring

**Backend:** `detector.py` splits the draft answer into individual factual claims and checks each against the validated evidence, then computes:

```
confidence = 0.45 * average_evidence_similarity
            + 0.30 * claim_support
            + 0.15 * evidence_coverage
            + 0.10 * source_agreement
```

Say this comes out to **91** → status band `85–100` → `HIGHLY_SUPPORTED`.

---

## Step 7 — Citation Generation

**Backend:** `citation_generator.py` maps each surviving claim back to its source chunk:

```json
[
  { "document_name": "attention_transformers.pdf", "page": 3, "section": "3. Model Architecture",
    "chunk_id": "c_014", "snippet": "...attention computes relationships in parallel across the full sequence..." },
  { "document_name": "attention_transformers.pdf", "page": 3, "section": "3. Model Architecture",
    "chunk_id": "c_015", "snippet": "...eliminating the sequential dependency inherent to recurrent architectures..." }
]
```

---

## Step 8 — What Priya Sees on Screen

The `ChatMessage` (assistant) renders:

> **Answer:** The attention mechanism computes relationships between all sequence positions in parallel, rather than processing tokens one-by-one as recurrent models do — removing the sequential dependency that limits RNN parallelization and reducing the effective path length between distant tokens.
>
> **Confidence:** 91% · **Status:** `HIGHLY_SUPPORTED`
>
> **Sources:**
> [1] attention_transformers.pdf — Page 3, §3. Model Architecture
> [2] attention_transformers.pdf — Page 3, §3. Model Architecture
>
> 👍 👎

Clicking citation `[1]` expands an `EvidenceCard` showing the full chunk text, page, section, and similarity score (0.87) — so Priya can verify the claim herself against the source.

**Full JSON returned to frontend:**

```json
{
  "answer": "The attention mechanism computes relationships between all sequence positions in parallel...",
  "confidence": 91,
  "status": "SUPPORTED",
  "hallucination_risk": 0.09,
  "citations": [ ... ],
  "evidence": [
    { "chunk_id": "c_014", "similarity": 0.87 },
    { "chunk_id": "c_015", "similarity": 0.81 }
  ]
}
```

---

## Step 9 — Feedback Loop

Priya clicks 👍. `FeedbackButtons` fires:

```
POST /api/feedback
{ "message_id": "...", "rating": "positive", "used_chunks": ["c_014", "c_015"] }
```

Backend updates the stored feedback score for those chunks:

```
feedback_score = (positive + 1) / (positive + negative + 2)
```

Next time *any* user asks a related question, `c_014` and `c_015` get a small ranking boost via:

```
final_rank = semantic_score + keyword_score + feedback_boost
```

— the system gets marginally better at surfacing good evidence over time, without any model retraining.

---

## Counter-Example — The Abstention Case

Worth showing in your demo too: if Priya instead asked *"What was the model's exact training cost in dollars?"* and the paper never mentions cost, **every** candidate chunk fails the similarity threshold at Step 4. No evidence survives, so:

```json
{
  "answer": "Insufficient evidence was found in the uploaded documents.",
  "confidence": 20,
  "status": "INSUFFICIENT_EVIDENCE",
  "citations": [],
  "evidence": []
}
```

This is the strongest thing to demonstrate to examiners: **the system refuses rather than fabricates** — the core trustworthiness claim of the whole project, directly enabled by the CA-RAG similarity-validation gate at Step 4.

---

## Why This Is Specific to Research Papers (not a generic chatbot)

- **Page/section-level citations** rely on structure only academic PDFs reliably have (numbered sections, page-fixed figures/results).
- **Adaptive chunking** respects paper structure (Abstract → Methodology → Results) rather than naive fixed-length splitting, which matters because claims in papers are section-scoped (a number in Results means something different than the same number in Related Work).
- **Abstention on insufficient evidence** matters specifically for research use — a student citing a hallucinated "fact" from a paper in their own thesis is a real, high-cost failure mode this design targets.
- **Feedback learning per chunk** improves future answers *for that specific paper's chunk set*, which is meaningful at the scale of one/few papers a student is working closely with — unlike a general web chatbot where feedback signal is diffuse.
