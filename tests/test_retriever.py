"""Tests unitaires pour le retriever hybride."""

from __future__ import annotations

import json

from config.settings import Settings, get_settings
from rag.retriever import HybridRetriever, _graph_match, _is_noise_entity, _is_noise_section


class DummyEmbedder:
    """Embedder factice deterministe pour les tests."""

    def embed_query(self, _query: str) -> list[float]:
        return [1.0, 0.0]


class RecordingEmbedder:
    """Capture le texte reellement embarque (pour verifier l'isolation HyDE)."""

    def __init__(self) -> None:
        self.last_text: str | None = None

    def embed_query(self, query: str) -> list[float]:
        self.last_text = query
        return [1.0, 0.0]


def _one_chunk_index(tmp_path):
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    row = {
        "chunk_id": "luffy__001", "entity_id": "luffy", "entity_name": "Monkey D. Luffy",
        "entity_type": "character", "section": "abilities",
        "content": "Luffy maitrise le haki.", "categories": ["Characters"],
        "related_entities": [], "token_count": 6,
        "source_url": "https://example.com", "embedding": [1.0, 0.0],
    }
    with index_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    return index_path


class _MapEmbedder:
    """Embedder texte->vecteur (table), enregistre les appels (test dual retrieval)."""

    def __init__(self, mapping: dict) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.calls.append(query)
        return self.mapping.get(query, [0.0, 0.0])


def _two_chunk_index(tmp_path):
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    rows = [
        {"chunk_id": "A", "entity_id": "a", "entity_name": "A", "entity_type": "character",
         "section": "overview", "content": "aaa", "categories": ["Characters"],
         "related_entities": [], "token_count": 1, "source_url": "x", "embedding": [1.0, 0.0]},
        {"chunk_id": "B", "entity_id": "b", "entity_name": "B", "entity_type": "character",
         "section": "overview", "content": "bbb", "categories": ["Characters"],
         "related_entities": [], "token_count": 1, "source_url": "x", "embedding": [0.0, 1.0]},
    ]
    with index_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return index_path


def test_dual_retrieval_rescues_question_match(tmp_path) -> None:
    # question->A, hyde->B. En dual, A (match question) doit etre remonte au max cosinus.
    embedder = _MapEmbedder({"question": [1.0, 0.0], "hyde": [0.0, 1.0]})
    retriever = HybridRetriever(
        settings=Settings(hyde_dual=True), embedder=embedder, vector_store=None,
        local_embeddings_path=_two_chunk_index(tmp_path),
    )
    results = retriever.retrieve("question", entities=[], top_k=5, embed_text="hyde")
    assert "question" in embedder.calls and "hyde" in embedder.calls  # les deux embarques
    by_id = {r.chunk_id: r for r in results}
    assert by_id["A"].vector_score == 1.0  # A recupere via la question
    assert by_id["B"].vector_score == 1.0  # B via HyDE


def test_dual_off_embeds_only_hyde(tmp_path) -> None:
    embedder = _MapEmbedder({"question": [1.0, 0.0], "hyde": [0.0, 1.0]})
    retriever = HybridRetriever(
        settings=Settings(hyde_dual=False), embedder=embedder, vector_store=None,
        local_embeddings_path=_two_chunk_index(tmp_path),
    )
    retriever.retrieve("question", entities=[], top_k=5, embed_text="hyde")
    assert embedder.calls == ["hyde"]  # seul le passage HyDE est embarque (single)


def test_embed_text_isolated_to_dense_channel(tmp_path) -> None:
    # embed_text (HyDE) sert a la recherche dense ; le keyword reste sur la question.
    embedder = RecordingEmbedder()
    retriever = HybridRetriever(
        settings=get_settings(), embedder=embedder, vector_store=None,
        local_embeddings_path=_one_chunk_index(tmp_path),
    )
    results = retriever.retrieve("haki", entities=[], top_k=5, embed_text="HYDE english passage")
    # Le dense a bien embarque le passage HyDE, pas la question brute.
    assert embedder.last_text == "HYDE english passage"
    # Le keyword a bien matche le terme "haki" de la QUESTION (pas du passage HyDE).
    assert any(r.keyword_score > 0 for r in results)


def test_retriever_uses_local_index_and_scores_keyword(tmp_path) -> None:
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    rows = [
        {
            "chunk_id": "luffy__001",
            "entity_id": "luffy",
            "entity_name": "Monkey D. Luffy",
            "entity_type": "character",
            "section": "abilities",
            "content": "Luffy utilise Gear 5 et le Haki des rois.",
            "categories": ["Characters"],
            "related_entities": ["Kaido"],
            "token_count": 15,
            "source_url": "https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
            "embedding": [1.0, 0.0],
        },
        {
            "chunk_id": "zoro__001",
            "entity_id": "zoro",
            "entity_name": "Roronoa Zoro",
            "entity_type": "character",
            "section": "abilities",
            "content": "Zoro maitrise le Santoryu.",
            "categories": ["Characters"],
            "related_entities": ["Mihawk"],
            "token_count": 8,
            "source_url": "https://onepiece.fandom.com/wiki/Roronoa_Zoro",
            "embedding": [0.0, 1.0],
        },
    ]
    with index_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")

    retriever = HybridRetriever(
        settings=get_settings(),
        embedder=DummyEmbedder(),
        vector_store=None,
        local_embeddings_path=index_path,
    )

    results = retriever.retrieve("Que sait faire Luffy avec son haki ?", entities=["Monkey D. Luffy"], top_k=5)

    assert results
    top = max(results, key=lambda row: row.vector_score)
    assert top.entity_name == "Monkey D. Luffy"
    assert any(row.keyword_score > 0 for row in results)


# --- Fix A: filtrage des sections/pages de bruit -----------------------------


def test_is_noise_section_flags_navigation():
    assert _is_noise_section("site_navigation")
    assert _is_noise_section("external_links")
    assert _is_noise_section("references")
    assert not _is_noise_section("overview")
    assert not _is_noise_section("abilities_and_powers.devil_fruit")


def test_is_noise_entity_flags_non_canonical_pages():
    assert _is_noise_entity("Roronoa Zoro/Gallery")
    assert _is_noise_entity("Roronoa Zoro/Misc.")
    assert _is_noise_entity("Volume Zoro")
    assert _is_noise_entity("Forum:Nightmare Luffy")
    assert _is_noise_entity("Episode 492")
    assert not _is_noise_entity("Roronoa Zoro")
    assert not _is_noise_entity("Monkey D. Luffy")


# --- Fix B: match strict entite <-> page -------------------------------------


def test_graph_match_exact_and_multiword_prefix():
    # Egalite exacte
    assert _graph_match(["Roronoa Zoro"], "Roronoa Zoro")
    # Entite multi-mots prefixant une (hypothetique) sous-page
    assert _graph_match(["Roronoa Zoro"], "Roronoa Zoro/Misc.")


def test_graph_match_rejects_single_word_substring():
    # "Zoro" seul ne doit PAS matcher "Volume Zoro" (ancien bug du `in`)
    assert not _graph_match(["Zoro"], "Volume Zoro")


def test_retrieve_excludes_noise_pages_and_sections(tmp_path):
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    rows = [
        {
            "chunk_id": "zoro__overview__001",
            "entity_id": "zoro",
            "entity_name": "Roronoa Zoro",
            "entity_type": "character",
            "section": "overview",
            "content": "Roronoa Zoro est un epeiste de l'equipage de Luffy.",
            "categories": ["Characters"],
            "related_entities": [],
            "token_count": 12,
            "source_url": "https://onepiece.fandom.com/wiki/Roronoa_Zoro",
            "embedding": [1.0, 0.0],
        },
        {
            "chunk_id": "volzoro__nav__001",
            "entity_id": "volume_zoro",
            "entity_name": "Volume Zoro",
            "entity_type": "unknown",
            "section": "site_navigation",
            "content": "Roronoa Zoro navigation menu links.",
            "categories": [],
            "related_entities": [],
            "token_count": 8,
            "source_url": "https://onepiece.fandom.com/wiki/Volume_Zoro",
            "embedding": [1.0, 0.0],
        },
    ]
    with index_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")

    retriever = HybridRetriever(
        settings=get_settings(),
        embedder=DummyEmbedder(),
        vector_store=None,
        local_embeddings_path=index_path,
    )
    results = retriever.retrieve("Qui est Zoro ?", entities=["Roronoa Zoro", "Zoro"], top_k=5)

    names = {row.entity_name for row in results}
    assert "Roronoa Zoro" in names
    assert "Volume Zoro" not in names  # page de bruit exclue


# --- BM25 : le terme rare doit primer sur le terme frequent -------------------


def test_bm25_rewards_rare_term(tmp_path):
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    # "haki" n'apparait que dans un doc (rare, IDF eleve) ; "pirate" partout.
    rows = [
        {
            "chunk_id": f"c{i}",
            "entity_id": f"e{i}",
            "entity_name": f"Perso {i}",
            "entity_type": "character",
            "section": "overview",
            "content": "pirate pirate pirate haki" if i == 0 else "pirate pirate pirate",
            "categories": ["Characters"],
            "related_entities": [],
            "token_count": 4,
            "source_url": "https://example.com",
            "embedding": [0.0, 0.0],
        }
        for i in range(5)
    ]
    with index_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")

    retriever = HybridRetriever(
        settings=get_settings(),
        embedder=DummyEmbedder(),
        vector_store=None,
        local_embeddings_path=index_path,
    )
    query_terms = {"pirate", "haki"}
    rare = retriever._keyword_score(query_terms, "pirate haki")
    common_only = retriever._keyword_score(query_terms, "pirate pirate")
    # Le doc contenant le terme rare "haki" doit scorer plus haut.
    assert rare > common_only
