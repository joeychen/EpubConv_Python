import opencc

from app.enums.converter import OpenCCConverter
from app.models import Chapter, Chapters


class OpenCCEngine:
    """Convert chapter content with the local OpenCC library."""

    @staticmethod
    def _converter(name: str) -> opencc.OpenCC:
        try:
            converter = OpenCCConverter(name)
        except ValueError as error:
            raise ValueError(f"unsupported OpenCC converter: {name!r}") from error
        return opencc.OpenCC(converter.value)

    def convert(self, converter: str, chapters: Chapters) -> Chapters:
        opencc_converter = self._converter(converter)
        return [
            Chapter(
                path=chapter["path"],
                content=opencc_converter.convert(chapter["content"]),
            )
            for chapter in chapters
        ]

    def filename_convert(self, converter: str, filename: str) -> str:
        return self._converter(converter).convert(filename)
