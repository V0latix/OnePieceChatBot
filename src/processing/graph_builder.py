"""Construction et maintenance du knowledge graph One Piece dans Neo4j."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.config.settings import Settings
from src.scraper.exporter import ScrapedPageDocument
from src.utils.logger import get_logger


_RELATION_CLEAN_RE = re.compile(r"[^A-Z0-9_]")
_SPLIT_VALUES_RE = re.compile(r",|/|;| and ", re.IGNORECASE)


@dataclass(slots=True)
class GraphTriplet:
    """Triplet relationnel pre-normalise pour Neo4j."""

    subject: str
    relation: str
    object: str
    subject_type: str = "Entity"
    object_type: str = "Entity"
    properties: dict[str, Any] = field(default_factory=dict)


class GraphBuilder:
    """Construit les noeuds et relations du graphe One Piece."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)
        self._driver = None

    def _normalize_relation(self, relation: str) -> str:
        relation = _RELATION_CLEAN_RE.sub("_", relation.upper()).strip("_")
        return relation or "RELATED_TO"

    def _normalize_label(self, value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", value.title())
        return cleaned or "Entity"

    def _split_values(self, raw: str) -> list[str]:
        values = [chunk.strip() for chunk in _SPLIT_VALUES_RE.split(raw) if chunk.strip()]
        return list(dict.fromkeys(values))

    def connect(self) -> None:
        """Initialise la connexion Neo4j si les credentials existent."""
        if self._driver is not None:
            return
        if not (self.settings.neo4j_uri and self.settings.neo4j_user and self.settings.neo4j_password):
            raise RuntimeError("Credentials Neo4j manquants dans l'environnement")

        self._driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )

    def close(self) -> None:
        """Ferme proprement le driver Neo4j."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _with_retry_write(self, query: str, parameters: dict[str, Any]) -> None:
        """Execute une ecriture avec reconnexion en cas de timeout/inactivite Aura."""
        self.connect()
        assert self._driver is not None

        for attempt in range(2):
            try:
                with self._driver.session() as session:
                    session.run(query, parameters)
                return
            except ServiceUnavailable:
                self.logger.warning("Neo4j indisponible, tentative de reconnexion %s/2", attempt + 1)
                self.close()
                self.connect()
            except Neo4jError as exc:
                raise RuntimeError(f"Erreur Neo4j: {exc}") from exc

        raise RuntimeError("Echec ecriture Neo4j apres reconnexion")

    def extract_triplets(self, document: ScrapedPageDocument) -> list[GraphTriplet]:
        """Extrait des relations a partir de l'infobox et des liens internes."""
        subject = document.title
        subject_type = self._normalize_label(document.type)
        triplets: list[GraphTriplet] = []

        infobox_relation_map: dict[str, tuple[str, str]] = {
            "devil_fruit": ("ATE", "DevilFruit"),
            "affiliation": ("MEMBER_OF_ORG", "Organization"),
            "occupation": ("HAS_ROLE", "Organization"),
            "origin": ("BORN_IN", "Location"),
            "race": ("BELONGS_TO_RACE", "Race"),
            "weapon": ("WIELDS", "Weapon"),
            "fighting_style": ("USES", "Technique"),
            "debut_arc": ("APPEARED_IN", "Arc"),
            "captain": ("MEMBER_OF", "Crew"),
        }

        for key, value in document.infobox.items():
            mapped = infobox_relation_map.get(key)
            if not mapped:
                continue
            relation, object_type = mapped
            for object_name in self._split_values(value):
                triplets.append(
                    GraphTriplet(
                        subject=subject,
                        relation=self._normalize_relation(relation),
                        object=object_name,
                        subject_type=subject_type,
                        object_type=self._normalize_label(object_type),
                    )
                )

        for related in document.related_entities[:100]:
            if related == subject:
                continue
            triplets.append(
                GraphTriplet(
                    subject=subject,
                    relation="RELATED_TO",
                    object=related,
                    subject_type=subject_type,
                    object_type="Entity",
                )
            )

        deduped: dict[tuple[str, str, str], GraphTriplet] = {}
        for triplet in triplets:
            key = (triplet.subject, triplet.relation, triplet.object)
            deduped[key] = triplet
        return list(deduped.values())

    def upsert_triplet(self, triplet: GraphTriplet) -> None:
        """Inserte ou met a jour un triplet dans Neo4j."""
        relation = self._normalize_relation(triplet.relation)
        subject_label = self._normalize_label(triplet.subject_type)
        object_label = self._normalize_label(triplet.object_type)

        query = f"""
        MERGE (s:Entity {{name: $subject}})
        SET s.type = $subject_type
        SET s:{subject_label}
        MERGE (o:Entity {{name: $object}})
        SET o.type = $object_type
        SET o:{object_label}
        MERGE (s)-[r:{relation}]->(o)
        SET r += $properties
        """
        self._with_retry_write(
            query,
            {
                "subject": triplet.subject,
                "subject_type": subject_label,
                "object": triplet.object,
                "object_type": object_label,
                "properties": triplet.properties,
            },
        )

    def build_from_documents(self, documents: list[ScrapedPageDocument]) -> tuple[int, int]:
        """Construit le graphe depuis une liste de documents."""
        inserted_relations = 0
        extracted_triplets = 0

        for document in documents:
            triplets = self.extract_triplets(document)
            extracted_triplets += len(triplets)
            for triplet in triplets:
                self.upsert_triplet(triplet)
                inserted_relations += 1

        return extracted_triplets, inserted_relations

    def export_triplets_jsonl(self, triplets: list[GraphTriplet], output_path: Path) -> None:
        """Exporte les triplets en JSONL pour audit et debug."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for triplet in triplets:
                payload = {
                    "subject": triplet.subject,
                    "relation": triplet.relation,
                    "object": triplet.object,
                    "subject_type": triplet.subject_type,
                    "object_type": triplet.object_type,
                    "properties": triplet.properties,
                }
                handle.write(json.dumps(payload, ensure_ascii=False))
                handle.write("\n")

    def get_counts(self) -> dict[str, int]:
        """Retourne les cardinalites principales du graphe."""
        self.connect()
        assert self._driver is not None
        with self._driver.session() as session:
            nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            edges = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        return {"nodes": int(nodes), "edges": int(edges)}
