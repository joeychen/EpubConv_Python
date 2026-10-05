from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.fanhuaji import CHUNK_SIZE, FanhuajiEngine


def test_fanhuaji_sync_conversion_uses_post() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.json.return_value = {"data": {"text": "繁體內容"}}

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
