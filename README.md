# One Piece RAG

RAG expert sur l'univers One Piece, base sur scraping Fandom + embeddings locaux + pgvector (Supabase) + knowledge graph (Neo4j) + generation via Groq.

## Prerequis

- Python 3.11+
- Compte Supabase (pgvector)
- Compte Neo4j Aura (free)
- Cle API Groq

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Pipeline

1. Scraping sous-ensemble

```bash
python scripts/01_scrape.py --max-pages 20
```

2. Chunking + embeddings + upload

```bash
python scripts/03_chunk_and_embed.py
```

3. Build graph Neo4j

```bash
python scripts/04_build_graph.py
```

4. Test pipeline RAG

```bash
python scripts/05_test_rag.py --question "Quel est le fruit du demon de Trafalgar Law ?"
```

5. API

```bash
uvicorn src.api.main:app --reload
```

## Tests

```bash
pytest -q
```
