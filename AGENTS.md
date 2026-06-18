# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

**Setup:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in credentials
```

**Data pipeline (run in order):**
```bash
python scripts/01_scrape.py --max-pages 20   # scrape Fandom wiki
python scripts/03_chunk_and_embed.py         # chunk + embed + upload to Qdrant
python scripts/04_build_graph.py             # build Neo4j knowledge graph
python scripts/05_test_rag.py --question "..." # end-to-end RAG test
python scripts/06_eval.py --top-k 5         # retrieval quality evaluation
```

**Backend API:**
```bash
uvicorn api.main:app --reload   # run from repo root (PYTHONPATH=src is set via .env)
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
cd frontend && npm run build && npm run lint
```

**Tests:**
```bash
.venv/bin/python -m pytest -q           # all tests
.venv/bin/python -m pytest tests/test_retriever.py -q  # single file
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) system for answering questions about the One Piece universe. All components are designed to run free on a MacBook Air M4.

### Data Flow

**Offline pipeline:**
```
Fandom Wiki (MediaWiki API)
  → src/scraper/fandom_spider.py    (scrape with retry/backoff)
  → src/scraper/cleaner.py          (HTML/wikitext cleaning)
  → src/scraper/categorizer.py      (auto-detect entity types)
  → data/raw/*.json

  → src/processing/chunker.py       (token-aware splitting, 500 tok / 50 overlap)
  → src/processing/embedder.py      (BAAI/bge-large-en-v1.5, 1024 dims)
  → src/processing/vector_store.py  (upload to Qdrant Cloud)
  → data/chunks/chunks_with_embeddings.jsonl  (local cosine fallback)

  → src/processing/graph_builder.py (extract triplets from infoboxes)
  → Neo4j Aura                      (UPSERT nodes/edges)
  → data/graph/*.jsonl              (exported triplets)
```

**Online query (POST /api/ask):**
```
Question
  → src/rag/entity_extractor.py     (rule-based NER from data/raw/)
  → src/rag/retriever.py            (hybrid: vector + keyword + graph signals)
      ├─ Qdrant Cloud search (primary)
      └─ Local JSONL cosine similarity (fallback)
  → src/rag/spoiler_filter.py       (arc-based spoiler filtering, applied post-rerank)
  → src/rag/reranker.py             (0.4*vector + 0.4*graph + 0.2*keyword)
  → src/rag/graph_retriever.py      (Neo4j Cypher queries)
  → src/rag/prompt_builder.py       (assemble context + citations)
  → src/rag/generator.py            (Groq → Ollama → context snippet fallback)
  → AskResponse (answer + sources + entities + confidence)
```

### Key Design Decisions

**Fallback chain throughout:** Qdrant → local JSONL for vectors; Groq → Ollama → snippet for LLM. The system degrades gracefully when external services are unavailable.

**Dependency injection:** `src/api/dependencies.py` holds a singleton `RAGService` that lazy-loads embeddings and the retrieval stack on first request (not at startup) to keep the health endpoint fast.

**Reranking weights:** `final_score = 0.4*vector + 0.4*graph + 0.2*keyword` — graph signals are intentionally weighted equally to vector similarity because entity-entity relationships are central to One Piece lore questions.

**Entity extraction:** Rule-based (not ML), builds an alias map from `data/raw/` documents supporting short names, last names, and full name variants. Used to boost graph signals during retrieval.

### API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/ask` | Main RAG query → answer + sources + entities + confidence |
| `GET /api/entity/{name}` | Entity detail (name, type, infobox, relations) |
| `GET /api/graph/{entity}?depth=2` | Subgraph for D3 visualization |
| `GET /api/search?q=...` | Raw chunk retrieval |
| `GET /api/health` | System health (chunk count, graph nodes) |

### Frontend

Next.js 16 + React 19 + Tailwind CSS + TypeScript. Key components:
- `ChatInterface.tsx` — main Q&A loop
- `GraphViewer.tsx` + `D3ForceGraph.tsx` — interactive knowledge graph
- `SpoilerFilter.tsx` — arc-based spoiler limiting (sends `spoiler_limit_arc` to backend)
- `SearchBar.tsx` — direct chunk search via `GET /api/search`
- `lib/api.ts` — all API calls to the backend

Frontend talks to the backend at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

### Configuration

All settings loaded via pydantic-settings from `src/config/settings.py`. Key env vars: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`, `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`, `GROQ_API_KEY`, `OLLAMA_BASE_URL`, `EMBEDDING_MODEL`, `LLM_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RETRIEVAL_TOP_K`.
