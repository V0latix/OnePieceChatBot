"""Configuration pytest commune.

Les tests unitaires ne doivent jamais joindre les services externes declares dans
le .env local. Ces variables vides prennent precedence sur le fichier .env.
"""

from __future__ import annotations

import pytest

from config.settings import get_settings


_EXTERNAL_SERVICE_ENV = {
    "QDRANT_URL": "",
    "QDRANT_API_KEY": "",
    "NEO4J_URI": "",
    "NEO4J_USER": "",
    "NEO4J_PASSWORD": "",
    "GROQ_API_KEY": "",
}


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force les tests a utiliser les fallbacks locaux/mocks."""
    get_settings.cache_clear()
    for key, value in _EXTERNAL_SERVICE_ENV.items():
        monkeypatch.setenv(key, value)
    yield
    get_settings.cache_clear()
