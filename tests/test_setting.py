from pathlib import Path

from app.enums.converter import Converter
from app.enums.engine import Engine
from app.enums.writing_format import WritingFormat
from config.config import AppConfig
from setting import (
    CONVERTER_CHOICES,
    ENGINE_CHOICES,
    FORMAT_CHOICES,
    Choice,
    ask_choice,
    prompt_for_config,
    run_wizard,
    smoke_test,
)


def _answers(*answers: str):
    iterator = iter(answers)
    return lambda _prompt: next(iterator)


def test_settings_options_cover_every_supported_value() -> None:
    assert {choice.value for choice in ENGINE_CHOICES} == set(Engine)
    assert {choice.value for choice in CONVERTER_CHOICES} == set(Converter)
    assert {choice.value for choice in FORMAT_CHOICES} == set(WritingFormat)


def test_ask_choice_reprompts_until_number_is_valid() -> None:
    output: list[str] = []

    selected = ask_choice(
        "Pick one",
        (Choice("First", "first"), Choice("Second", "second")),
        "first",
        input_fn=_answers("invalid", "3", "2"),
        output_fn=output.append,
    )

    assert selected == "second"
    assert output.count("Please enter a number from 1 to 2.") == 2


def test_blank_answer_keeps_current_choice() -> None:
    selected = ask_choice(
        "Pick one",
        (Choice("First", "first"), Choice("Second", "second")),
        "second",
        input_fn=_answers(""),
        output_fn=lambda _message: None,
    )
    assert selected == "second"


def test_prompt_for_config_maps_numbered_answers() -> None:
    selected = prompt_for_config(
        AppConfig(),
        input_fn=_answers("2", "4", "2", "3", "4", "4", "2", "2", "1", "2"),
        output_fn=lambda _message: None,
    )

    assert selected == AppConfig(
        engine="fanhuaji",
        converter="t2s",
        writing_format="vertical",
        log_level="WARNING",
        stdout_level="ERROR",
        async_limit=10,
        async_limit_per_host=2,
        file_check=False,
        enable_pause=True,
        add_suffix=False,
    )


def test_wizard_generates_formatted_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    output: list[str] = []

    saved_path = run_wizard(
        config_path,
        input_fn=_answers(*([""] * 11)),
        output_fn=output.append,
    )

    assert saved_path == config_path
    assert AppConfig.load(config_path, {}) == AppConfig()
    assert config_path.read_text(encoding="utf-8") == AppConfig().to_ini()
    assert output[-1] == f"Saved configuration to {config_path}"


def test_wizard_can_cancel_without_writing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"

    saved_path = run_wizard(
        config_path,
        input_fn=_answers(*([""] * 10), "2"),
        output_fn=lambda _message: None,
    )

    assert saved_path is None
    assert not config_path.exists()


def test_settings_smoke_test_reads_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    expected = AppConfig(engine="fanhuaji", converter="t2s", writing_format="vertical")
    expected.save(config_path)

    assert smoke_test(config_path) == 0
    assert AppConfig.load(config_path, {}) == expected
