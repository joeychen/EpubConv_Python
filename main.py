from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from app import __version__
from app.modules.epubconv import EpubConverter
from config.config import AppConfig, application_directory

BANNER = rf"""
  ______             _      _____
 |  ____|           | |    / ____|
 | |__   _ __  _   _| |__ | |     ___  _ ____   __
 |  __| | '_ \| | | | '_ \| |    / _ \| '_ \ \ / /
 | |____| |_) | |_| | |_) | |___| (_) | | | \ V /
 |______| .__/ \__,_|_.__/ \_____\___/|_| |_|\_/
        | |
        |_|
 v{__version__}
"""


def configure_logging(config: AppConfig) -> None:
    logs_directory = application_directory() / "storages" / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level=config.stdout_level.upper())
    logger.add(
        logs_directory / "app_{time:YYYY-MM-DD}.log",
        level=config.log_level.upper(),
        format="{time} {level} {message}",
        rotation="00:00",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epubconv",
        description="Convert EPUB files between Simplified and Traditional Chinese.",
    )
    parser.add_argument("epub", nargs="*", type=Path, help="EPUB file(s) to convert")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None, config: AppConfig | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if not arguments.epub:
        parser.error("provide at least one EPUB file")

    config = config or AppConfig.load()
    configure_logging(config)
    logger.info(BANNER)
    exit_code = 0
    for epub_path in arguments.epub:
        try:
            EpubConverter(epub_path, config).run()
        except Exception:
            exit_code = 1
            logger.exception("轉換失敗: {}", epub_path)

    if config.enable_pause and sys.platform == "win32":
        input("Press Enter to continue...")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
