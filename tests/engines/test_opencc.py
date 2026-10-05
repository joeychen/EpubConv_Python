import pytest

from app.engines.opencc import OpenCCEngine


@pytest.mark.parametrize(
    ("converter", "source", "expected"),
    [
        (
            "s2t",
            "使用 Python 撰写，epub 档案繁简横直互转",
            "使用 Python 撰寫，epub 檔案繁簡橫直互轉",
        ),
        (
            "t2s",
            "使用 Python 撰寫，epub 檔案繁簡橫直互轉",
            "使用 Python 撰写，epub 档案繁简横直互转",
        ),
        ("s2twp", "内存", "記憶體"),
        ("tw2sp", "記憶體", "内存"),
    ],
)
def test_opencc_conversion(converter: str, source: str, expected: str) -> None:
    result = OpenCCEngine().convert(
        converter,
        [{"path": "chapter.xhtml", "content": source}],
    )
    assert result == [{"path": "chapter.xhtml", "content": expected}]


def test_opencc_rejects_unknown_converter() -> None:
    with pytest.raises(ValueError, match="unsupported OpenCC converter"):
        OpenCCEngine().convert("unknown", [])
