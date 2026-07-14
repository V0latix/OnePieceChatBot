# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
python scripts/upload_qdrant_from_jsonl.py   # re-upload vectors to Qdrant WITHOUT re-embedding
```

**Backend API:**
```bash
PYTHONPATH=src uvicorn api.main:app --reload   # run from repo root; PYTHONPATH=src is required
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
  → src/rag/noise.py                (shared non-canon filter: nav/SBS/forum/gallery pages)
  → src/rag/retriever.py            (hybrid: vector + keyword + graph signals)
      ├─ Qdrant Cloud search (primary)
      └─ Local JSONL cosine similarity (fallback)
  → src/rag/reranker.py             (RRF fusion of vector + BM25 rankings + graph bias)
  → src/rag/graph_retriever.py      (Neo4j Cypher queries)
  → src/rag/prompt_builder.py       (assemble context + citations)
  → src/rag/generator.py            (Groq → Ollama → context snippet fallback)
  → AskResponse (answer + sources + entities + confidence)
```

### Key Design Decisions

**Fallback chain throughout:** Qdrant → local JSONL for vectors; Groq → Ollama → snippet for LLM. The system degrades gracefully when external services are unavailable.

**Dependency injection:** `src/api/dependencies.py` holds a singleton `RAGService` that lazy-loads embeddings and the retrieval stack on first request (not at startup) to keep the health endpoint fast.

**Reranking = Reciprocal Rank Fusion (RRF):** `final_score = Σ 1/(k+rank)` over the vector-similarity ranking and the BM25 lexical ranking (k=`RERANK_RRF_K`, default 60), plus a `RERANK_GRAPH_BOOST · 1/(k+1)` bias when an extracted entity matches the chunk. RRF is robust to the heterogeneous score scales (cosine vs BM25 vs binary graph) and needs no hand-tuned weights. Confidence is derived from mean top-k cosine similarity, then scaled by citation-grounding ratio (fraction of `[i]` citations that point to a real source).

**Entity extraction:** Rule-based (not ML), builds an alias map from `data/raw/` documents supporting short names, last names, and full name variants. Used to boost graph signals during retrieval.

### API Endpoints

Routes live in `src/api/routes/*.py` (one file per resource); the `slowapi` limiter is a singleton in `src/api/limiter.py`.

| Endpoint | Purpose |
|---|---|
| `POST /api/ask` | Main RAG query → answer + sources + entities + confidence |
| `POST /api/ask/stream` | Same as /ask but streams SSE (events: metadata, token, done) |
| `GET /api/entity/{name}` | Entity detail (name, type, infobox, relations) |
| `GET /api/graph/{entity}?depth=2` | Subgraph (no frontend consumer since the graph viewer was removed) |
| `GET /api/search?q=...` | Raw chunk retrieval |
| `GET /api/health` | System health (chunk count, graph nodes) |

### Frontend

Next.js 16 + React 19 + Tailwind v3 + shadcn/ui + TypeScript. Key components:
- `ChatInterface.tsx` — main Q&A loop
- `SearchBar.tsx` — direct chunk search via `GET /api/search`
- `components/ui/*` — shadcn primitives (button, input, card, tabs, badge)
- `lib/api.ts` — all API calls to the backend

**Theme = light brutalist** (`mytheme.md`): flat surfaces, hard black borders, `--radius: 0`, no shadows, Syne (display) + Space Mono (body), accent `#1a56db`. Tokens are HSL CSS vars in `src/app/globals.css`, wired into `tailwind.config.js`. No dark mode.

Frontend talks to the backend at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

### Configuration

All settings loaded via pydantic-settings from `src/config/settings.py`. Key env vars: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`, `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`, `GROQ_API_KEY`, `GROQ_MODEL`, `OLLAMA_BASE_URL`, `EMBEDDING_MODEL`, `LLM_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RETRIEVAL_TOP_K`.

### Gotchas

- **Neo4j Aura username = DB-ID, not `neo4j`.** `NEO4J_USER` must be the instance DB-ID (from the downloaded Aura credentials file). Using `neo4j` gives `AuthError` even with a correct password.
- **Groq model names get decommissioned.** Default is now `groq_model=llama-3.3-70b-versatile`; if Groq retires it too, set `GROQ_MODEL` in .env to a current model. Symptom of a dead model: 400 BadRequest.
- **`/api/ask` is rate-limited to 10/min** (slowapi, keyed by IP). Load tests or rapid manual testing hit 429; loosen `@limiter.limit` in `src/api/routes/ask.py` if needed.
- **Qdrant Cloud & Neo4j Aura free clusters expire on inactivity.** After re-creating: re-run `04_build_graph.py` for Neo4j; for Qdrant use `upload_qdrant_from_jsonl.py` (re-uploads existing embeddings, no re-embed).
- **Production = local backend + ngrok.** Frontend is on Vercel; the backend runs locally and is exposed via a static ngrok domain. See README "Production" section. Vercel project needs Root Directory = `frontend`.
