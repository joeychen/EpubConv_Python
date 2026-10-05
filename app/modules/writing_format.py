from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import cssutils
from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.enums.writing_format import WritingFormat
from app.modules.utils import dict_to_css_text, file_encoding
from config.config import AppConfig

cssutils.log.setLevel(logging.CRITICAL)

VERTICAL_STYLES: dict[str, str] = {
    "writing-mode": "vertical-rl",
    "-webkit-writing-mode": "vertical-rl",
    "-epub-writing-mode": "vertical-rl",
    "-epub-line-break": "strict",
    "line-break": "strict",
    "-epub-word-break": "normal",
    "word-break": "normal",
    "margin": "0",
    "padding": "0",
}


class WritingFormatConverter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def format(
        self,
        *,
        opf_path: Path,
        css_files: Sequence[Path],
        content_files: Sequence[Path],
    ) -> None:
        try:
            writing_format = WritingFormat(self.config.writing_format)
        except ValueError as error:
            raise ValueError(
                f"unsupported writing format: {self.config.writing_format!r}"
            ) from error

        opf = OpfFormat(opf_path)
        styles = StyleFile()
        match writing_format:
            case WritingFormat.VERTICAL:
                logger.info("將書籍書寫格式轉為直式")
                opf.add_vertical_attribute()
                if css_files and styles.selector_exists("html", css_files):
                    styles.append_vertical_styles(css_files, VERTICAL_STYLES)
                    return

                custom_css = styles.create_vertical_style(opf_path, VERTICAL_STYLES)
                self._insert_css(custom_css, content_files)
                self._insert_opf_item(opf_path, custom_css)
            case WritingFormat.HORIZONTAL:
                logger.info("將書籍書寫格式轉為橫式")
                opf.remove_vertical_attribute()
                styles.delete_vertical_styles(css_files, VERTICAL_STYLES)

    @staticmethod
    def _insert_css(css_path: Path, content_files: Sequence[Path]) -> None:
        html_suffixes = {".htm", ".html", ".xhtml"}
        for content_file in content_files:
            if content_file.suffix.lower() not in html_suffixes:
                continue

            content = content_file.read_text(encoding=file_encoding(content_file))
            soup = BeautifulSoup(content, "html.parser")
            if soup.head is None:
                head = soup.new_tag("head")
                if soup.html is None:
                    html = soup.new_tag("html")
                    html.append(head)
                    html.extend(list(soup.contents))
                    soup.clear()
                    soup.append(html)
                else:
                    soup.html.insert(0, head)

            href = Path(os.path.relpath(css_path, content_file.parent)).as_posix()
            if soup.head.find("link", href=href) is None:
                link = soup.new_tag(
                    "link",
                    attrs={"href": href, "rel": "stylesheet", "type": "text/css"},
                )
                soup.head.append(link)
            content_file.write_text(soup.prettify(), encoding="utf-8")

    @staticmethod
    def _insert_opf_item(opf_path: Path, css_path: Path) -> None:
        content = opf_path.read_text(encoding=file_encoding(opf_path))
        soup = BeautifulSoup(content, "xml")
        manifest = soup.find("manifest")
        if not isinstance(manifest, Tag):
            raise ValueError(f"OPF document has no manifest: {opf_path}")

        href = Path(os.path.relpath(css_path, opf_path.parent)).as_posix()
        if manifest.find("item", attrs={"id": "epubconv-custom-css"}) is None:
            item = soup.new_tag(
                "item",
                attrs={
                    "href": href,
                    "id": "epubconv-custom-css",
                    "media-type": "text/css",
                },
            )
            manifest.append(item)
        opf_path.write_text(soup.prettify(), encoding="utf-8")


class OpfFormat:
    def __init__(self, opf_path: Path) -> None:
        self.opf_path = opf_path

    def _document(self) -> tuple[BeautifulSoup, Tag]:
        content = self.opf_path.read_text(encoding=file_encoding(self.opf_path))
        soup = BeautifulSoup(content, "xml")
        spine = soup.find("spine")
        if not isinstance(spine, Tag):
            raise ValueError(f"OPF document has no spine: {self.opf_path}")
        return soup, spine

    def add_vertical_attribute(self) -> None:
        soup, spine = self._document()
        spine["page-progression-direction"] = "rtl"
        self.opf_path.write_text(soup.prettify(), encoding="utf-8")

    def remove_vertical_attribute(self) -> None:
        soup, spine = self._document()
        spine.attrs.pop("page-progression-direction", None)
        self.opf_path.write_text(soup.prettify(), encoding="utf-8")

    @property
    def writing_format(self) -> WritingFormat:
        _, spine = self._document()
        if spine.get("page-progression-direction") in {"ltr", "rtl"}:
            return WritingFormat.VERTICAL
        return WritingFormat.HORIZONTAL


class StyleFile:
    @staticmethod
    def _style_rules(css_file: Path):
        sheet = cssutils.CSSParser().parseFile(css_file)
        return sheet, sheet.cssRules.rulesOfType(cssutils.css.CSSRule.STYLE_RULE)

    def selector_exists(self, selector: str, css_files: Sequence[Path]) -> bool:
        return any(
            rule.selectorText == selector
            for css_file in css_files
            for rule in self._style_rules(css_file)[1]
        )

    @staticmethod
    def create_vertical_style(
        opf_path: Path,
        vertical_styles: Mapping[str, str],
    ) -> Path:
        css_file = opf_path.parent / "Styles" / "epubconv_custom.css"
        css_file.parent.mkdir(parents=True, exist_ok=True)
        declarations = dict_to_css_text(dict(vertical_styles))
        css_file.write_text(f"html {{\n{declarations}\n}}\n", encoding="utf-8")
        return css_file

    def delete_vertical_styles(
        self,
        css_files: Sequence[Path],
        vertical_styles: Mapping[str, str],
    ) -> None:
        for css_file in css_files:
            sheet, rules = self._style_rules(css_file)
            changed = False
            for rule in rules:
                if rule.selectorText != "html":
                    continue
                for name in vertical_styles:
                    if rule.style.getProperty(name):
                        rule.style.removeProperty(name)
                        changed = True
            if changed:
                css_file.write_bytes(sheet.cssText)

    def append_vertical_styles(
        self,
        css_files: Sequence[Path],
        vertical_styles: Mapping[str, str],
    ) -> None:
        for css_file in css_files:
            sheet, rules = self._style_rules(css_file)
            changed = False
            for rule in rules:
                if rule.selectorText != "html":
                    continue
                for name, value in vertical_styles.items():
                    rule.style.setProperty(name, value)
                    changed = True
            if changed:
                css_file.write_bytes(sheet.cssText)
