from pathlib import Path

import pytest

from config.config import AppConfig, AppConfigError


def test_config_loads_ini_and_environment_override(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        """
[ConvertSetting]
engine=fanhuaji
converter=s2twp
format=vertical
loglevel=warning
stdlevel=debug

[AsyncSetting]
async_limit=7
async_limit_per_host=4

[OtherSetting]
file_check=false
enable_pause=yes
add_suffix=0
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig.load(config_path, {"ENGINE": "opencc"})

    assert config.engine == "opencc"
    assert config.converter == "s2twp"
    assert config.writing_format == "vertical"
    assert config.async_limit == 7
    assert config.file_check is False
    assert config.enable_pause is True
    assert config.add_suffix is False


def test_config_rejects_invalid_boolean(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    config_path.write_text("[OtherSetting]\nfile_check=maybe\n", encoding="utf-8")
    with pytest.raises(AppConfigError, match="FILE_CHECK"):
        AppConfig.load(config_path, {})


def test_config_rejects_malformed_ini(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    config_path.write_text("[ConvertSetting\nengine=opencc\n", encoding="utf-8")

    with pytest.raises(AppConfigError, match="cannot read config file"):
        AppConfig.load(config_path, {})


def test_config_save_is_formatted_and_round_trips(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    config = AppConfig(
        engine="fanhuaji_async",
        converter="tw2sp",
        writing_format="vertical",
        log_level="WARNING",
        stdout_level="ERROR",
        async_limit=8,
        async_limit_per_host=4,
        file_check=False,
        enable_pause=True,
        add_suffix=False,
    )

    saved_path = config.save(config_path)

    assert saved_path == config_path
    assert config_path.read_text(encoding="utf-8") == config.to_ini()
    assert "\n\n[AsyncSetting]\n" in config.to_ini()
    assert "file_check=false\n" in config.to_ini()
    assert AppConfig.load(config_path, {}) == config
    assert not (tmp_path / ".config.ini.tmp").exists()
