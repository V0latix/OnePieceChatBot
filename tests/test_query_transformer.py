"""Tests du QueryTransformer (HyDE)."""

from __future__ import annotations

from rag.query_transformer import QueryTransformer


class _StubGen:
    def __init__(self, reply: str | None = None, boom: bool = False) -> None:
        self.reply = reply
        self.boom = boom
        self.messages = None

    def _generate_with_groq(self, messages, model=None):  # noqa: ANN001, ANN202
        if self.boom:
            raise RuntimeError("groq down")
        self.messages = messages
        self.model = model
        return self.reply


def test_hyde_returns_generated_passage() -> None:
    qt = QueryTransformer(_StubGen(reply="  Luffy is the captain of the Straw Hat Pirates.  "))
    out = qt.hyde("Qui est le capitaine des Mugiwara ?")
    assert out == "Luffy is the captain of the Straw Hat Pirates."


def test_hyde_degrades_to_empty_on_failure() -> None:
    assert QueryTransformer(_StubGen(boom=True)).hyde("Qui est Zoro ?") == ""


def test_hyde_empty_when_llm_returns_none() -> None:
    assert QueryTransformer(_StubGen(reply=None)).hyde("Qui est Zoro ?") == ""


def test_hyde_routes_fast_model() -> None:
    stub = _StubGen(reply="passage")
    QueryTransformer(stub, model="llama-3.1-8b-instant").hyde("Q")
    assert stub.model == "llama-3.1-8b-instant"
