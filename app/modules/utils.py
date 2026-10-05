from pathlib import Path

import chardet
from loguru import logger


def file_encoding(file: str | Path) -> str:
    """Detect a text file's encoding, falling back to UTF-8 when unknown."""
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"檔案 {path} 不存在")

    detection = chardet.detect(path.read_bytes())
    logger.debug("{} encoding: {}", path.name, detection)
    encoding = detection.get("encoding")
    if not encoding:
        logger.warning("無法偵測 {} 的編碼；使用 UTF-8", path.name)
        return "utf-8"
    return str(encoding)


def dict_to_css_text(css_properties: dict[str, object]) -> str:
    """Render CSS properties as declarations."""
    return "\n".join(f"{name}: {value};" for name, value in css_properties.items())
