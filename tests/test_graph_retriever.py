"""Tests du GraphRetriever : parsing Cypher + degradation gracieuse (Neo4j down)."""

from __future__ import annotations

from config.settings import get_settings
from rag.graph_retriever import GraphRetriever


class _FakeSession:
    """Session Neo4j factice (context manager) ; renvoie des rows ou leve."""

    def __init__(self, rows, raise_exc=None) -> None:  # noqa: ANN001
        self._rows = rows
        self._raise = raise_exc

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *_a) -> bool:
        return False

    def run(self, _query, _params=None):  # noqa: ANN001, ANN202
        if self._raise:
            raise self._raise
        return self._rows


class _FakeDriver:
    def __init__(self, rows, raise_exc=None) -> None:  # noqa: ANN001
        self._rows = rows
        self._raise = raise_exc
        self.closed = False

    def session(self):  # noqa: ANN201
        return _FakeSession(self._rows, self._raise)

    def close(self) -> None:
        self.closed = True


class _FakeRel:
    def __init__(self, start: str, end: str, rel_type: str) -> None:
        self.start_node = {"name": start}
        self.end_node = {"name": end}
        self.type = rel_type


def _retriever_with(rows, raise_exc=None) -> GraphRetriever:
    r = GraphRetriever(get_settings())
    r._driver = _FakeDriver(rows, raise_exc)  # connect() court-circuite a True
    return r


# --- degradation gracieuse quand Neo4j est injoignable (pas de creds) -----------


def test_fetch_relations_graceful_without_credentials() -> None:
    # conftest vide les creds NEO4J -> connect() False -> [].
    assert GraphRetriever(get_settings()).fetch_relations("Kuzan") == []


def test_fetch_subgraph_graceful_without_credentials() -> None:
    assert GraphRetriever(get_settings()).fetch_subgraph("Kuzan") == {"nodes": [], "edges": []}


# --- parsing des resultats ------------------------------------------------------


def test_fetch_relations_parses_records() -> None:
    rows = [
        {"source": "Kuzan", "relation": "MEMBER_OF", "target": "Marines", "target_type": "Organization"},
        {"source": "Kuzan", "relation": "RELATED_TO", "target": "Aokiji", "target_type": "Entity"},
    ]
    result = _retriever_with(rows).fetch_relations("Kuzan")
    assert result == rows


def test_fetch_relations_error_degrades_and_resets_driver() -> None:
    r = _retriever_with([], raise_exc=RuntimeError("neo4j down"))
    assert r.fetch_relations("Kuzan") == []
    assert r._driver is None  # reset pour forcer la reconnexion


def test_fetch_subgraph_parses_and_dedups() -> None:
    rows = [
        {
            "nodes": [{"name": "Kuzan", "type": "Character"}, {"name": "Marines", "type": "Organization"}],
            "rels": [_FakeRel("Kuzan", "Marines", "MEMBER_OF")],
        },
        {
            # meme noeud + meme arete -> doivent etre dedupliques
            "nodes": [{"name": "Kuzan", "type": "Character"}],
            "rels": [_FakeRel("Kuzan", "Marines", "MEMBER_OF")],
        },
    ]
    out = _retriever_with(rows).fetch_subgraph("Kuzan")
    assert len(out["nodes"]) == 2
    assert len(out["edges"]) == 1
    assert {"source": "Kuzan", "target": "Marines", "type": "MEMBER_OF"} in out["edges"]


def test_fetch_subgraph_error_degrades() -> None:
    r = _retriever_with([], raise_exc=RuntimeError("neo4j down"))
    assert r.fetch_subgraph("Kuzan") == {"nodes": [], "edges": []}
    assert r._driver is None
