from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines import fanhuaji as fanhuaji_module
from app.engines.fanhuaji import CHUNK_SIZE, FanhuajiEngine, FanhuajiResponseError


def test_fanhuaji_sync_conversion_uses_post() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.json.return_value = {"code": 0, "data": {"text": "繁體內容"}, "msg": ""}

    with patch("app.engines.fanhuaji.requests.post", return_value=response) as post:
        result = FanhuajiEngine().convert(
            converter="s2t",
            chapters=[{"path": "chapter.xhtml", "content": "简体内容"}],
        )

    assert result == [{"path": "chapter.xhtml", "content": "繁體內容"}]
    post.assert_called_once()
    assert post.call_args.kwargs["data"]["converter"] == "Traditional"
    response.raise_for_status.assert_called_once_with()


@pytest.mark.asyncio
async def test_fanhuaji_async_conversion_preserves_chapter_order() -> None:
    engine = FanhuajiEngine()
    conversion = AsyncMock(side_effect=["第一章", "第二章"])
    with patch.object(engine, "_convert_text_async", conversion):
        result = await engine.async_convert(
            converter="s2t",
            chapters=[
                {"path": "one.xhtml", "content": "第一章简体"},
                {"path": "two.xhtml", "content": "第二章简体"},
            ],
        )

    assert result == [
        {"path": "one.xhtml", "content": "第一章"},
        {"path": "two.xhtml", "content": "第二章"},
    ]


def test_fanhuaji_chunking_has_no_empty_trailing_chunk() -> None:
    chunks = list(FanhuajiEngine._chunks("x" * (CHUNK_SIZE * 2)))
    assert [len(chunk) for chunk in chunks] == [CHUNK_SIZE, CHUNK_SIZE]


def test_fanhuaji_rejects_unknown_converter() -> None:
    with pytest.raises(ValueError, match="unsupported Fanhuaji converter"):
        FanhuajiEngine().convert(converter="unknown", chapters=[])


# Offline cases ported from upstream's tests/engines/test_fanhuaji_offline.py.
API_ERROR = {"code": 1, "data": [], "msg": "Invalid converter."}


def _api_success(text: str) -> dict[str, Any]:
    return {"code": 0, "data": {"text": text}, "msg": ""}


class _FakeApi:
    """Record requests; reply with "[converter]text" unless a handler is set."""

    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []
        self.connector = MagicMock()
        self.handler: Callable[[dict[str, str]], dict[str, Any]] = lambda data: _api_success(
            f"[{data['converter']}]{data['text']}"
        )

    def respond(self, data: dict[str, str]) -> dict[str, Any]:
        self.requests.append(data)
        return self.handler(data)


class _FakeSyncResponse:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def __enter__(self) -> _FakeSyncResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self.result


class _FakeAsyncResponse(_FakeSyncResponse):
    async def __aenter__(self) -> _FakeAsyncResponse:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def json(self) -> dict[str, Any]:  # type: ignore[override]
        return self.result


class _FakeClientSession:
    def __init__(self, api: _FakeApi) -> None:
        self.api = api

    async def __aenter__(self) -> _FakeClientSession:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    def post(
        self, url: str, *, data: dict[str, str], headers: dict[str, str]
    ) -> _FakeAsyncResponse:
        return _FakeAsyncResponse(self.api.respond(data))


@pytest.fixture
def sync_api(monkeypatch: pytest.MonkeyPatch) -> _FakeApi:
    api = _FakeApi()
    monkeypatch.setattr(
        fanhuaji_module.requests,
        "post",
        lambda url, *, data, headers, timeout: _FakeSyncResponse(api.respond(data)),
    )
    return api


@pytest.fixture
def async_api(monkeypatch: pytest.MonkeyPatch) -> _FakeApi:
    api = _FakeApi()
    monkeypatch.setattr(fanhuaji_module.aiohttp, "TCPConnector", api.connector)
    monkeypatch.setattr(
        fanhuaji_module.aiohttp,
        "ClientSession",
        lambda *, connector, timeout: _FakeClientSession(api),
    )
    return api


@pytest.mark.parametrize(
    ("converter", "expected"),
    [
        ("s2t", "Traditional"),
        ("s2tw", "Traditional"),
        ("s2twp", "Taiwan"),
        ("t2s", "Simplified"),
        ("tw2s", "Simplified"),
        ("tw2sp", "China"),
    ],
)
def test_fanhuaji_converter_mapping(sync_api: _FakeApi, converter: str, expected: str) -> None:
    FanhuajiEngine().convert(converter=converter, chapters=[{"path": "a.html", "content": "简体"}])

    assert sync_api.requests[0]["converter"] == expected
    assert sync_api.requests[0]["jpTextConversionStrategy"] == "protect"


def test_fanhuaji_sync_api_error_code_raises(sync_api: _FakeApi) -> None:
    sync_api.handler = lambda data: API_ERROR

    with pytest.raises(FanhuajiResponseError, match=r"code=1.*Invalid converter"):
        FanhuajiEngine().convert(converter="s2t", chapters=[{"path": "a.html", "content": "简体"}])


async def test_fanhuaji_async_api_error_code_raises(async_api: _FakeApi) -> None:
    async_api.handler = lambda data: API_ERROR

    with pytest.raises(FanhuajiResponseError, match=r"code=1.*Invalid converter"):
        await FanhuajiEngine().async_convert(
            converter="s2t", chapters=[{"path": "a.html", "content": "简体"}]
        )


async def test_fanhuaji_async_slices_long_content(async_api: _FakeApi) -> None:
    async_api.handler = lambda data: _api_success(data["text"].upper())
    content = "a" * CHUNK_SIZE + "b" * CHUNK_SIZE + "c" * 10

    result = await FanhuajiEngine().async_convert(
        converter="s2t", chapters=[{"path": "a.html", "content": content}]
    )

    assert [len(request["text"]) for request in async_api.requests] == [CHUNK_SIZE, CHUNK_SIZE, 10]
    assert result[0]["content"] == content.upper()


@pytest.mark.parametrize(("limit_per_host", "expected"), [(3, 3), (5, 5), (6, 5), (10, 5)])
async def test_fanhuaji_async_caps_limit_per_host(
    async_api: _FakeApi, limit_per_host: int, expected: int
) -> None:
    await FanhuajiEngine().async_convert(
        converter="s2t",
        chapters=[{"path": "a.html", "content": "简体"}],
        aiohttp_tcp_limit=8,
        aiohttp_tcp_limit_per_host=limit_per_host,
    )

    async_api.connector.assert_called_once_with(limit=8, limit_per_host=expected, force_close=True)
