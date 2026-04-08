# TODO — OnePiece RAG

## 🔴 Critique (bloque la prod)

### [X] Uploader les vecteurs dans Qdrant
Le cluster est vide. Les 250 chunks locaux doivent être uploadés pour que le RAG fonctionne en prod.
```bash
source .venv/bin/activate
python scripts/03_chunk_and_embed.py
```
> Si tu veux plus de données, relance d'abord le scraping complet : `python scripts/01_scrape.py`

### [X] Implémenter le filtre anti-spoiler dans le pipeline RAG
`spoiler_limit_arc` est accepté par l'API mais ignoré (`_ = spoiler_limit_arc` dans `dependencies.py:102` et `:153`).
Il faut filtrer les chunks dont l'arc est postérieur à l'arc limite avant le reranking.

---

## 🟠 Important (qualité & robustesse)

### [X] Scraping complet du wiki
Actuellement limité à `--max-pages 20`. Lancer le scraping complet pour avoir une base de connaissance riche.
```bash
python scripts/01_scrape.py  # sans --max-pages pour tout scraper
python scripts/03_chunk_and_embed.py
python scripts/04_build_graph.py
```

### [X] Implémenter scripts/06_eval.py (évaluation qualité)
Prévu dans `Instruction.md` mais jamais créé. Mesurer precision/recall du RAG sur un jeu de questions de référence One Piece.

### [X] Implémenter src/scraper/sbs_scraper.py
Le fichier existe mais n'a que 28 lignes (stub). Les SBS (Q&A d'Oda) sont une source précieuse pour les anecdotes et relations entre personnages.

### [X] Mise à jour Next.js 14 → 15
Vulnérabilité critique signalée à chaque build Vercel. Voir [security update](https://nextjs.org/blog/security-update-2025-12-11).
```bash
cd frontend && npm install next@latest react@latest react-dom@latest
```

---

## 🟡 Améliorations (nice to have)

### [X] CI/CD GitHub Actions
Pas de `.github/workflows/`. Ajouter un workflow minimal :
- `pytest` sur push
- `npm run build && npm run lint` sur push
- Smoke test import Python (cf. recommandation Codex review)

### [X] Caching des requêtes fréquentes
Les questions répétées (`"Qui est Luffy ?"`) refont tout le pipeline. Ajouter un cache LRU en mémoire sur les 100 dernières réponses dans `RAGService`.

### [X] Rate limiting sur l'API
Pas de protection contre les abus. Ajouter `slowapi` sur `/api/ask` et `/api/ask/stream` (ex: 10 req/min par IP).

### [X] Gérer l'expiration du cluster Qdrant
Le cluster est supprimé après 4 semaines d'inactivité. Ajouter un script de "ping" hebdomadaire ou documenter la procédure de ré-upload depuis le JSONL local.

### [X] UI pour l'endpoint /api/search
`GET /api/search?q=...` existe côté backend mais aucun composant frontend ne l'utilise. Ajouter une barre de recherche directe dans le frontend.

### [X] Mettre à jour CLAUDE.md
Plusieurs sections sont obsolètes (références à Supabase, structure des imports `src.xxx`).

---

## 📋 Rappels techniques

| Commande | Usage |
|---|---|
| `python scripts/01_scrape.py --max-pages 20` | Scraping partiel (dev) |
| `python scripts/03_chunk_and_embed.py` | Upload vecteurs → Qdrant |
| `python scripts/04_build_graph.py` | Rebuild graphe Neo4j |
| `uvicorn api.main:app --reload` | Démarrer le backend |
| `ngrok http 8000` | Exposer le backend (prod perso) |
| `cd frontend && vercel deploy --prod` | Déployer le frontend |
| `.venv/bin/python -m pytest` | Lancer les tests |
