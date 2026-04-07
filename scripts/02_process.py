"""Validation/normalisation des JSON raw vers data/processed."""

from __future__ import annotations

from pathlib import Path

from src.config.settings import get_settings
from src.scraper.exporter import JsonExporter
from src.utils.logger import configure_logging, get_logger


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    exporter = JsonExporter(settings.raw_data_dir)
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for file_path in sorted(Path(settings.raw_data_dir).glob("*.json")):
        document = exporter.load(file_path)
        output_path = settings.processed_data_dir / file_path.name
        output_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        count += 1

    logger.info("Documents valides copies vers data/processed: %s", count)


if __name__ == "__main__":
    main()
