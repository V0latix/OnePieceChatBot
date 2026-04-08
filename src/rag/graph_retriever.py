"""Recuperation des relations depuis Neo4j pour enrichir le contexte RAG."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from config.settings import Settings
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

# Timeouts Neo4j (secondes)
_NEO4J_CONNECTION_TIMEOUT = 10
_NEO4J_QUERY_TIMEOUT = 15_000  # ms, utilise par le driver


class GraphRetriever:
    """Interroge le graphe Neo4j pour des entites donnees."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._driver = None
        self._cb = CircuitBreaker("neo4j", failure_threshold=3, recovery_timeout=120.0)

    def connect(self) -> bool:
        """Etablit la connexion si possible, sinon retourne False."""
        if self._driver is not None:
            return True
        if not (self.settings.neo4j_uri and self.settings.neo4j_user and self.settings.neo4j_password):
            return False
        try:
            self._cb.before_call()
            self._driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
                connection_timeout=_NEO4J_CONNECTION_TIMEOUT,
                max_transaction_retry_time=_NEO4J_QUERY_TIMEOUT / 1000,
            )
            self._cb.on_success()
        except CircuitBreakerOpen:
            return False
        except Exception:
            self._cb.on_failure()
            return False
        return True

    def close(self) -> None:
        """Ferme la connexion active."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def fetch_relations(self, entity_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """Retourne les relations directes autour d'une entite."""
        if not self.connect():
            return []
        assert self._driver is not None

        query = """
        MATCH (n:Entity {name: $name})-[r]-(m:Entity)
        RETURN n.name AS source,
               type(r) AS relation,
               m.name AS target,
               m.type AS target_type
        LIMIT $limit
        """

        try:
            self._cb.before_call()
            with self._driver.session() as session:
                rows = session.run(query, {"name": entity_name, "limit": limit})
                result = [dict(record) for record in rows]
            self._cb.on_success()
            return result
        except CircuitBreakerOpen:
            return []
        except (Neo4jError, Exception):
            self._cb.on_failure()
            self._driver = None  # Force reconnexion au prochain appel
            return []

    def fetch_subgraph(self, entity_name: str, depth: int = 2, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
        """Retourne un sous-graphe (nodes/edges) autour d'une entite."""
        if not self.connect():
            return {"nodes": [], "edges": []}
        assert self._driver is not None

        bounded_depth = max(1, min(depth, 3))
        query = f"""
        MATCH p=(n:Entity {{name: $name}})-[*1..{bounded_depth}]-(m:Entity)
        RETURN nodes(p) AS nodes, relationships(p) AS rels
        LIMIT $limit
        """

        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str, str], dict[str, Any]] = {}

        try:
            self._cb.before_call()
            with self._driver.session() as session:
                rows = session.run(query, {"name": entity_name, "limit": limit})
                for row in rows:
                    for node in row["nodes"]:
                        name = node.get("name")
                        if not name:
                            continue
                        nodes[name] = {
                            "id": name,
                            "label": name,
                            "type": node.get("type", "Entity"),
                        }
                    for rel in row["rels"]:
                        start = rel.start_node.get("name")
                        end = rel.end_node.get("name")
                        rel_type = rel.type
                        if not start or not end:
                            continue
                        edge_key = (start, end, rel_type)
                        edges[edge_key] = {
                            "source": start,
                            "target": end,
                            "type": rel_type,
                        }
            self._cb.on_success()
        except CircuitBreakerOpen:
            return {"nodes": [], "edges": []}
        except (Neo4jError, Exception):
            self._cb.on_failure()
            self._driver = None
            return {"nodes": [], "edges": []}

        return {
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
        }
