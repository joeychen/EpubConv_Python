from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import aiohttp
import requests
from loguru import logger

from app import __version__
from app.enums.converter import FANHUAJI_CONVERTERS
from app.models import Chapter, Chapters

API_URL = "https://api.zhconvert.org/convert"
CHUNK_SIZE = 50_000
USER_AGENT = f"EpubConv_Python/{__version__}"


class FanhuajiEngine:
    """Convert chapter content with the Fanhuaji web API."""

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    @staticmethod
    def _format_converter(converter: str) -> str:
        try:
            return FANHUAJI_CONVERTERS[converter]
        except KeyError as error:
            raise ValueError(f"unsupported Fanhuaji converter: {converter!r}") from error

    @staticmethod
    def _chunks(content: str) -> Iterator[str]:
        for offset in range(0, len(content), CHUNK_SIZE):
            yield content[offset : offset + CHUNK_SIZE]

    @staticmethod
    def _payload(text: str, converter: str) -> dict[str, str]:
        return {
            "text": text,
            "converter": converter,
            "jpTextConversionStrategy": "protect",
        }

    @staticmethod
    def _converted_text(response_data: dict[str, Any]) -> str:
        try:
            return str(response_data["data"]["text"])
        except (KeyError, TypeError) as error:
            raise FanhuajiResponseError("Fanhuaji returned an invalid response") from error

    def _convert_text(self, text: str, converter: str) -> str:
        if not text:
            return ""

        converted_chunks: list[str] = []
        for chunk in self._chunks(text):
            with requests.post(
                API_URL,
                data=self._payload(chunk, converter),
                headers={"User-Agent": USER_AGENT},
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                converted_chunks.append(self._converted_text(response.json()))
        return "".join(converted_chunks)

    async def _convert_text_async(
        self,
        session: aiohttp.ClientSession,
        text: str,
        converter: str,
    ) -> str:
        if not text:
            return ""

        converted_chunks: list[str] = []
        for chunk in self._chunks(text):
            async with session.post(
                API_URL,
                data=self._payload(chunk, converter),
                headers={"User-Agent": USER_AGENT},
            ) as response:
                response.raise_for_status()
                converted_chunks.append(self._converted_text(await response.json()))
        return "".join(converted_chunks)

    def convert(self, *, converter: str, chapters: Chapters) -> Chapters:
        api_converter = self._format_converter(converter)
        return [
            Chapter(
                path=chapter["path"],
                content=self._convert_text(chapter["content"], api_converter),
            )
            for chapter in chapters
        ]

    async def async_convert(
        self,
        *,
        converter: str,
        chapters: Chapters,
        aiohttp_tcp_limit: int = 10,
        aiohttp_tcp_limit_per_host: int = 5,
    ) -> Chapters:
        api_converter = self._format_converter(converter)
        limit_per_host = min(aiohttp_tcp_limit_per_host, 5)
        if limit_per_host != aiohttp_tcp_limit_per_host:
            logger.warning("limit_per_host 最大值為 5；已自動調整")

        connector = aiohttp.TCPConnector(
            limit=aiohttp_tcp_limit,
            limit_per_host=limit_per_host,
            force_close=True,
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            converted = await asyncio.gather(
                *(
                    self._convert_text_async(session, chapter["content"], api_converter)
                    for chapter in chapters
                )
            )

        return [
            Chapter(path=chapter["path"], content=content)
            for chapter, content in zip(chapters, converted, strict=True)
        ]


class FanhuajiResponseError(RuntimeError):
    """Raised when the Fanhuaji response does not contain converted text."""
