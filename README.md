# One Piece RAG

RAG expert sur l'univers One Piece, base sur scraping Fandom + embeddings locaux + Qdrant Cloud + knowledge graph Neo4j + generation via Groq/Ollama.

## Prerequis

- Python 3.11+
- Compte Qdrant Cloud
- Compte Neo4j Aura (free)
- Cle API Groq, ou Ollama local pour le fallback

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

2. Chunking + embeddings + upload Qdrant

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

6. Frontend (dans un second terminal)

```bash
cd frontend
npm install
npm run dev
```

## Donnees locales

Les artefacts generes par le pipeline (`data/raw`, `data/chunks`, `data/graph`, `data/processed`) sont ignores par git. Apres un clone propre, il faut relancer le scraping, le chunking/embedding et le build graph, ou restaurer ces dossiers depuis une sauvegarde locale.

Sans credentials Qdrant, l'API peut utiliser `data/chunks/chunks_with_embeddings.jsonl` comme fallback vectoriel local. Sans Groq/Ollama joignable, la generation retourne un extrait du meilleur contexte retrouve.

## Tests

```bash
.venv/bin/python -m pytest -q
```
