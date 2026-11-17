"""End-to-end conversion tests, ported from upstream's tests/modules/test_epubconv.py
and tests/test_main.py to the refactored EpubConverter / AppConfig API."""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from app.modules.epubconv import EpubConverter
from config.config import AppConfig
from tests.conftest import VERTICAL_STYLES, EpubInspector

MAIN = Path(__file__).resolve().parent.parent / "main.py"

VERTICAL_CSS = "html {{ color: black; {} }}\np {{ text-indent: 2em; }}".format(
    " ".join(f"{key}: {value};" for key, value in VERTICAL_STYLES.items())
)

MakeEpub = Callable[..., Path]


def convert(
    make_epub: MakeEpub,
    *,
    converter: str = "s2twp",
    writing_format: str = "horizontal",
    **kwargs,
) -> EpubInspector:
    epub = make_epub("book.epub", **kwargs)
    config = AppConfig(
        engine="opencc",
        converter=converter,
        writing_format=writing_format,
        add_suffix=True,
    )
    output = EpubConverter(epub, config).run()
    assert output == epub.parent / f"book_{converter}.epub"
    return EpubInspector(output)


def assert_vertical(book: EpubInspector) -> None:
    assert book.page_progression_direction == "rtl"
    for page in book.pages:
        styles = book.applied_vertical_styles(page)
        assert styles == VERTICAL_STYLES, f"{page} does not apply the full vertical style"
    for css in book.css_files:
        assert css in book.manifest.values(), f"{css} is missing from the OPF manifest"


def assert_horizontal(book: EpubInspector) -> None:
    assert book.page_progression_direction is None
    for page in book.pages:
        assert book.applied_vertical_styles(page) == {}, f"{page} still applies vertical style"


class TestConvertContent:
    def test_s2twp(self, make_epub: MakeEpub) -> None:
        book = convert(make_epub, converter="s2twp")

        chapter1 = book.read("OEBPS/Text/chapter1.xhtml")
        chapter2 = book.read("OEBPS/Text/chapter2.xhtml")
        assert "這是一本簡體中文的小說，內容講述了一個少年的冒險故事。" in chapter1
        assert "軟體和記憶體都是計算機的重要組成部分。" in chapter2
        assert "第一章 簡體中文" in book.read("OEBPS/toc.ncx")
        assert book.language == "zh-Hant-TW"

    def test_t2s(self, make_epub: MakeEpub) -> None:
        book = convert(make_epub, converter="t2s")

        assert book.language == "zh-Hans-CN"
        assert "这是一本简体中文的小说" in book.read("OEBPS/Text/chapter1.xhtml")

    def test_original_file_untouched(self, make_epub: MakeEpub) -> None:
        epub = make_epub("book.epub")
        original = epub.read_bytes()

        EpubConverter(epub, AppConfig(engine="opencc", converter="s2twp")).run()

        assert epub.read_bytes() == original
        assert not Path(f"{epub}_files").exists()


class TestConvertFormat:
    def test_horizontal(self, make_epub: MakeEpub) -> None:
        book = convert(make_epub, writing_format="horizontal")
        assert_horizontal(book)

    def test_vertical_to_horizontal(self, make_epub: MakeEpub) -> None:
        book = convert(
            make_epub,
            writing_format="horizontal",
            css=VERTICAL_CSS,
            page_progression_direction="rtl",
        )

        assert_horizontal(book)
        assert "color: black" in book.read("OEBPS/Styles/style.css")

    def test_vertical_css_without_html(self, make_epub: MakeEpub) -> None:
        book = convert(make_epub, writing_format="vertical")

        assert_vertical(book)
        assert "OEBPS/Styles/epubconv_custom.css" in book.manifest.values()

    def test_vertical_css_with_html(self, make_epub: MakeEpub) -> None:
        book = convert(
            make_epub,
            writing_format="vertical",
            css="html { color: black; }\np { text-indent: 2em; }",
        )

        assert_vertical(book)
        assert "OEBPS/Styles/epubconv_custom.css" not in book.names

    def test_vertical_no_css(self, make_epub: MakeEpub) -> None:
        book = convert(make_epub, writing_format="vertical", css=None)

        assert_vertical(book)
        assert book.css_files == ["OEBPS/Styles/epubconv_custom.css"]

    @pytest.mark.xfail(
        strict=True,
        reason="known issue: with an existing html rule, pages that do not link that CSS "
        "do not get the vertical style",
    )
    def test_vertical_css_with_html_partially_linked(self, make_epub: MakeEpub) -> None:
        book = convert(
            make_epub,
            writing_format="vertical",
            css="html { color: black; }",
            linked_chapters=("chapter1",),
        )

        assert_vertical(book)

    def test_vertical_opf_at_root(self, make_epub: MakeEpub) -> None:
        # Upstream marks this xfail; the refactored writer places the CSS relative to the OPF.
        book = convert(make_epub, writing_format="vertical", opf_dir="", css=None)

        assert_vertical(book)
        assert "Styles/epubconv_custom.css" in book.manifest.values()


def run_main(*epubs: Path, **settings: str) -> subprocess.CompletedProcess[str]:
    """Run main.py; environment variables override config.ini."""
    env = (
        os.environ
        | {
            "ENGINE": "opencc",
            "ENABLE_PAUSE": "false",
            "ADD_SUFFIX": "true",
            "PYTHONIOENCODING": "utf-8",
        }
        | {key.upper(): value for key, value in settings.items()}
    )
    return subprocess.run(
        [sys.executable, str(MAIN), *map(str, epubs)],
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


class TestMain:
    @pytest.mark.parametrize(
        ("writing_format", "direction"),
        [("horizontal", None), ("vertical", "rtl")],
    )
    def test_convert(self, make_epub: MakeEpub, writing_format: str, direction: str | None) -> None:
        epub = make_epub("简体书名.epub")

        process = run_main(epub, converter="s2twp", writing_format=writing_format)

        assert process.returncode == 0, process.stderr
        book = EpubInspector(epub.parent / "簡體書名_s2twp.epub")
        assert "這是一本簡體中文的小說" in book.read("OEBPS/Text/chapter1.xhtml")
        assert book.language == "zh-Hant-TW"
        assert book.page_progression_direction == direction
        assert not Path(f"{epub}_files").exists()

    def test_multiple_files(self, make_epub: MakeEpub) -> None:
        first = make_epub("第一本.epub")
        second = make_epub("第二本.epub")

        process = run_main(first, second, converter="s2t", writing_format="horizontal")

        assert process.returncode == 0, process.stderr
        assert (first.parent / "第一本_s2t.epub").exists()
        assert (second.parent / "第二本_s2t.epub").exists()

    def test_relative_main_path(self, make_epub: MakeEpub) -> None:
        epub = make_epub("book.epub")
        env = os.environ | {"ENGINE": "opencc", "ENABLE_PAUSE": "false"}

        process = subprocess.run(
            [sys.executable, "main.py", str(epub)],
            cwd=MAIN.parent,
            env=env,
            capture_output=True,
            timeout=120,
            check=False,
        )

        assert process.returncode == 0, process.stderr
