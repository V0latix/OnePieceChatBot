"""Assemblage du prompt system + contexte retrieval."""

from __future__ import annotations

import re

from rag.retriever import RetrievalResult


_CITATION_RE = re.compile(r"\[(\d+)\]")


def grounded_ratio(answer: str, n_sources: int) -> float:
    """Fraction des citations [i] de la reponse qui pointent une source fournie.

    Retourne 1.0 si la reponse ne cite rien (pas de penalite). Sinon, part des
    citations dont l'index est dans 1..n_sources : detecte les [i] hallucines.
    """
    cites = _CITATION_RE.findall(answer)
    if not cites:
        return 1.0
    valid = sum(1 for c in cites if 1 <= int(c) <= n_sources)
    return valid / len(cites)


SYSTEM_PROMPT_TEMPLATE = """Tu es un expert encyclopedique de l'univers One Piece, le manga cree par Eiichiro Oda.

REGLES STRICTES :
1. Reponds UNIQUEMENT a partir du contexte fourni ci-dessous. Ne fabrique JAMAIS d'information.
2. Si le contexte ne contient pas la reponse, dis-le clairement : "Je n'ai pas trouve cette information dans ma base de donnees."
3. Cite tes sources : mentionne l'arc, le chapitre ou la section wiki quand c'est possible.
4. Distingue toujours le CANON du FILLER et des THEORIES.
5. Utilise les noms complets a la premiere mention.
6. Respecte le filtre anti-spoiler s'il est fourni.
7. Reponds en francais sauf si la question est en anglais.
8. Pour les comparaisons/classements, structure clairement.
9. L'historique de conversation ne sert QU'A resoudre les references (pronoms, "et lui ?"). Reponds UNIQUEMENT a la derniere question posee ; ne repete jamais les reponses precedentes et n'enchaine pas sur d'anciennes questions.

CONTEXTE :
{context}

DONNEES DU GRAPHE (relations entre entites) :
{graph_context}
"""


class PromptBuilder:
    """Construit le contexte textuel et les messages chat."""

    def build_context(self, results: list[RetrievalResult], top_k: int = 5) -> str:
        """Assemble les meilleurs chunks avec citations."""
        lines: list[str] = []
        for index, result in enumerate(results[:top_k], start=1):
            lines.append(
                f"[{index}] Entite: {result.entity_name} | Type: {result.entity_type} | "
                f"Section: {result.section} | Source: {result.source_url or 'supabase'}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    def build_graph_context(self, relations: list[dict[str, str]]) -> str:
        """Assemble un resume relationnel pour le LLM."""
        if not relations:
            return "Aucune relation de graphe disponible."
        lines = [
            f"{row.get('source', '?')} -[{row.get('relation', '?')}]-> {row.get('target', '?')}"
            for row in relations
        ]
        return "\n".join(lines)

    def build_messages(
        self,
        question: str,
        context: str,
        graph_context: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Construit les messages compatibles API chat.

        L'historique (max 6 derniers messages = 3 echanges) est insere entre
        le system prompt et la question courante pour que le LLM ait du contexte
        conversationnel sans depasser la fenetre de contexte.
        """
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_TEMPLATE.format(
                    context=context,
                    graph_context=graph_context,
                ),
            }
        ]
        # Garde les 6 derniers messages (3 echanges user/assistant)
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": question})
        return messages
