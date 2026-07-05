# TODO — Améliorations du RAG

Backlog priorisé pour le pipeline de retrieval du chatbot One Piece.
Chaque piste : **quoi · gain attendu · coût/effort (stack gratuite locale M4) · fichiers · source**.

> Règle d'or : **mesurer avant/après** (section 0). Sans golden set, on ne saura pas si un
> changement aide vraiment — on garde uniquement ce qui bouge les chiffres.

## État actuel (base de référence)

Pipeline online (`src/api/dependencies.py` → `RAGService.ask`) :
extraction d'entités (règles) → retrieval hybride → rerank pondéré → filtre spoiler →
graphe Neo4j (prompt seulement) → génération (Groq → Ollama → snippet).

Faiblesses qui motivent ce backlog :

| # | Faiblesse | Où |
|---|-----------|----|
| 1 | Rerank = somme linéaire non calibrée `0.4·vec + 0.4·graph + 0.2·kw`, pas de cross-encoder ; signal graphe binaire (0/1) qui domine | `src/rag/reranker.py:19` |
| 2 | Keyword = simple ratio de recouvrement d'ensembles, pas de BM25/IDF | `src/rag/retriever.py` `_keyword_score` |
| 3 | Pas de vraie fusion : scores collectés puis pondérés (pas de RRF) | `src/rag/retriever.py` / `reranker.py` |
| 4 | Aucune query transformation (pas de HyDE / multi-query / décomposition) | — |
| 5 | Graphe Neo4j sous-exploité : n'influence jamais le classement, sert au prompt | `src/rag/graph_retriever.py` |
| 6 | Fallback vecteur local = cosinus O(N) en Python pur | `src/rag/retriever.py` `_local_vector_search` |
| 7 | Extraction d'entités rule-based, aucune tolérance fautes/alias manquants | `src/rag/entity_extractor.py` |
| 8 | Citations non vérifiées : le LLM cite `[i]` sans grounding programmatique | `src/rag/prompt_builder.py` |
| 9 | Modèle Groq périmé (`llama-3.1-70b-versatile` décommissionné) | `src/config/settings.py:43` |
| 10 | Aucune évaluation : ni golden set ni métrique | — |
| 11 | Tests absents sur reranker / generator / graph_retriever | `tests/` |

---

## 0. Mesurer d'abord (pré-requis, bloquant)

- **Golden set + RAGAS.** Constituer 50–200 Q/R One Piece vérifiées à la main (multi-hop,
  spoilers, filler vs canon, questions globales). Scorer avec **RAGAS** : *context precision,
  context recall, faithfulness, answer relevancy*. RAGAS peut aussi générer un jeu de départ synthétique.
  - **Gain :** rend tout le reste mesurable ; sans ça les gains sont invisibles.
  - **Coût :** golden set = travail manuel ; juge LLM via Groq (free tier suffit).
  - **Fichiers :** nouveau `scripts/07_eval_ragas.py`, réutilise `scripts/06_eval.py`.
  - **Source :** https://docs.ragas.io — alt. TruLens "RAG triad", DeepEval pour CI.

---

## 1. Tier 1 — meilleur ratio impact/effort

- **Contextual Retrieval (Anthropic).** Préfixer chaque chunk d'un blurb LLM d'1–2 phrases
  ("où ce passage se situe dans la page") **avant** embedding et indexation BM25.
  - **Gain :** −35 % d'échecs de retrieval (embeddings seuls), −49 % avec BM25 contextuel.
  - **Coût :** passe offline unique via Groq/Ollama (gratuit) ; prompt caching si API payante.
  - **Fichiers :** `src/processing/chunker.py`, `src/processing/embedder.py`.
  - **Source :** https://www.anthropic.com/engineering/contextual-retrieval

- **Fusion RRF** à la place de la somme pondérée. Fusionner vecteur + BM25 (+ graphe) **par rang** :
  `score = Σ 1/(k + rang)`, k≈60. Robuste aux scores d'échelles différentes (cosinus vs ratio vs binaire).
  - **Gain :** bat systématiquement la pondération manuelle ; plus de poids à régler à la main.
  - **Coût :** trivial, Python pur. Garder une variante *weighted RRF* si on veut biaiser le graphe.
  - **Fichiers :** `src/rag/reranker.py`, `src/rag/retriever.py`.
  - **Source :** https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/

- **Vrai BM25** en remplacement du ratio d'overlap (TF + IDF, vs simple intersection d'ensembles).
  - **Gain :** meilleur rappel lexical, gère fréquence et rareté des termes.
  - **Coût :** faible. Deux options : **sparse vectors Qdrant** (indexé côté serveur) ou `rank_bm25` local.
  - **Fichiers :** `src/rag/retriever.py`, `src/processing/vector_store.py`.

- **Cross-encoder `bge-reranker-v2-m3`** en 2e étage. Retrieve top-50 → rerank (query, chunk) → garder 8–10.
  - **Gain :** le plus gros lift unitaire dans la plupart des ablations RAG (c'est l'étape "+reranking → −67 %").
  - **Coût :** modèle 0.6B, tourne en fp16 (`FlagReranker(use_fp16=True)`) ou MLX sur M4. Plafonner le
    nombre de candidats car scoring par paire plus lent.
  - **Fichiers :** `src/rag/reranker.py`.
  - **Source :** https://huggingface.co/BAAI/bge-reranker-v2-m3

---

## 2. Tier 2 — gains ciblés

- **Personalized PageRank (HippoRAG).** Seeder un PPR sur le graphe Neo4j depuis les entités
  extraites de la question, classer les passages par proximité graphe.
  - **Gain :** intègre enfin le graphe au **classement** (aujourd'hui il ne sert qu'au prompt) ;
    fort sur les questions multi-hop ("comment X est lié à Y") sans appel LLM supplémentaire.
  - **Coût :** faible — `gds.pageRank` avec `sourceNodes`, ou NetworkX PPR côté CPU. ~10× moins cher
    à indexer que GraphRAG.
  - **Fichiers :** `src/rag/graph_retriever.py`, `src/rag/retriever.py`.
  - **Source :** https://github.com/OSU-NLP-Group/HippoRAG

- **Query transformation** (activée selon le type de question, pas systématique) :
  - **Multi-query + RRF** par défaut : le LLM écrit 3–4 reformulations, on retrieve chacune et on fusionne.
  - **Décomposition** si un routeur détecte une question multi-parties ("compare X et Y").
  - **HyDE** pour les questions descriptives (générer une réponse hypothétique, embarquer celle-ci).
  - **Gain :** rappel/couverture d'intention en hausse. **Coût :** 1+ appel LLM Groq + latence.
  - **Fichiers :** nouveau `src/rag/query_transformer.py`, branché dans `RAGService`.
  - **Source :** https://arxiv.org/pdf/2404.01037 (ARAGOG)

- **Résumés hiérarchiques (RAPTOR) + community summaries (GraphRAG global).** Construire offline des
  nœuds "résumé d'arc / de personnage / de thème" et les ajouter à Qdrant + Neo4j.
  - **Gain :** répond aux questions **globales** que le RAG plat rate ("résume l'arc de Marineford",
    "comment évolue l'équipage de Luffy").
  - **Coût :** summarization offline unique (tokens modérés via Groq/Ollama).
  - **Fichiers :** nouveau `scripts/08_build_summaries.py`.
  - **Sources :** https://github.com/parthsarthi03/raptor · https://microsoft.github.io/graphrag/query/global_search/

---

## 3. Tier 3 — robustesse & qualité

- **Grounding des citations.** Vérifier après génération que chaque `[i]` cité correspond à un
  chunk réellement fourni ; sinon signaler / abaisser la confiance.
  - **Fichiers :** `src/rag/prompt_builder.py`, post-génération dans `src/rag/generator.py`.

- **Entités : fuzzy matching** (`rapidfuzz`) + éventuel NER léger pour tolérer fautes de frappe et
  alias non listés (ex. "Zolo" vs "Zoro").
  - **Fichiers :** `src/rag/entity_extractor.py`.

- **Corriger le modèle Groq périmé** (`llama-3.1-70b-versatile` → `llama-3.3-70b-versatile`) et
  documenter clairement le fallback. Déjà noté dans CLAUDE.md — à câbler proprement.
  - **Fichiers :** `src/config/settings.py`, `.env.example`.

- **ANN local** (`hnswlib` ou `faiss`) pour le fallback hors-ligne, au lieu du cosinus O(N) Python.
  - **Fichiers :** `src/rag/retriever.py`.

- **Tests manquants** : reranker (formule/tri), chaîne de fallback du generator, graph_retriever mické.
  - **Fichiers :** `tests/`.

---

## 4. Annexe — projets comparables (quoi voler)

| Projet | Technique | Quoi voler | Adoptable gratuit/local |
|--------|-----------|-----------|:---:|
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | Communautés (Leiden) + résumés ; local/global/DRIFT search | Le **local search** (déjà via Neo4j) + **community summaries** pour les questions thématiques | ⚠️ indexing très gourmand en tokens |
| [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) | Personalized PageRank sur KG passage+entité | **Le PPR** — meilleur fit pour toi (cf. §2) | ✅ léger, CPU |
| [LightRAG](https://github.com/HKUDS/LightRAG) | Dual-level retrieval (entités + relations/thèmes) | Design des prompts de requête dual-level | ✅ supporte Ollama + embeddings locaux |
| [RAPTOR](https://github.com/parthsarthi03/raptor) | Arbre récursif de résumés (clustering + summarize) | Nœuds résumé multi-niveaux dans Qdrant | ✅ build offline unique |
| [LlamaIndex PropertyGraphIndex](https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex) | Graph property + retrievers modulaires (Neo4j) | Référence pour valider ton retriever Neo4j maison | ✅ (framework) |
| [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) | Blurb contextuel avant embedding + BM25 | **La technique entière** (cf. §1) | ✅ ~1 $/1M tokens ou gratuit local |

**Modèles locaux (M4) :** `bge-large-en-v1.5` (actuel) reste solide ; upgrade possible vers **bge-m3**
(dense + sparse + ColBERT en un modèle, idéal pour l'hybride, multilingue). Runtime : **MLX ~50 % plus
rapide que llama.cpp** sur workloads d'embedding Apple Silicon.

---

## 5. Roadmap minimale suggérée

1. **Golden set + RAGAS** (baseline du pipeline actuel 0.4/0.4/0.2)
2. ✅ **RRF + BM25** (`reranker.py` / `retriever.py`) — fait
3. **Contextual retrieval** (`chunker.py` / `embedder.py`)
4. **bge-reranker-v2-m3** en 2e étage
5. **PPR graphe** (`graph_retriever.py`)
6. **Résumés RAPTOR + community summaries** (offline)

Re-mesurer après **chaque** étape. Ne garder que ce qui améliore les métriques RAGAS.

> **Fait (slice code pur, sans re-embedding ni deps lourdes) :** RRF (`reranker.py`),
> vrai BM25 (`retriever.py`), grounding des citations (`prompt_builder.py`),
> fuzzy entités via `difflib` (`entity_extractor.py`), modèle Groq à jour
> (`settings.py`). Confiance = cosinus moyen × ratio de grounding.
> Restent ouverts : §0 golden set/RAGAS, §1 contextual retrieval + cross-encoder,
> §2 PPR/query-transform/RAPTOR, §3 ANN local.
