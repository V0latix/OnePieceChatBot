"""Personalized PageRank sur le graphe d'entites, pour injecter la proximite
graphe dans le classement (au lieu du seul prompt).

Seede depuis les entites extraites de la question, PPR classe les autres entites
par proximite graphe. On mappe ensuite entite -> chunk via `entity_name` dans le
retriever. GDS n'etant pas dispo sur Aura Free, on tourne NetworkX en CPU sur les
triplets exportes (7.7k noeuds, ~ms par requete).
"""

from __future__ import annotations

import json
from pathlib import Path

from utils.logger import get_logger

_logger = get_logger(__name__)


class GraphRanker:
    """Charge le graphe d'entites (paresseux) et calcule un PPR seede."""

    def __init__(self, triplets_path: Path) -> None:
        self.triplets_path = triplets_path
        self._graph = None  # networkx.Graph, construit au 1er appel
        self._loaded = False

    def _get_graph(self):
        if self._loaded:
            return self._graph
        self._loaded = True
        try:
            import networkx as nx

            if not self.triplets_path.exists():
                _logger.warning("Triplets absents (%s): PPR desactive", self.triplets_path)
                return None
            graph = nx.Graph()
            with self.triplets_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    subj, obj = row.get("subject"), row.get("object")
                    if subj and obj:
                        graph.add_edge(subj, obj)
            self._graph = graph
        except Exception as exc:  # noqa: BLE001 - degradation gracieuse
            _logger.warning("Graphe PPR indisponible (%s): fallback sans signal graphe", exc)
            self._graph = None
        return self._graph

    def personalized_scores(self, seeds: list[str]) -> dict[str, float]:
        """Retourne {entite: score PPR} seede sur `seeds`. {} si rien d'exploitable."""
        graph = self._get_graph()
        if graph is None:
            return {}
        present = [s for s in seeds if s in graph]
        if not present:
            return {}
        try:
            import networkx as nx

            weight = 1.0 / len(present)
            personalization = {node: 0.0 for node in graph}
            for seed in present:
                personalization[seed] = weight
            return nx.pagerank(graph, personalization=personalization)
        except Exception as exc:  # noqa: BLE001 - degradation gracieuse
            _logger.warning("Echec PPR (%s): fallback sans signal graphe", exc)
            return {}
