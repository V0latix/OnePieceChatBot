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
PYTHONPATH=src uvicorn api.main:app --reload
```

6. Frontend (dans un second terminal)

```bash
cd frontend
npm install
npm run dev
```

## Production (backend perso + ngrok)

Le frontend est deploye sur Vercel (`one-piece-chatbot.vercel.app`), mais le
backend tourne en local et est expose au frontend via un tunnel ngrok. Si le
Mac est redemarre ou le terminal ferme, l'appli en ligne retombe en erreur
(CORS / 404) tant que le backend + ngrok ne sont pas relances.

### Procedure de redemarrage

1. **Backend** (terminal 1) — depuis la racine du repo :

```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Attendre le message `Application startup complete.`

2. **Tunnel ngrok** (terminal 2) — avec le domaine statique reserve :

```bash
ngrok http --url=overdistant-colloquial-leonora.ngrok-free.dev 8000
```

> Si ta version de ngrok ne connait pas `--url`, utilise
> `--domain=overdistant-colloquial-leonora.ngrok-free.dev` a la place.

Le frontend Vercel pointe vers ce domaine via la variable
`NEXT_PUBLIC_API_BASE_URL` (configuree dans les env vars du projet Vercel). Le
domaine ngrok doit donc rester identique a chaque redemarrage.

### Verification

```bash
# Doit renvoyer {"status":"ok","chunks_count":...,"graph_nodes":...}
curl -H "ngrok-skip-browser-warning: 1" \
  https://overdistant-colloquial-leonora.ngrok-free.dev/api/health

# Preflight CORS : doit renvoyer HTTP 200
curl -o /dev/null -w "%{http_code}\n" -X OPTIONS \
  https://overdistant-colloquial-leonora.ngrok-free.dev/api/ask/stream \
  -H "Origin: https://one-piece-chatbot.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Une fois ces deux checks OK, le chat fonctionne sur `one-piece-chatbot.vercel.app`.

> Note Vercel : le projet doit avoir **Root Directory = `frontend`** et aucun
> override de Build/Install/Output Command (sinon la detection de Next.js
> echoue avec `No Next.js version detected`).

## Donnees locales

Les artefacts generes par le pipeline (`data/raw`, `data/chunks`, `data/graph`, `data/processed`) sont ignores par git. Apres un clone propre, il faut relancer le scraping, le chunking/embedding et le build graph, ou restaurer ces dossiers depuis une sauvegarde locale.

Sans credentials Qdrant, l'API peut utiliser `data/chunks/chunks_with_embeddings.jsonl` comme fallback vectoriel local. Sans Groq/Ollama joignable, la generation retourne un extrait du meilleur contexte retrouve.

## Tests

```bash
.venv/bin/python -m pytest -q
```
