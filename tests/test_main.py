from unittest.mock import patch

import pytest

import main as cli
from config.config import AppConfig


def test_version_does_not_load_configuration(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(AppConfig, "load", side_effect=AssertionError("config was loaded")),
        pytest.raises(SystemExit) as exit_info,
    ):
        cli.main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == "epubconv 3.0.0"
