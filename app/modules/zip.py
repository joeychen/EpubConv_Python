from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from loguru import logger

from app.engines.opencc import OpenCCEngine
from app.enums.converter import FILENAME_CONVERTERS
from config.config import AppConfig


class EpubArchive:
    """Safely extract and rebuild EPUB ZIP containers."""

    @staticmethod
    def extract(source: Path, destination: Path) -> None:
        if destination.exists():
            raise FileExistsError(f"temporary directory already exists: {destination}")
        destination.mkdir()

        try:
            with ZipFile(source) as archive:
                for member in archive.infolist():
                    member_path = PurePosixPath(member.filename.replace("\\", "/"))
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise BadZipFile(f"unsafe archive member: {member.filename!r}")
                archive.extractall(destination)
        except Exception:
            shutil.rmtree(destination)
            raise

    @staticmethod
    def output_path(source: Path, config: AppConfig) -> Path:
        filename_converter = FILENAME_CONVERTERS.get(config.converter, "s2t")
        converted_name = OpenCCEngine().filename_convert(filename_converter, source.name)
        output = source.with_name(converted_name)
        if config.add_suffix:
            output = output.with_name(f"{output.stem}_{config.converter}.epub")
        elif output == source:
            output = source.with_name(f"{source.stem}_converted.epub")
        return output

    @classmethod
    def compress(cls, source: Path, extracted: Path, config: AppConfig) -> Path:
        output = cls.output_path(source, config)
        if output.exists():
            raise FileExistsError(f"output file already exists: {output}")

        temporary = output.with_name(f"{output.name}.tmp")
        if temporary.exists():
            raise FileExistsError(f"temporary output already exists: {temporary}")

        files = sorted(path for path in extracted.rglob("*") if path.is_file())
        mimetype = extracted / "mimetype"
        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
                if mimetype.is_file():
                    archive.write(mimetype, "mimetype", compress_type=ZIP_STORED)
                for file in files:
                    if file == mimetype:
                        continue
                    archive_name = file.relative_to(extracted).as_posix()
                    logger.debug("壓縮: {}", archive_name)
                    archive.write(file, archive_name, compress_type=ZIP_DEFLATED)
            temporary.replace(output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return output
