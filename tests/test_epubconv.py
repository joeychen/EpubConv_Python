from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from app.modules.epubconv import EpubConverter
from config.config import AppConfig

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile
      full-path="OEBPS/content.opf"
      media-type="application/oebps-package+xml"
    />
  </rootfiles>
</container>
"""

OPF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<package
  xmlns="http://www.idpf.org/2007/opf"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  version="3.0"
>
  <metadata><dc:language>zh-CN</dc:language></metadata>
  <manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="chapter"/></spine>
</package>
"""


def _create_epub(path: Path) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", OPF_XML)
        archive.writestr(
            "OEBPS/chapter.xhtml",
            "<html><head><title>测试</title></head><body>内存</body></html>",
        )


def test_end_to_end_opencc_conversion(tmp_path: Path) -> None:
    source = tmp_path / "sample.epub"
    _create_epub(source)
    config = AppConfig(converter="s2twp", add_suffix=True)

    output = EpubConverter(source, config).run()

    assert output == tmp_path / "sample_s2twp.epub"
    assert not (tmp_path / "sample.epub_files").exists()
    with ZipFile(output) as archive:
        assert archive.infolist()[0].filename == "mimetype"
        assert archive.infolist()[0].compress_type == ZIP_STORED
        assert "記憶體" in archive.read("OEBPS/chapter.xhtml").decode("utf-8")
        assert "zh-Hant-TW" in archive.read("OEBPS/content.opf").decode("utf-8")
