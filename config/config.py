from __future__ import annotations

import configparser
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path


class AppConfigError(ValueError):
    """Raised when a configuration value cannot be parsed."""


def application_directory() -> Path:
    """Return the directory used for user-editable config and runtime output."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise AppConfigError(f"invalid boolean value: {value!r}")


_INI_LOCATIONS: dict[str, tuple[str, str]] = {
    "engine": ("ConvertSetting", "engine"),
    "converter": ("ConvertSetting", "converter"),
    "writing_format": ("ConvertSetting", "format"),
    "log_level": ("ConvertSetting", "loglevel"),
    "stdout_level": ("ConvertSetting", "stdlevel"),
    "async_limit": ("AsyncSetting", "async_limit"),
    "async_limit_per_host": ("AsyncSetting", "async_limit_per_host"),
    "file_check": ("OtherSetting", "file_check"),
    "enable_pause": ("OtherSetting", "enable_pause"),
    "add_suffix": ("OtherSetting", "add_suffix"),
}


@dataclass(frozen=True, slots=True)
class AppConfig:
    engine: str = "opencc"
    converter: str = "s2t"
    writing_format: str = "horizontal"
    log_level: str = "INFO"
    stdout_level: str = "INFO"
    async_limit: int = 5
    async_limit_per_host: int = 5
    file_check: bool = True
    enable_pause: bool = False
    add_suffix: bool = True

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> AppConfig:
        config_path = path or application_directory() / "config.ini"
        environment = os.environ if environ is None else environ
        parser = configparser.ConfigParser()
        if config_path.is_file():
            try:
                parser.read(config_path, encoding="utf-8")
            except (configparser.Error, OSError, UnicodeError) as error:
                raise AppConfigError(f"cannot read config file {config_path}: {error}") from error

        defaults = cls()
        values: dict[str, str | int | bool] = {}
        for field in fields(cls):
            default = getattr(defaults, field.name)
            section, option = _INI_LOCATIONS[field.name]
            raw_value = environment.get(field.name.upper())
            if raw_value is None and parser.has_option(section, option):
                raw_value = parser.get(section, option)
            if raw_value is None:
                values[field.name] = default
                continue

            try:
                if isinstance(default, bool):
                    values[field.name] = _parse_bool(raw_value)
                elif isinstance(default, int):
                    values[field.name] = int(raw_value)
                elif field.name in {"log_level", "stdout_level"}:
                    values[field.name] = raw_value.strip().upper()
                else:
                    values[field.name] = raw_value.strip().lower()
            except (TypeError, ValueError) as error:
                raise AppConfigError(f"cannot parse {field.name.upper()}={raw_value!r}") from error

        loaded = cls(**values)
        if loaded.async_limit < 1 or loaded.async_limit_per_host < 1:
            raise AppConfigError("async limits must be positive integers")
        return loaded

    def to_ini(self) -> str:
        """Render the complete application configuration in a stable INI format."""
        return (
            "[ConvertSetting]\n"
            "# 轉換相關設定\n"
            f"engine={self.engine}\n"
            f"converter={self.converter}\n"
            f"format={self.writing_format}\n"
            f"loglevel={self.log_level.lower()}\n"
            f"stdlevel={self.stdout_level.lower()}\n"
            "\n"
            "[AsyncSetting]\n"
            "# 繁化姬異步請求設定，請不要設定過高避免 429 錯誤發生\n"
            "# 繁化姬 API: rate=20r/s, burst=20 nodelay\n"
            f"async_limit={self.async_limit}\n"
            f"async_limit_per_host={self.async_limit_per_host}\n"
            "\n"
            "[OtherSetting]\n"
            "# 其他相關設定\n"
            f"file_check={str(self.file_check).lower()}\n"
            f"enable_pause={str(self.enable_pause).lower()}\n"
            f"add_suffix={str(self.add_suffix).lower()}\n"
        )

    def save(self, path: Path | None = None) -> Path:
        """Atomically write a formatted config file and return its path."""
        config_path = path or application_directory() / "config.ini"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = config_path.with_name(f".{config_path.name}.tmp")
        try:
            temporary.write_text(self.to_ini(), encoding="utf-8", newline="\n")
            temporary.replace(config_path)
        finally:
            temporary.unlink(missing_ok=True)
        return config_path
