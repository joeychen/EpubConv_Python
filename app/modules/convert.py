import asyncio

from app.engines.fanhuaji import FanhuajiEngine
from app.engines.opencc import OpenCCEngine
from app.enums.engine import Engine
from app.models import Chapters
from config.config import AppConfig


def convert_chapters(chapters: Chapters, config: AppConfig) -> Chapters:
    """Convert chapters with the engine selected in the application config."""
    try:
        engine = Engine(config.engine)
    except ValueError as error:
        raise ValueError(f"unsupported conversion engine: {config.engine!r}") from error

    match engine:
        case Engine.OPENCC:
            return OpenCCEngine().convert(config.converter, chapters)
        case Engine.FANHUAJI:
            return FanhuajiEngine().convert(
                converter=config.converter,
                chapters=chapters,
            )
        case Engine.FANHUAJI_ASYNC:
            return asyncio.run(
                FanhuajiEngine().async_convert(
                    converter=config.converter,
                    chapters=chapters,
                    aiohttp_tcp_limit=config.async_limit,
                    aiohttp_tcp_limit_per_host=config.async_limit_per_host,
                )
            )

    raise AssertionError(f"unhandled engine: {engine}")
