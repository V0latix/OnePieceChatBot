# ONE PIECE RAG — Instructions Claude Code

## Contexte projet

Tu construis un **RAG (Retrieval-Augmented Generation) expert sur l'univers One Piece**, capable de répondre à n'importe quelle question sur le manga/anime avec précision, en citant ses sources (arcs, chapitres, wiki). Le projet doit être **100% gratuit** et tourner sur un MacBook Air M4.

Le développeur est un étudiant français en actuariat, expérimenté en Python et TypeScript, qui utilise Supabase, des VPS, et maîtrise les architectures de données propres. Il veut un code **maintenable, modulaire, bien structuré**, avec des formats JSON stricts et une architecture scalable.

---

## Stack technique

| Composant | Technologie | Raison |
|---|---|---|
| Langage principal | **Python 3.11+** | Écosystème ML/NLP dominant |
| Scraping | **Scrapy** + **BeautifulSoup4** | Scraping robuste du wiki Fandom |
| Chunking | **LangChain** `RecursiveCharacterTextSplitter` | Chunking sémantique avec overlap |
| Embeddings | **sentence-transformers** (`BAAI/bge-large-en-v1.5`) | Modèle local gratuit, 1024 dims, top qualité |
| Vector Store | **Supabase** (pgvector) | Free tier 500 Mo, suffisant pour ~50k chunks |
| Knowledge Graph | **Neo4j** (Aura free tier) | 200k nœuds gratuits, parfait pour les relations OP |
| LLM (inférence) | **Groq API** (Llama 3.1 70B) | Gratuit, rapide, bonne qualité |
| Backend API | **FastAPI** | Async, rapide, Python natif |
| Frontend | **Next.js 14** + **Tailwind CSS** | Déploiement Vercel gratuit |
| Gestion deps | **uv** ou **pip + venv** | Environnement isolé |

---

## Structure du projet

```
onepiece-rag/
├── README.md
├── pyproject.toml                 # ou requirements.txt
├── .env.example                   # Variables d'environnement template
├── .gitignore
│
├── src/
│   ├── __init__.py
│   │
│   ├── scraper/                   # Phase 1 : Collecte des données
│   │   ├── __init__.py
│   │   ├── fandom_spider.py       # Spider Scrapy pour le wiki Fandom One Piece
│   │   ├── sbs_scraper.py         # Scraper pour les SBS (Q&A d'Oda)
│   │   ├── cleaner.py             # Nettoyage HTML → texte structuré
│   │   ├── categorizer.py         # Classification automatique (personnage, arc, lieu, etc.)
│   │   └── exporter.py            # Export en JSON structuré
│   │
│   ├── processing/                # Phase 2 : Traitement et indexation
│   │   ├── __init__.py
│   │   ├── chunker.py             # Chunking sémantique avec métadonnées
│   │   ├── embedder.py            # Génération d'embeddings (local, sentence-transformers)
│   │   ├── vector_store.py        # Interface Supabase pgvector (CRUD embeddings)
│   │   └── graph_builder.py       # Construction du knowledge graph Neo4j
│   │
│   ├── rag/                       # Phase 3 : Pipeline RAG
│   │   ├── __init__.py
│   │   ├── retriever.py           # Retrieval hybride (vector + keyword + graph)
│   │   ├── reranker.py            # Reranking des résultats
│   │   ├── entity_extractor.py    # Extraction d'entités nommées One Piece
│   │   ├── graph_retriever.py     # Requêtes Cypher sur Neo4j
│   │   ├── prompt_builder.py      # Construction du prompt avec contexte
│   │   └── generator.py           # Appel LLM (Groq/Ollama) et génération de réponse
│   │
│   ├── api/                       # Phase 4 : Backend API
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── ask.py             # POST /api/ask — question → réponse RAG
│   │   │   ├── entity.py          # GET /api/entity/{name} — fiche entité
│   │   │   ├── graph.py           # GET /api/graph/{entity} — sous-graphe
│   │   │   └── health.py          # GET /api/health
│   │   ├── models.py              # Pydantic schemas (request/response)
│   │   └── dependencies.py        # Injection de dépendances
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Config centralisée (pydantic-settings)
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py              # Logging structuré
│
├── data/
│   ├── raw/                       # Données brutes scrapées (JSON)
│   ├── processed/                 # Données nettoyées et catégorisées
│   ├── chunks/                    # Chunks avec métadonnées
│   └── graph/                     # Export des triplets pour Neo4j
│
├── scripts/
│   ├── 01_scrape.py               # Lance le scraping complet
│   ├── 02_process.py              # Nettoyage + catégorisation
│   ├── 03_chunk_and_embed.py      # Chunking + embedding + upload Supabase
│   ├── 04_build_graph.py          # Construction du knowledge graph Neo4j
│   ├── 05_test_rag.py             # Test du pipeline RAG complet
│   └── 06_eval.py                 # Évaluation qualité (precision/recall)
│
├── tests/
│   ├── test_scraper.py
│   ├── test_chunker.py
│   ├── test_retriever.py
│   └── test_rag_pipeline.py
│
└── frontend/                      # Next.js app (séparé)
    ├── package.json
    ├── next.config.js
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx            # Page principale chat
    │   │   └── layout.tsx
    │   ├── components/
    │   │   ├── ChatInterface.tsx
    │   │   ├── EntityCard.tsx
    │   │   ├── GraphViewer.tsx
    │   │   └── SpoilerFilter.tsx
    │   └── lib/
    │       └── api.ts              # Client API
    └── tailwind.config.js
```

---

## Phase 1 — Scraping du wiki Fandom One Piece

### Objectif
Scraper toutes les pages pertinentes de `https://onepiece.fandom.com/wiki/` et les stocker en JSON structuré.

### Pages à scraper

Les catégories principales à cibler (URLs Fandom) :

```
# Personnages
https://onepiece.fandom.com/wiki/Category:Characters
https://onepiece.fandom.com/wiki/List_of_Canon_Characters

# Fruits du Démon
https://onepiece.fandom.com/wiki/Category:Devil_Fruits

# Équipages / Organisations
https://onepiece.fandom.com/wiki/Category:Pirate_Crews
https://onepiece.fandom.com/wiki/Category:Marine
https://onepiece.fandom.com/wiki/Category:World_Government

# Arcs narratifs
https://onepiece.fandom.com/wiki/Category:Story_Arcs

# Lieux
https://onepiece.fandom.com/wiki/Category:Locations

# Techniques / Haki / Abilities
https://onepiece.fandom.com/wiki/Category:Fighting_Styles
https://onepiece.fandom.com/wiki/Haki

# Objets importants
https://onepiece.fandom.com/wiki/Category:Objects

# Races
https://onepiece.fandom.com/wiki/Category:Races

# Événements majeurs
https://onepiece.fandom.com/wiki/Category:Events
```

### Méthode de scraping

Utiliser l'**API MediaWiki** de Fandom (plus fiable que le scraping HTML direct) :

```
# API endpoint
https://onepiece.fandom.com/api.php

# Récupérer le contenu d'une page
?action=parse&page=Monkey_D._Luffy&format=json&prop=wikitext|categories

# Lister les pages d'une catégorie
?action=categorymembers&cmtitle=Category:Characters&cmlimit=500&format=json

# Récupérer le contenu brut (wikitext)
?action=query&titles=Monkey_D._Luffy&prop=revisions&rvprop=content&format=json
```

**Alternative** : utiliser les dumps Fandom si disponibles (`Special:Statistics` de chaque wiki).

### Format de sortie (JSON strict)

Chaque page scrapée doit produire un fichier JSON avec cette structure :

```json
{
  "id": "monkey_d_luffy",
  "title": "Monkey D. Luffy",
  "url": "https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
  "type": "character",
  "categories": ["Straw Hat Pirates", "Super Rookies", "Yonko", "D. Bearers"],
  "infobox": {
    "japanese_name": "モンキー・D・ルフィ",
    "romanized_name": "Monkī Dī Rufi",
    "epithet": "Straw Hat",
    "bounty": "3,000,000,000",
    "devil_fruit": "Gomu Gomu no Mi (Hito Hito no Mi, Model: Nika)",
    "affiliation": "Straw Hat Pirates",
    "occupation": "Captain",
    "origin": "East Blue, Foosha Village",
    "age": "19",
    "height": "174 cm",
    "birthday": "May 5",
    "blood_type": "F",
    "status": "Alive"
  },
  "sections": {
    "appearance": "Luffy is a young man of average height...",
    "personality": "Luffy's most prominent trait...",
    "relationships": "Luffy has formed bonds with...",
    "abilities_and_powers": "Luffy possesses immense physical strength...",
    "history": {
      "early_life": "Luffy was born in Foosha Village...",
      "romance_dawn_arc": "Luffy set out from Foosha Village...",
      "alabasta_arc": "..."
    },
    "major_battles": ["Luffy vs. Crocodile", "Luffy vs. Katakuri", "Luffy vs. Kaido"],
    "trivia": "..."
  },
  "related_entities": ["Straw Hat Pirates", "Gomu Gomu no Mi", "Monkey D. Dragon", "Garp"],
  "last_scraped": "2026-03-27T12:00:00Z"
}
```

### Nettoyage requis

Le cleaner doit :
- Supprimer les balises HTML résiduelles, navbars, footers, références `[1]`, liens internes `[[...]]`
- Convertir le wikitext en texte propre
- Extraire les infobox en dictionnaire structuré
- Séparer le contenu par sections (en utilisant les headers `== ... ==` du wikitext)
- Détecter et catégoriser automatiquement le type d'entité (character, location, devil_fruit, arc, crew, etc.)
- Extraire les entités mentionnées dans le texte pour `related_entities`
- Normaliser les noms (ex: "Luffy" → "Monkey D. Luffy")

### Contraintes techniques

- **Rate limiting** : respecter un délai de 1-2 secondes entre chaque requête API Fandom
- **Gestion des erreurs** : retry avec backoff exponentiel sur les erreurs 429/500
- **Reprise** : pouvoir reprendre le scraping là où il s'est arrêté (sauvegarder l'état)
- **Logs** : logger chaque page scrapée avec son statut (succès/échec/skip)
- **Encodage** : UTF-8 strict, gérer les caractères japonais correctement

---

## Phase 2 — Chunking, Embedding et Indexation

### Chunking

Chaque document JSON de la Phase 1 est découpé en chunks intelligents :

```python
# Stratégie de chunking
# 1. Chaque section majeure (appearance, personality, history...) = 1 chunk minimum
# 2. Si une section dépasse 500 tokens, la découper avec RecursiveCharacterTextSplitter
# 3. Overlap de 50 tokens entre sous-chunks d'une même section
# 4. Chaque chunk porte ses métadonnées complètes

chunk_schema = {
    "chunk_id": "monkey_d_luffy__abilities_and_powers__001",
    "entity_id": "monkey_d_luffy",
    "entity_name": "Monkey D. Luffy",
    "entity_type": "character",
    "section": "abilities_and_powers",
    "content": "Luffy possesses immense physical strength...",
    "categories": ["Straw Hat Pirates", "Yonko"],
    "related_entities": ["Gomu Gomu no Mi", "Haki", "Gear 5"],
    "token_count": 387,
    "source_url": "https://onepiece.fandom.com/wiki/Monkey_D._Luffy"
}
```

### Embedding

```python
# Modèle : BAAI/bge-large-en-v1.5
# Dimensions : 1024
# Tourne en local sur le Mac M4 via sentence-transformers
# Pour les requêtes, préfixer avec "Represent this sentence: " (spécifique à bge)

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-large-en-v1.5")
embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
```

### Upload Supabase pgvector

Créer la table dans Supabase :

```sql
-- Activer l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Table principale des chunks
CREATE TABLE op_chunks (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    categories TEXT[] DEFAULT '{}',
    related_entities TEXT[] DEFAULT '{}',
    token_count INTEGER,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index HNSW pour la recherche vectorielle rapide
CREATE INDEX ON op_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index pour la recherche par entité
CREATE INDEX idx_entity_id ON op_chunks (entity_id);
CREATE INDEX idx_entity_type ON op_chunks (entity_type);

-- Index GIN pour la recherche dans les catégories
CREATE INDEX idx_categories ON op_chunks USING GIN (categories);

-- Fonction de recherche vectorielle
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding VECTOR(1024),
    match_count INT DEFAULT 5,
    filter_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id TEXT,
    entity_name TEXT,
    entity_type TEXT,
    section TEXT,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.entity_name,
        c.entity_type,
        c.section,
        c.content,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM op_chunks c
    WHERE (filter_type IS NULL OR c.entity_type = filter_type)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## Phase 3 — Knowledge Graph (Neo4j)

### Schéma du graphe

**Node labels :**
- `Character` (name, epithet, bounty, status, age, origin, debut_arc)
- `DevilFruit` (name, type [Paramecia/Zoan/Logia], awakened)
- `Crew` (name, captain, ship, jolly_roger)
- `Arc` (name, saga, chapters_start, chapters_end, location)
- `Location` (name, sea [East/West/North/South/Grand Line/New World/Red Line])
- `Technique` (name, type [Haki/DevilFruit/Physical/Sword])
- `Race` (name)
- `Weapon` (name, type)
- `Organization` (name, type [Marine/Government/Revolutionary/Underworld])
- `Event` (name, arc, description)

**Relationships :**
```cypher
// Personnages
(Character)-[:MEMBER_OF]->(Crew)
(Character)-[:ATE]->(DevilFruit)
(Character)-[:ALLIED_WITH]->(Character)
(Character)-[:FOUGHT]->(Character)
(Character)-[:CHILD_OF]->(Character)
(Character)-[:SIBLING_OF]->(Character)
(Character)-[:MENTOR_OF]->(Character)
(Character)-[:USES]->(Technique)
(Character)-[:WIELDS]->(Weapon)
(Character)-[:BELONGS_TO_RACE]->(Race)
(Character)-[:BORN_IN]->(Location)
(Character)-[:APPEARED_IN]->(Arc)
(Character)-[:MEMBER_OF_ORG]->(Organization)
(Character)-[:PARTICIPATED_IN]->(Event)
(Character)-[:HAS_BOUNTY {amount: 3000000000}]->(Crew)

// Arcs
(Arc)-[:TAKES_PLACE_IN]->(Location)
(Arc)-[:PART_OF_SAGA {saga_name: "Water 7"}]->(Arc)
(Arc)-[:NEXT_ARC]->(Arc)

// Fruits
(DevilFruit)-[:TYPE_OF {category: "Mythical Zoan"}]->(DevilFruit)

// Techniques
(Technique)-[:DERIVED_FROM]->(Technique)
(Technique)-[:REQUIRES]->(DevilFruit)
```

### Construction du graphe

Extraire les triplets (sujet, relation, objet) depuis :
1. Les `infobox` des pages scrapées (relations structurées fiables)
2. Les `related_entities` détectées dans le texte
3. Un prompt LLM pour extraire les relations implicites depuis les sections textuelles

```python
# Exemple de triplets extraits de l'infobox de Luffy
triplets = [
    ("Monkey D. Luffy", "MEMBER_OF", "Straw Hat Pirates"),
    ("Monkey D. Luffy", "ATE", "Gomu Gomu no Mi"),
    ("Monkey D. Luffy", "CHILD_OF", "Monkey D. Dragon"),
    ("Monkey D. Luffy", "BORN_IN", "Foosha Village"),
    ("Monkey D. Luffy", "APPEARED_IN", "Romance Dawn Arc"),
    ("Monkey D. Luffy", "USES", "Gear 5"),
    ("Monkey D. Luffy", "USES", "Conqueror's Haki"),
]
```

### Connexion Neo4j

```python
from neo4j import GraphDatabase

# Neo4j Aura free tier
URI = "neo4j+s://xxxxx.databases.neo4j.io"
AUTH = ("neo4j", "password")

driver = GraphDatabase.driver(URI, auth=AUTH)
```

---

## Phase 4 — Pipeline RAG

### Architecture du retrieval

```
Question utilisateur
    │
    ├──[1] Entity Extraction
    │       Extraire les entités nommées One Piece de la question
    │       Ex: "Quel est le fruit de Law ?" → ["Trafalgar Law", "fruit du démon"]
    │
    ├──[2] Graph Retrieval (si entités détectées)
    │       Requête Cypher sur Neo4j pour récupérer les relations directes
    │       Ex: MATCH (c:Character {name: "Trafalgar Law"})-[:ATE]->(df) RETURN df
    │
    ├──[3] Vector Search (toujours)
    │       Recherche des top-K chunks similaires dans Supabase pgvector
    │       Avec filtre optionnel sur entity_type si pertinent
    │
    ├──[4] Keyword Search (BM25, optionnel)
    │       Recherche full-text sur les noms propres (important pour One Piece
    │       car les noms sont très spécifiques et les embeddings peuvent les rater)
    │
    └──[5] Reranking
            Combiner et réordonner les résultats avec un cross-encoder
            ou un simple scoring pondéré (graph_score * 0.4 + vector_score * 0.4 + keyword_score * 0.2)
            
            → Top-K contextes assemblés → envoyés au LLM
```

### Prompt système

```python
SYSTEM_PROMPT = """Tu es un expert encyclopédique de l'univers One Piece, le manga créé par Eiichiro Oda.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir du contexte fourni ci-dessous. Ne fabrique JAMAIS d'information.
2. Si le contexte ne contient pas la réponse, dis-le clairement : "Je n'ai pas trouvé cette information dans ma base de données."
3. Cite tes sources : mentionne l'arc, le chapitre ou la section wiki quand c'est possible.
4. Distingue toujours le CANON (manga) du FILLER (anime uniquement) et des THÉORIES (fan-made).
5. Sois précis sur les noms : utilise les noms complets (ex: "Monkey D. Luffy", pas juste "Luffy") au moins à la première mention.
6. Si l'utilisateur a configuré un filtre anti-spoiler, ne mentionne AUCUN événement après l'arc indiqué.
7. Réponds en français sauf si l'utilisateur pose sa question en anglais.
8. Pour les questions de comparaison ou de classement, structure ta réponse clairement.

CONTEXTE :
{context}

DONNÉES DU GRAPHE (relations entre entités) :
{graph_context}
"""
```

### Appel LLM via Groq

```python
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(question: str, context: str, graph_context: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(
                context=context, graph_context=graph_context
            )},
            {"role": "user", "content": question}
        ],
        temperature=0.3,
        max_tokens=2048
    )
    return response.choices[0].message.content
```

### Fallback LLM local (Ollama)

Si Groq est down ou rate-limité, fallback automatique sur Ollama :

```python
import httpx

def generate_answer_local(question: str, context: str, graph_context: str) -> str:
    response = httpx.post("http://localhost:11434/api/chat", json={
        "model": "llama3.1:8b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(
                context=context, graph_context=graph_context
            )},
            {"role": "user", "content": question}
        ],
        "stream": False,
        "options": {"temperature": 0.3}
    })
    return response.json()["message"]["content"]
```

---

## Phase 5 — API FastAPI

### Endpoints

```python
# POST /api/ask
# Body: {"question": "Quel est le fruit du démon de Law ?", "spoiler_limit_arc": "Wano"}
# Response: {"answer": "...", "sources": [...], "entities": [...], "confidence": 0.92}

# GET /api/entity/{entity_name}
# Response: {"name": "Trafalgar Law", "type": "character", "infobox": {...}, "relations": [...]}

# GET /api/graph/{entity_name}?depth=2
# Response: {"nodes": [...], "edges": [...]}

# GET /api/search?q=haki&type=technique
# Response: {"results": [...]}

# GET /api/health
# Response: {"status": "ok", "chunks_count": 45000, "graph_nodes": 3500}
```

---

## Phase 6 — Frontend (Next.js)

### Pages et composants

```
/ (page.tsx)
├── ChatInterface        # Zone de chat principale
│   ├── MessageBubble    # Bulle de message (user/bot)
│   ├── SourceCitation   # Citation cliquable vers le wiki
│   └── LoadingIndicator
│
├── EntityCard           # Fiche détaillée d'une entité
│   ├── InfoboxDisplay   # Affichage des infos clés (bounty, fruit, etc.)
│   ├── RelationsList    # Relations avec autres entités
│   └── SectionTabs      # Onglets (Apparence, Histoire, Capacités...)
│
├── GraphViewer          # Visualisation du knowledge graph
│   └── D3ForceGraph     # Graphe interactif D3.js/vis.js
│
└── SpoilerFilter        # Sélecteur d'arc max pour filtrer les spoilers
```

### Design

- Thème **pirate / One Piece** : couleurs chaudes (rouge, or, bleu marine)
- Dark mode par défaut
- Responsive mobile
- Animations subtiles sur les réponses du chat

---

## Variables d'environnement (.env)

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx

# Groq (LLM gratuit)
GROQ_API_KEY=gsk_xxxxx

# Optionnel : Ollama local (fallback)
OLLAMA_BASE_URL=http://localhost:11434

# App
LOG_LEVEL=INFO
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
LLM_MODEL=llama-3.1-70b-versatile
CHUNK_SIZE=500
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
```

---

## Dépendances Python (requirements.txt)

```
# Scraping
scrapy>=2.11
beautifulsoup4>=4.12
lxml>=5.0

# NLP & Embeddings
sentence-transformers>=3.0
torch>=2.1
langchain>=0.3
langchain-community>=0.3
tiktoken>=0.7

# Vector Store
supabase>=2.0
vecs>=0.4

# Knowledge Graph
neo4j>=5.20

# LLM
groq>=0.9
httpx>=0.27

# API
fastapi>=0.115
uvicorn>=0.30
pydantic>=2.7
pydantic-settings>=2.4

# Utils
python-dotenv>=1.0
rich>=13.0            # Pretty logging
tqdm>=4.66            # Progress bars
```

---

## Ordre d'exécution

**Commence par la Phase 1.** Implémente les modules dans cet ordre :

1. `src/config/settings.py` — Configuration centralisée avec pydantic-settings
2. `src/utils/logger.py` — Logger avec `rich`
3. `src/scraper/fandom_spider.py` — Spider principal
4. `src/scraper/cleaner.py` — Nettoyage wikitext → texte propre
5. `src/scraper/categorizer.py` — Classification automatique
6. `src/scraper/exporter.py` — Export JSON structuré
7. `scripts/01_scrape.py` — Script orchestrateur

**Puis Phase 2 :**
8. `src/processing/chunker.py`
9. `src/processing/embedder.py`
10. `src/processing/vector_store.py`
11. `scripts/03_chunk_and_embed.py`

**Puis Phase 3 :**
12. `src/processing/graph_builder.py`
13. `scripts/04_build_graph.py`

**Puis Phase 4 :**
14. `src/rag/entity_extractor.py`
15. `src/rag/graph_retriever.py`
16. `src/rag/retriever.py`
17. `src/rag/reranker.py`
18. `src/rag/prompt_builder.py`
19. `src/rag/generator.py`
20. `scripts/05_test_rag.py`

**Puis Phase 5 :**
21. `src/api/models.py`
22. `src/api/dependencies.py`
23. `src/api/routes/*.py`
24. `src/api/main.py`

**Frontend en dernier (Phase 6).**

---

## Critères de qualité

- **Type hints** partout, Python 3.11+ syntax
- **Docstrings** sur chaque fonction publique
- **Logging** structuré avec `rich`, pas de `print()`
- **Gestion d'erreurs** : try/except avec messages clairs, retry sur les appels réseau
- **Tests** : au minimum des tests unitaires sur le chunker, l'entity extractor, et le retriever
- **Format JSON strict** : validation Pydantic sur toutes les données
- **Pas de secrets en dur** : tout dans `.env`, jamais committé
- **Modularité** : chaque module doit être testable et utilisable indépendamment
- **Commentaires en français** dans le code (le développeur est français)

---

## Notes importantes

- Le wiki Fandom One Piece est en **anglais**. Les données seront en anglais, mais le RAG doit pouvoir répondre en **français** (le LLM gère la traduction).
- Le scraping doit respecter le `robots.txt` de Fandom et les rate limits.
- Pour la Phase 1, commence par scraper un **sous-ensemble** (ex: les 20 personnages principaux + les Straw Hats) pour valider le pipeline avant de lancer le scraping complet.
- Le modèle d'embedding `bge-large-en-v1.5` fonctionne mieux quand on préfixe la query avec `"Represent this sentence for retrieval: "`.
- Neo4j Aura free tier a un timeout d'inactivité (pause après quelques jours sans requête). Prévoir un mécanisme de reconnexion.