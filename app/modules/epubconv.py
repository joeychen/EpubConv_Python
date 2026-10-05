from __future__ import annotations

import shutil
from pathlib import Path
from xml.etree import ElementTree
from zipfile import is_zipfile

from loguru import logger

from app.models import Chapter, Chapters
from app.modules.convert import convert_chapters
from app.modules.opf import update_language
from app.modules.renamer import publish_converted_file
from app.modules.utils import file_encoding
from app.modules.writing_format import WritingFormatConverter
from app.modules.zip import EpubArchive
from config.config import AppConfig

_CONTENT_SUFFIXES = {".htm", ".html", ".ncx", ".opf", ".txt", ".xhtml"}


class EpubFiles:
    """Discover files inside an extracted EPUB directory."""

    def __init__(self, extracted_path: Path) -> None:
        self.extracted_path = extracted_path

    @property
    def content_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.extracted_path.rglob("*")
            if path.is_file() and path.suffix.lower() in _CONTENT_SUFFIXES
        )

    @property
    def css_files(self) -> list[Path]:
        return sorted(self.extracted_path.rglob("*.css"))

    @property
    def opf_file(self) -> Path:
        container_path = self.extracted_path / "META-INF" / "container.xml"
        if container_path.is_file():
            tree = ElementTree.parse(container_path)
            rootfile = next(
                (
                    element
                    for element in tree.iter()
                    if element.tag.rsplit("}", 1)[-1] == "rootfile" and element.get("full-path")
                ),
                None,
            )
            if rootfile is not None:
                candidate = (self.extracted_path / str(rootfile.get("full-path"))).resolve()
                if candidate.is_relative_to(self.extracted_path.resolve()) and candidate.is_file():
                    return candidate

        candidates = sorted(self.extracted_path.rglob("*.opf"))
        if not candidates:
            raise FileNotFoundError("EPUB contains no OPF package document")
        return candidates[0]


class EpubConverter:
    """Coordinate extraction, conversion, formatting, and EPUB rebuilding."""

    def __init__(self, epub_path: str | Path, config: AppConfig) -> None:
        self.source = Path(epub_path).expanduser().resolve()
        self.config = config
        self.extracted_path = self.source.with_name(f"{self.source.name}_files")

        if not self.source.is_file():
            raise FileNotFoundError(f"EPUB file does not exist: {self.source}")
        if self.source.suffix.lower() != ".epub":
            raise ValueError(f"input file must use the .epub extension: {self.source}")
        if config.file_check and not is_zipfile(self.source):
            raise ValueError(f"input is not a valid ZIP/EPUB file: {self.source}")

    def run(self) -> Path:
        logger.info("正在處理 EPUB: {}", self.source)
        EpubArchive.extract(self.source, self.extracted_path)
        try:
            files = EpubFiles(self.extracted_path)
            content_files = files.content_files
            css_files = files.css_files
            opf_file = files.opf_file

            self._convert_content(content_files)
            converted_opf = opf_file.with_name(f"{opf_file.name}.new")
            update_language(converted_opf, self.config.converter)
            for content_file in content_files:
                publish_converted_file(content_file)

            WritingFormatConverter(self.config).format(
                opf_path=opf_file,
                css_files=css_files,
                content_files=content_files,
            )
            output = EpubArchive.compress(self.source, self.extracted_path, self.config)
            logger.info("完成: {}", output)
            return output
        finally:
            self.clean()

    def _convert_content(self, content_files: list[Path]) -> None:
        chapters: Chapters = []
        for content_file in content_files:
            content = content_file.read_text(encoding=file_encoding(content_file))
            chapters.append(Chapter(path=str(content_file), content=content))

        for chapter in convert_chapters(chapters, self.config):
            original = Path(chapter["path"])
            converted = original.with_name(f"{original.name}.new")
            converted.write_text(chapter["content"], encoding="utf-8")

    def clean(self) -> None:
        if self.extracted_path.is_dir():
            logger.debug("刪除暫存目錄: {}", self.extracted_path)
            shutil.rmtree(self.extracted_path)
