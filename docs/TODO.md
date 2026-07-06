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
| 1 | ~~Rerank somme linéaire + graphe binaire~~ ✅ RRF + cross-encoder + graph_score continu (PPR) | `src/rag/reranker.py` |
| 2 | ~~Keyword = ratio d'overlap~~ ✅ vrai BM25 (TF·IDF) | `src/rag/retriever.py` `_keyword_score` |
| 3 | ~~Pas de vraie fusion~~ ✅ fusion RRF | `src/rag/retriever.py` / `reranker.py` |
| 4 | ~~Aucune query transformation~~ ✅ HyDE (passage hypothétique EN pour le dense) — **Hit@5 68→92 %, Recall@5 88→100 %** | `src/rag/query_transformer.py` |
| 5 | ⚠️ Graphe replié dans le classement (PPR opt-in) **mais effet non prouvé** ; Neo4j live → sert encore au prompt | `src/rag/graph_ranker.py` |
| 6 | Fallback vecteur local = cosinus O(N) en Python pur | `src/rag/retriever.py` `_local_vector_search` |
| 7 | ~~Extraction d'entités rule-based~~ ✅ collisions résolues (prior d'importance) + alias hors-titre minés du lede ("Aokiji"→Kuzan, "Whitebeard"→Edward Newgate) | `src/rag/entity_extractor.py` |
| 8 | ~~Citations non vérifiées~~ ✅ grounding programmatique (`grounded_ratio`) | `src/rag/prompt_builder.py` |
| 9 | ~~Modèle Groq périmé~~ ✅ `llama-3.3-70b-versatile` | `src/config/settings.py` |
| 10 | ~~Aucune évaluation~~ ✅ golden set **61 Q** (durci) + `06_eval` (Hit@K/Recall@K/seed, `--sleep`/`--limit`) + `07_eval_ragas` | `data/eval/`, `scripts/` |
| 11 | ⚠️ Tests reranker ✅ + graph_ranker ✅ ; reste generator (chaîne fallback) / graph_retriever | `tests/` |

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

1. ✅ **Golden set + eval** (`data/eval/golden.jsonl`, `scripts/06_eval.py` réparé, `scripts/07_eval_ragas.py`) — fait, variante *lean* (juge Groq, sans dépendance ragas)
2. ✅ **RRF + BM25** (`reranker.py` / `retriever.py`) — fait
3. ❌ **Contextual retrieval v1** (préfixe templaté, `chunker.py`) — testé, **régresse** (Hit@5 68→52 %), rollback ; blurb LLM à tester
4. ✅ **bge-reranker-v2-m3** en 2e étage (`CrossEncoderReranker`, opt-in `RERANK_CROSS_ENCODER=1`) — fait
5. ⚠️ **PPR graphe** (`graph_ranker.py`, opt-in `GRAPH_PPR=1`) — implémenté mais **effet non prouvé** (graphe co-occurrence dégénéré), laissé OFF
6. **Résumés RAPTOR + community summaries** (offline)
7. ✅ **HyDE** (§2 query transformation, `query_transformer.py`, opt-in `HYDE=1`) — **plus gros gain** (Hit@5 68→92 %, Recall@5 88→100 %)

Re-mesurer après **chaque** étape. Ne garder que ce qui améliore les métriques RAGAS.

> **Fait (slice code pur, sans re-embedding ni deps lourdes) :** RRF (`reranker.py`),
> vrai BM25 (`retriever.py`), grounding des citations (`prompt_builder.py`),
> fuzzy entités via `difflib` (`entity_extractor.py`), modèle Groq à jour
> (`settings.py`). Confiance = cosinus moyen × ratio de grounding.
> **Fait (mesure) :** golden set JSONL (`data/eval/golden.jsonl`, 25 Q taggées
> factual/multi-hop/global/canon/spoiler), `06_eval.py` réparé (Hit@K/Recall@K sur RRF),
> `07_eval_ragas.py` (faithfulness + answer_relevancy via juge Groq, sans lib ragas).
> Baseline actuel : **Hit@5 64 %, Recall@5 88 %** ; faithfulness ~0.5, relevancy ~0.83.
> **Fait (cross-encoder §4) :** `CrossEncoderReranker` (bge-reranker-v2-m3) 2e étage,
> opt-in `RERANK_CROSS_ENCODER=1`, dégradation gracieuse vers RRF si modèle absent.
> Mesure A/B (n=10) : la métrique retrieval par nom d'entité est **aveugle** (Hit@5 plat),
> mais la **génération** progresse nettement — faithfulness 0.50→0.63, relevancy 0.56→0.81.
> Verdict : garder, activer en prod.
> **Fait (résolution d'entités §3/#7) :** collisions d'alias arbitrées par un prior
> d'importance (`len(related_entities)` du doc raw) dans `entity_extractor.py` :
> "luffy"→Monkey D. Luffy (145) au lieu de Nightmare Luffy (1), "law"→Trafalgar D. Water Law.
> Mesure : seed accuracy 72 %, **Hit@5 64 %→68 %** (CE off, n=25), suite 143 verte.
> Nouveau : métrique *seed accuracy* dans `06_eval.py`. Débloque un futur §5 PPR (seeds corrects).
> **Fait (alias hors-titre) :** minés du lede wiki ("X, known by his alias Y, is…") pour les
> pages perso, importance-aware (n'écrase pas un titre canonique). "Aokiji"→Kuzan,
> "Kizaru/Akainu/Ryokugyu/Fujitora" (les 5 amiraux), "Whitebeard"→Edward Newgate.
> Mesure : **seed accuracy 72 %→80 %** (CE off, n=25), Hit@5 plat, suite 147 verte.
> Note : le plein bénéfice (graph_context, fetch_relations) est en sommeil tant que
> Neo4j est mort ; effet runtime actuel = entités affichées correctes + boost graphe minime.
> **Fait (§5 PPR + Neo4j live) :** Neo4j Aura de nouveau up (7708 nœuds / 99345 arêtes) →
> `graph_context` réactivé automatiquement. `GraphRanker` (NetworkX PPR sur `triplets.jsonl`,
> GDS indispo sur Aura Free) branché comme `graph_score` continu, replié dans RRF comme 3e
> signal classé (refactor reranker, **0 régression** vs binaire). **Mesure A/B (CE off, n=25) :
> Hit@5 68 % et Recall@5 88 % INCHANGÉS** ; A/B génération bloqué (Groq HS pendant le test).
> Verdict : **effet non prouvé** — le graphe est un co-occurrence non typé (tout `RELATED_TO`),
> PPR n'a quasi pas de signal exploitable. Laissé **OFF** (`GRAPH_PPR=0`). À revisiter APRÈS
> reconstruction du graphe (relations typées + nœuds passages), là où PPR paie vraiment.
> **Testé & rejeté (§1 contextual retrieval v1) :** préfixe templaté sans LLM
> ("Page: X (type). Section: Y.") anteposé à chaque chunk, re-embed complet des 36 949
> chunks (~2 h). Mesure A/B locale (CE+PPR off) : **Hit@5 68 %→52 %, Recall@5 88 %→84 %** —
> le boilerplate répété dilue les embeddings. Rollback (backup restauré, Qdrant jamais
> touché grâce à `--dry-run`). Toggle `CHUNK_CONTEXTUAL` gardé OFF. Leçon : la version
> lean templatée ne marche pas ici ; seul un vrai blurb LLM par chunk vaut la peine d'être retenté.
> **Fait (§2 HyDE) — plus gros gain de la série :** `QueryTransformer.hyde` génère un
> passage hypothétique **anglais** (1 appel Groq) embarqué pour la recherche **dense**
> uniquement (keyword/BM25 + graphe restent sur la question FR). Comble l'écart question
> FR / corpus+modèle EN. Mesure A/B locale (CE+PPR off) : **Hit@5 68→92 %, Recall@5 88→100 %**
> (métrique non-aveugle, n=25) ; génération (n≈6, espacé) : faithfulness 0.46→0.87,
> relevancy 0.76→0.88. Opt-in `HYDE=1` (activé en prod), +1 appel Groq/requête, fallback
> gracieux sur la question brute si Groq HS. Prochaine étape naturelle : multi-query + RRF.
> **Fait (§0 golden set durci) :** 25 → **61 questions** (ajout descriptive-sans-nom,
> multi-hop, disambiguation/vrai-nom, devil-fruit, global, spoiler, faction). Motif : HyDE
> avait **saturé** l'ancien set (Recall@5 100 %), plus rien à mesurer. Nouveau plancher
> **sans Groq (HYDE/CE off) : Hit@5 52,5 %, Recall@5 67,2 %, seed 52,5 %** (n=61) → la
> résolution est revenue. `06_eval` gagne `--sleep`/`--limit`. **HyDE sur le set durci = à
> mesurer** (quota journalier Groq free épuisé pendant la session ; relancer avec
> `HYDE=1 06_eval --sleep 8` quand le quota se réinitialise). Le gain HyDE prouvé reste
> celui du set n=25 (Hit@5 68→92 %, Recall@5 88→100 %).
> Restent ouverts : mesurer HyDE/CE sur n=61, §2 multi-query/RAPTOR, §3 ANN local + graphe typé.
