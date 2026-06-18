# AGENTS.md

Guidance for Codex/AI agents working in this repository.

## Project Snapshot

This repository is a One Piece RAG application with:

- Python/FastAPI backend in `src/`
- Offline data pipeline in `scripts/`
- Local generated data under `data/`
- Next.js frontend in `frontend/`
- Retrieval stack: Qdrant Cloud first, local JSONL cosine fallback
- Graph stack: Neo4j Aura for entity relations
- LLM stack: Groq first, Ollama fallback, context-snippet fallback

The project is designed to run locally on a MacBook Air M4 with free-tier external services.

## Important Repository Facts

- Run Python commands from the repository root.
- The Python import root is `src`; use `PYTHONPATH=src` when running app commands outside pytest.
- `pytest` gets `pythonpath = ["src"]` from `pyproject.toml`.
- Generated data is intentionally ignored by git:
  - `data/raw/*`
  - `data/processed/*`
  - `data/chunks/*`
  - `data/graph/*`
- Only the `.gitkeep` files under `data/` are versioned.
- A clean clone will not contain the scraped corpus, embeddings, or graph triplets.
- Do not commit `.env`, credentials, `.venv`, `.next`, `node_modules`, or generated pipeline data unless the user explicitly asks for an artifact export.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with the needed services:

- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `GROQ_API_KEY`
- `OLLAMA_BASE_URL`
- `GROQ_MODEL`
- `OLLAMA_MODEL`

External services are optional for some local flows because the app has fallbacks, but Qdrant upload and Neo4j graph writes require credentials.

## Common Commands

### Tests

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_retriever.py -q
```

Tests must not contact Qdrant, Neo4j, or Groq. `tests/conftest.py` clears those environment variables for pytest so tests stay deterministic even when a local `.env` contains real credentials.

### Backend

```bash
PYTHONPATH=src .venv/bin/uvicorn api.main:app --reload
```

Health endpoint:

```bash
curl -s http://localhost:8000/api/health
```

Main ask endpoint:

```bash
curl -s http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quel est le fruit du demon de Trafalgar Law ?"}'
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run build
```

The frontend reads `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`.

### Data Pipeline

Run from repo root, with `.venv` activated or `.venv/bin/python`.

```bash
PYTHONPATH=src .venv/bin/python scripts/01_scrape.py --max-pages 20
PYTHONPATH=src .venv/bin/python scripts/03_chunk_and_embed.py --dry-run
PYTHONPATH=src .venv/bin/python scripts/03_chunk_and_embed.py
PYTHONPATH=src .venv/bin/python scripts/04_build_graph.py
PYTHONPATH=src .venv/bin/python scripts/05_test_rag.py --question "Qui est Luffy ?"
PYTHONPATH=src .venv/bin/python scripts/06_eval.py --top-k 5 --verbose
```

Use `--dry-run` on `03_chunk_and_embed.py` when validating chunking/embedding without uploading to Qdrant.

## Architecture

### Offline Flow

```text
Fandom MediaWiki API
  -> src/scraper/fandom_spider.py
  -> src/scraper/cleaner.py
  -> src/scraper/categorizer.py
  -> data/raw/*.json

data/raw/*.json
  -> src/processing/chunker.py
  -> src/processing/embedder.py
  -> data/chunks/chunks.jsonl
  -> data/chunks/chunks_with_embeddings.jsonl
  -> src/processing/vector_store.py
  -> Qdrant Cloud

data/raw/*.json
  -> src/processing/graph_builder.py
  -> data/graph/triplets.jsonl
  -> Neo4j Aura
```

### Online Ask Flow

```text
POST /api/ask or /api/ask/stream
  -> api.dependencies.RAGService
  -> rag.entity_extractor.EntityExtractor
  -> rag.retriever.HybridRetriever
       -> Qdrant search if configured
       -> local data/chunks/chunks_with_embeddings.jsonl fallback
       -> keyword augmentation
       -> entity/graph signal
  -> rag.reranker.WeightedReranker
  -> rag.spoiler_filter.filter_by_spoiler_limit
  -> rag.graph_retriever.GraphRetriever
  -> rag.prompt_builder.PromptBuilder
  -> rag.generator.AnswerGenerator
       -> Groq
       -> Ollama
       -> retrieved context snippet
```

## Backend Details

- FastAPI app: `src/api/main.py`
- Route modules: `src/api/routes/`
- API schemas: `src/api/models.py`
- Service singleton and pipeline orchestration: `src/api/dependencies.py`
- Rate limiting: `src/api/limiter.py` using `slowapi`
- Settings: `src/config/settings.py`

Keep `GET /api/health` lightweight. Do not initialize embeddings or the full retriever stack in health checks.

`RAGService` lazy-loads the embedder/retriever on first real retrieval. Preserve that behavior unless there is a strong reason to change startup cost.

## RAG Components

- `src/rag/entity_extractor.py`: rule-based aliases from `data/raw`.
- `src/rag/retriever.py`: hybrid vector + keyword + entity signal retrieval.
- `src/rag/reranker.py`: weighted final score. Default weights must sum to 1.0.
- `src/rag/spoiler_filter.py`: arc-based post-rerank filtering.
- `src/rag/graph_retriever.py`: Neo4j reads for relations/subgraphs.
- `src/rag/prompt_builder.py`: builds context and messages.
- `src/rag/generator.py`: Groq/Ollama/snippet fallback chain and streaming.

When changing retrieval behavior, update or add tests for ranking, fallback behavior, and spoiler filtering.

## Data Model Expectations

Scraped raw documents should generally contain:

- `id`
- `title`
- `url`
- `type`
- `categories`
- `infobox`
- `sections`
- `related_entities`
- `last_scraped`

Chunk records should preserve enough metadata for citations and filtering:

- `chunk_id`
- `entity_id`
- `entity_name`
- `entity_type`
- `section`
- `content`
- `categories`
- `related_entities`
- `token_count`
- `source_url`

Embeddings use `BAAI/bge-large-en-v1.5` by default and are expected to be 1024-dimensional. Keep this aligned with Qdrant collection vector size in `src/processing/vector_store.py`.

## Frontend Details

- Next.js app router entry: `frontend/src/app/page.tsx`
- API client: `frontend/src/lib/api.ts`
- Chat UI: `frontend/src/components/ChatInterface.tsx`
- Direct search UI: `frontend/src/components/SearchBar.tsx`
- Spoiler filter UI: `frontend/src/components/SpoilerFilter.tsx`
- Graph UI: `frontend/src/components/GraphViewer.tsx` and `D3ForceGraph.tsx`

If API response shapes change, update both `src/api/models.py` and `frontend/src/lib/api.ts`.

## Quality Bar

Before finishing backend or shared logic changes, run:

```bash
.venv/bin/python -m pytest -q
```

Before finishing frontend changes, run:

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

If a build/test fails because of missing external credentials, prefer making the code/test use explicit fallbacks or mocks. Unit tests should not require live Qdrant, Neo4j, Groq, Ollama, or Fandom.

## Known Project-Specific Pitfalls

- `Settings` loads `.env`; tests must stay isolated from it.
- Qdrant is optional at query time only if `data/chunks/chunks_with_embeddings.jsonl` exists.
- A clean clone has no local vector fallback until `scripts/03_chunk_and_embed.py` has run.
- Neo4j relation lookups should degrade gracefully when credentials are absent or the DB is unreachable.
- The spoiler filter is intentionally conservative for `history.*` sections with unknown arcs.
- The SBS scraper is currently minimal; do not assume it extracts structured Q&A without checking `src/scraper/sbs_scraper.py`.
- Keep README, `.env.example`, `pyproject.toml`, and `requirements.txt` aligned when dependencies or env vars change.

## Coding Conventions

- Prefer small, focused changes that match the existing module boundaries.
- Keep fallback behavior explicit and tested.
- Do not introduce network calls in constructors unless there is already a clear fallback or the object is only created inside an explicit command.
- Avoid broad refactors while fixing pipeline or retrieval bugs.
- Keep Pydantic response models strict with `extra="forbid"` unless there is a clear API compatibility reason.
- Preserve French-facing UI text unless the user asks for a language change.
