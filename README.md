# CA-RAG — Trustworthy Research Paper QA System

A research-project implementation of **Context-Aware Retrieval Augmented
Generation (CA-RAG)**, based on the paper *"Context-Aware Retrieval
Augmented Generation Using Similarity Validation to Handle Context
Inconsistencies in Large Language Models."*

Users upload research papers (PDF) and ask questions about them. Answers
are generated **only** from evidence the system has validated against the
source text — if there isn't enough support, it says so instead of
guessing.

Five extended features on top of the core CA-RAG concept:
1. **Hallucination Detection** — per-claim support scoring + a transparent confidence formula
2. **Source Citation Generation** — every answer links back to real page/section/chunk
3. **Query Rewriting** — up to 3 intent-preserving rewrites to widen recall
4. **Adaptive Chunking** — chunk boundaries follow headings/semantic shifts, not fixed character counts
5. **Feedback Learning** — 👍/👎 nudges future retrieval ranking (bounded, no model training)

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, React Router, Axios |
| Backend / API | Python, FastAPI |
| RAG pipeline | Python (query rewriting, adaptive chunking, CA-RAG validation, hallucination detection, citation generation, feedback ranking) |
| PDF parsing | PyMuPDF |
| Embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS |
| App database | MongoDB (users, documents, conversations, feedback) |
| LLM | Ollama (local, default) or any OpenAI-compatible API |
| Auth | JWT + bcrypt |

No Node/Express backend, no agentic framework — the whole pipeline is
plain Python, deliberately kept simple enough to explain end-to-end in a
viva. See `USE_CASE_WALKTHROUGH.md` for a full worked example of the
pipeline, stage by stage.

## Project layout

```
project/
├── backend/     FastAPI app — see backend/app/services for the CA-RAG pipeline
└── frontend/    React + Vite app
```

Full backend structure:

```
backend/app/
├── main.py                 FastAPI entrypoint, CORS, router registration
├── config.py                Settings (reads .env)
├── routes/                  auth.py, documents.py, chat.py, feedback.py
├── models/                  Mongo document shape helpers
├── schemas/                 Pydantic request/response models
├── auth/                    JWT + bcrypt
├── database/                Mongo connection
└── services/
    ├── llm_client.py         Ollama / OpenAI-compatible abstraction
    ├── embeddings.py         Sentence-Transformers wrapper
    ├── vector_store.py       FAISS index per document
    ├── ingestion/            PDF loading + text cleaning
    ├── chunking/             Adaptive chunker
    ├── query/                Query rewriter
    ├── retrieval/            Candidate retrieval + ranking
    ├── carag/                Candidate generation + similarity validation (the core contribution)
    ├── synthesis/            Evidence-grounded answer generation (replaces agentic reasoning)
    ├── hallucination/        Claim-level support scoring + confidence formula
    ├── citation/             Citation + evidence-list builders
    └── feedback/             Bounded feedback-based ranking boost
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running locally (`mongod`) — or a connection string in `.env`
- **One of:**
  - [Ollama](https://ollama.com) running locally with a model pulled (`ollama pull llama3.1`), **or**
  - An OpenAI-compatible API key

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set MONGODB_URI, LLM_PROVIDER, and either OLLAMA_* or OPENAI_* values

uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. First request that touches
embeddings will download the `all-MiniLM-L6-v2` model (~90MB) — this
requires internet access once, then it's cached locally.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` calls to the
backend (see `vite.config.js`).

## Using it

1. Register an account, then log in.
2. Go to **Documents**, upload a PDF paper. Processing (extraction →
   cleaning → adaptive chunking → embedding → FAISS indexing) runs in the
   background; status flips from `Processing…` to `Ready`.
3. Go to **Chat**, pick the document, ask a question.
   - **Extended CA-RAG** mode runs the full pipeline (query rewriting →
     retrieval → per-chunk candidate generation → similarity validation →
     evidence synthesis → hallucination check → citations).
   - **Traditional RAG** mode skips validation, for the Mode 1 vs Mode 2
     comparison described in the assignment brief.
4. Rate answers with 👍/👎 — this nudges future retrieval ranking for that
   chunk (bounded, capped influence — see `feedback_learning.py`).

## Notes on the CA-RAG validation gate

For each retrieved chunk, the system asks the LLM to answer using *only*
that chunk, then checks how well the resulting answer's embedding aligns
with the chunk's own embedding (cosine similarity, threshold in
`VALIDATION_SIMILARITY_THRESHOLD`). Chunks that fail are dropped before
they ever reach the final answer — this is what lets the system say
"insufficient evidence" instead of fabricating, and it's the one thing
worth demonstrating clearly in a demo: ask something the paper doesn't
cover and watch it refuse rather than guess.

## Testing

```bash
cd backend
pip install pytest httpx
pytest
```

A starter test file is at `backend/tests/test_similarity.py` — extend it
with tests for the chunker and the CA-RAG validation threshold behavior.
