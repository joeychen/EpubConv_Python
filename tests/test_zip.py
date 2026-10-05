from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pytest

from app.modules.zip import EpubArchive


def test_extract_rejects_path_traversal_and_cleans_destination(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.epub"
    destination = tmp_path / "extracted"
    with ZipFile(source, "w") as archive:
        archive.writestr("../escape.txt", "unsafe")

    with pytest.raises(BadZipFile, match="unsafe archive member"):
        EpubArchive.extract(source, destination)

    assert not destination.exists()
    assert not (tmp_path / "escape.txt").exists()
