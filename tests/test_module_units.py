"""Unit tests ported from upstream's tests/modules/*.py to the refactored module API."""

import codecs
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import cssutils
import pytest
from bs4 import BeautifulSoup
from lxml import etree

from app.modules import convert as convert_module
from app.modules.convert import convert_chapters
from app.modules.opf import update_language
from app.modules.renamer import publish_converted_file
from app.modules.utils import dict_to_css_text, file_encoding
from app.modules.writing_format import (
    VERTICAL_STYLES,
    OpfFormat,
    StyleFile,
    WritingFormatConverter,
)
from app.modules.zip import EpubArchive
from config.config import AppConfig

CHAPTERS = [{"path": "chapter1.xhtml", "content": "简体"}]
RESULT = [{"path": "chapter1.xhtml", "content": "簡體"}]


# --- convert.py (upstream tests/modules/test_convert.py) ---


@pytest.fixture
def engines(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    opencc = MagicMock()
    opencc.convert.return_value = RESULT
    fanhuaji = MagicMock()
    fanhuaji.convert.return_value = RESULT
    fanhuaji.async_convert = AsyncMock(return_value=RESULT)
    monkeypatch.setattr(convert_module, "OpenCCEngine", lambda: opencc)
    monkeypatch.setattr(convert_module, "FanhuajiEngine", lambda: fanhuaji)
    return opencc, fanhuaji


class TestConvertChapters:
    def test_opencc(self, engines: tuple[MagicMock, MagicMock]) -> None:
        opencc, fanhuaji = engines

        result = convert_chapters(CHAPTERS, AppConfig(engine="opencc", converter="s2twp"))

        assert result == RESULT
        opencc.convert.assert_called_once_with("s2twp", CHAPTERS)
        fanhuaji.convert.assert_not_called()

    def test_fanhuaji(self, engines: tuple[MagicMock, MagicMock]) -> None:
        opencc, fanhuaji = engines

        result = convert_chapters(CHAPTERS, AppConfig(engine="fanhuaji", converter="s2twp"))

        assert result == RESULT
        fanhuaji.convert.assert_called_once_with(converter="s2twp", chapters=CHAPTERS)
        opencc.convert.assert_not_called()

    def test_fanhuaji_async(self, engines: tuple[MagicMock, MagicMock]) -> None:
        _, fanhuaji = engines
        config = AppConfig(
            engine="fanhuaji_async",
            converter="s2twp",
            async_limit=3,
            async_limit_per_host=2,
        )

        assert convert_chapters(CHAPTERS, config) == RESULT
        fanhuaji.async_convert.assert_awaited_once_with(
            converter="s2twp",
            chapters=CHAPTERS,
            aiohttp_tcp_limit=3,
            aiohttp_tcp_limit_per_host=2,
        )

    def test_unsupported_engine(self, engines: tuple[MagicMock, MagicMock]) -> None:
        opencc, fanhuaji = engines

        with pytest.raises(ValueError, match="google"):
            convert_chapters(CHAPTERS, AppConfig(engine="google"))

        opencc.convert.assert_not_called()
        fanhuaji.convert.assert_not_called()


# --- zip.py (upstream tests/modules/test_zip.py) ---


class TestOutputPath:
    @pytest.mark.parametrize(
        ("converter", "expected"),
        [
            ("s2t", "簡體書名.epub"),
            ("s2twp", "簡體書名.epub"),
            ("t2s", "简体书名.epub"),
            ("tw2sp", "简体书名.epub"),
        ],
    )
    def test_converts_filename(self, tmp_path: Path, converter: str, expected: str) -> None:
        source = tmp_path / ("简体书名.epub" if converter.startswith("s") else "簡體書名.epub")

        output = EpubArchive.output_path(source, AppConfig(converter=converter, add_suffix=False))

        assert output == tmp_path / expected

    def test_unknown_converter_falls_back_to_s2t(self, tmp_path: Path) -> None:
        config = AppConfig(converter="unknown", add_suffix=False)

        output = EpubArchive.output_path(tmp_path / "简体书名.epub", config)

        assert output == tmp_path / "簡體書名.epub"

    def test_add_suffix(self, tmp_path: Path) -> None:
        config = AppConfig(converter="s2twp", add_suffix=True)

        output = EpubArchive.output_path(tmp_path / "简体书名.epub", config)

        assert output == tmp_path / "簡體書名_s2twp.epub"


# --- opf.py (upstream tests/modules/test_opf.py) ---

OPF_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试书籍</dc:title>
    <dc:language>zh-CN</dc:language>
  </metadata>
</package>
"""


@pytest.mark.parametrize(
    ("converter", "expected"),
    [
        ("s2t", "zh-Hant-TW"),
        ("s2tw", "zh-Hant-TW"),
        ("s2twp", "zh-Hant-TW"),
        ("t2s", "zh-Hans-CN"),
        ("tw2s", "zh-Hans-CN"),
        ("tw2sp", "zh-Hans-CN"),
    ],
)
def test_update_language(tmp_path: Path, converter: str, expected: str) -> None:
    opf_path = tmp_path / "content.opf"
    opf_path.write_text(OPF_CONTENT, encoding="utf-8")

    update_language(opf_path, converter)

    tree = etree.parse(opf_path)
    assert tree.xpath("//*[local-name()='language']/text()") == [expected]
    assert tree.xpath("//*[local-name()='title']/text()") == ["测试书籍"]


# --- renamer.py (upstream tests/modules/test_renamer.py) ---


class TestPublishConvertedFile:
    def test_replaces_original(self, tmp_path: Path) -> None:
        original = tmp_path / "chapter.xhtml"
        original.write_text("原始內容", encoding="utf-8")
        (tmp_path / "chapter.xhtml.new").write_text("轉換後內容", encoding="utf-8")

        publish_converted_file(original)

        assert original.read_text(encoding="utf-8") == "轉換後內容"
        assert not (tmp_path / "chapter.xhtml.new").exists()

    def test_converted_file_missing(self, tmp_path: Path) -> None:
        original = tmp_path / "chapter.xhtml"
        original.write_text("原始內容", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            publish_converted_file(original)


# --- utils.py (upstream tests/modules/test_utils.py) ---

TEXT = (
    '<?xml version="1.0"?><html><body>'
    "<p>这是一本简体中文的小说，内容讲述了一个少年的冒险故事。</p></body></html>"
)


class TestFileEncoding:
    @pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gb18030"])
    def test_detect(self, tmp_path: Path, encoding: str) -> None:
        file = tmp_path / "chapter.xhtml"
        file.write_bytes(TEXT.encode(encoding))

        detected = file_encoding(file)

        assert codecs.lookup(detected).name == codecs.lookup(encoding).name
        assert file.read_bytes().decode(detected) == TEXT

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            file_encoding(tmp_path / "not_exist.xhtml")


class TestDictToCssText:
    def test_convert(self) -> None:
        css = dict_to_css_text({"writing-mode": "vertical-rl", "margin": 0})
        assert css == "writing-mode: vertical-rl;\nmargin: 0;"

    def test_empty(self) -> None:
        assert dict_to_css_text({}) == ""


# --- writing_format.py (upstream tests/modules/test_writing_format.py) ---

SPINE_OPF = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <spine toc="ncx"{attr}>
    <itemref idref="chapter1"/>
  </spine>
</package>
"""


def _write_opf(tmp_path: Path, direction: str | None = None) -> Path:
    opf_path = tmp_path / "content.opf"
    attr = f' page-progression-direction="{direction}"' if direction else ""
    opf_path.write_text(SPINE_OPF.format(attr=attr), encoding="utf-8")
    return opf_path


def _spine_direction(opf_path: Path) -> str | None:
    soup = BeautifulSoup(opf_path.read_text(encoding="utf-8"), "xml")
    return soup.select_one("spine").get("page-progression-direction")


def _html_rule(css_path: Path) -> dict[str, str] | None:
    sheet = cssutils.CSSParser().parseFile(str(css_path))
    for rule in sheet.cssRules.rulesOfType(cssutils.css.CSSRule.STYLE_RULE):
        if rule.selectorText == "html":
            return {key: rule.style.getPropertyValue(key) for key in rule.style.keys()}  # noqa: SIM118
    return None


class TestOpfFormat:
    @pytest.mark.parametrize("direction", [None, "rtl"])
    def test_add_vertical_attribute(self, tmp_path: Path, direction: str | None) -> None:
        opf_path = _write_opf(tmp_path, direction)
        OpfFormat(opf_path).add_vertical_attribute()
        assert _spine_direction(opf_path) == "rtl"

    @pytest.mark.parametrize("direction", [None, "rtl", "ltr"])
    def test_remove_vertical_attribute(self, tmp_path: Path, direction: str | None) -> None:
        opf_path = _write_opf(tmp_path, direction)
        OpfFormat(opf_path).remove_vertical_attribute()
        assert _spine_direction(opf_path) is None

    @pytest.mark.parametrize(
        ("direction", "expected"),
        [("rtl", "vertical"), ("ltr", "vertical"), (None, "horizontal")],
    )
    def test_writing_format(self, tmp_path: Path, direction: str | None, expected: str) -> None:
        assert OpfFormat(_write_opf(tmp_path, direction)).writing_format == expected


class TestStyleFile:
    def test_selector_exists(self, tmp_path: Path) -> None:
        no_html = tmp_path / "a.css"
        no_html.write_text("p { color: red; }", encoding="utf-8")
        with_html = tmp_path / "b.css"
        with_html.write_text("html { color: black; }", encoding="utf-8")

        assert StyleFile().selector_exists("html", [no_html, with_html])
        assert not StyleFile().selector_exists("html", [no_html])
        assert not StyleFile().selector_exists("html", [])

    def test_create_vertical_style(self, tmp_path: Path) -> None:
        opf_path = tmp_path / "OEBPS" / "content.opf"

        css_path = StyleFile.create_vertical_style(opf_path, VERTICAL_STYLES)

        assert css_path == tmp_path / "OEBPS" / "Styles" / "epubconv_custom.css"
        assert _html_rule(css_path) == VERTICAL_STYLES

    def test_append_vertical_styles(self, tmp_path: Path) -> None:
        with_html = tmp_path / "with_html.css"
        with_html.write_text("html { color: black; }\np { text-indent: 2em; }", encoding="utf-8")
        no_html = tmp_path / "no_html.css"
        no_html.write_text("p { text-indent: 2em; }", encoding="utf-8")

        StyleFile().append_vertical_styles([with_html, no_html], VERTICAL_STYLES)

        assert _html_rule(with_html) == {"color": "black", **VERTICAL_STYLES}
        assert no_html.read_text(encoding="utf-8") == "p { text-indent: 2em; }"

    def test_delete_vertical_styles(self, tmp_path: Path) -> None:
        css_path = tmp_path / "style.css"
        styles = " ".join(f"{key}: {value};" for key, value in VERTICAL_STYLES.items())
        css_path.write_text(f"html {{ color: black; {styles} }}", encoding="utf-8")

        StyleFile().delete_vertical_styles([css_path], VERTICAL_STYLES)

        assert _html_rule(css_path) == {"color": "black"}

    def test_delete_vertical_styles_without_html(self, tmp_path: Path) -> None:
        css_path = tmp_path / "style.css"
        css_path.write_text("p { text-indent: 2em; }", encoding="utf-8")

        StyleFile().delete_vertical_styles([css_path], VERTICAL_STYLES)

        assert css_path.read_text(encoding="utf-8") == "p { text-indent: 2em; }"


def test_writing_format_rejects_unknown_format(tmp_path: Path) -> None:
    converter = WritingFormatConverter(AppConfig(writing_format="diagonal"))

    with pytest.raises(ValueError, match="diagonal"):
        converter.format(opf_path=tmp_path / "content.opf", css_files=[], content_files=[])
