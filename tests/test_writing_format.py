from pathlib import Path

from bs4 import BeautifulSoup

from app.modules.writing_format import OpfFormat, WritingFormatConverter
from config.config import AppConfig

OPF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest></manifest>
  <spine></spine>
</package>
"""


def test_vertical_format_adds_custom_stylesheet(tmp_path: Path) -> None:
    opf = tmp_path / "OEBPS" / "content.opf"
    chapter = tmp_path / "OEBPS" / "Text" / "chapter.xhtml"
    opf.parent.mkdir(parents=True)
    chapter.parent.mkdir(parents=True)
    opf.write_text(OPF_XML, encoding="utf-8")
    chapter.write_text("<html><head></head><body>內容</body></html>", encoding="utf-8")

    WritingFormatConverter(AppConfig(writing_format="vertical")).format(
        opf_path=opf,
        css_files=[],
        content_files=[chapter],
    )

    assert OpfFormat(opf).writing_format == "vertical"
    custom_css = opf.parent / "Styles" / "epubconv_custom.css"
    assert "writing-mode: vertical-rl" in custom_css.read_text(encoding="utf-8")
    chapter_soup = BeautifulSoup(chapter.read_text(encoding="utf-8"), "html.parser")
    assert chapter_soup.find("link", href="../Styles/epubconv_custom.css") is not None
    assert "epubconv-custom-css" in opf.read_text(encoding="utf-8")


def test_horizontal_format_removes_vertical_css(tmp_path: Path) -> None:
    opf = tmp_path / "content.opf"
    css = tmp_path / "book.css"
    opf.write_text(
        OPF_XML.replace("<spine>", '<spine page-progression-direction="rtl">'), encoding="utf-8"
    )
    css.write_text("html { writing-mode: vertical-rl; color: black; }", encoding="utf-8")

    WritingFormatConverter(AppConfig(writing_format="horizontal")).format(
        opf_path=opf,
        css_files=[css],
        content_files=[],
    )

    assert OpfFormat(opf).writing_format == "horizontal"
    css_content = css.read_text(encoding="utf-8")
    assert "writing-mode" not in css_content
    assert "color: black" in css_content
