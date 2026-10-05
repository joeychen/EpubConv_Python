from pathlib import Path

from loguru import logger


def publish_converted_file(original: str | Path) -> None:
    """Atomically replace a source file with its adjacent `.new` conversion."""
    original_path = Path(original)
    converted_path = original_path.with_name(f"{original_path.name}.new")
    if not converted_path.is_file():
        raise FileNotFoundError(f"converted file does not exist: {converted_path}")
    logger.debug("重新命名: {} -> {}", converted_path.name, original_path.name)
    converted_path.replace(original_path)
