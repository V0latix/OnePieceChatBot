"""Evaluation simplifiee de la qualite retrieval/generation."""

from __future__ import annotations

from utils.logger import configure_logging, get_logger


def main() -> None:
    configure_logging("INFO")
    logger = get_logger(__name__)
    logger.info("Evaluation non implementee: brancher un set de questions gold + metrics precision/recall")


if __name__ == "__main__":
    main()
