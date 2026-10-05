from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.enums.converter import Converter
from app.enums.engine import Engine
from app.enums.writing_format import WritingFormat
from config.config import AppConfig, AppConfigError, application_directory

APP_TITLE = "EpubConv configuration wizard"

type InputFunction = Callable[[str], str]
type OutputFunction = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class Choice[T]:
    label: str
    value: T


ENGINE_CHOICES = (
    Choice("OpenCC (offline)", Engine.OPENCC),
    Choice("zhconvert (online)", Engine.FANHUAJI),
    Choice("zhconvert async (online)", Engine.FANHUAJI_ASYNC),
)

CONVERTER_CHOICES = (
    Choice("Simplified to Traditional (s2t)", Converter.S2T),
    Choice("Simplified to Taiwan (s2tw)", Converter.S2TW),
    Choice("Simplified to Taiwan with phrases (s2twp)", Converter.S2TWP),
    Choice("Traditional to Simplified (t2s)", Converter.T2S),
    Choice("Taiwan to Simplified (tw2s)", Converter.TW2S),
    Choice("Taiwan to China with phrases (tw2sp)", Converter.TW2SP),
)

FORMAT_CHOICES = (
    Choice("Horizontal", WritingFormat.HORIZONTAL),
    Choice("Vertical, right to left", WritingFormat.VERTICAL),
)

LOG_LEVEL_CHOICES = tuple(
    Choice(level.title(), level) for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
)

ASYNC_LIMIT_CHOICES = tuple(Choice(str(limit), limit) for limit in (1, 3, 5, 10, 20))
ASYNC_HOST_LIMIT_CHOICES = tuple(Choice(str(limit), limit) for limit in range(1, 6))

BOOLEAN_CHOICES = (
    Choice("Yes", True),
    Choice("No", False),
)


def ask_choice[T](
    heading: str,
    choices: Sequence[Choice[T]],
    default: T,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> T:
    """Display numbered choices and keep prompting until a valid selection is made."""
    if not choices:
        raise ValueError("at least one choice is required")

    default_index = next(
        (index for index, choice in enumerate(choices, start=1) if choice.value == default),
        1,
    )
    output_fn("")
    output_fn(heading)
    for index, choice in enumerate(choices, start=1):
        marker = " (current)" if index == default_index else ""
        output_fn(f"  {index}. {choice.label}{marker}")

    while True:
        answer = input_fn(f"Select 1-{len(choices)} [{default_index}]: ").strip()
        if not answer:
            return choices[default_index - 1].value
        if answer.isdecimal():
            selected = int(answer)
            if 1 <= selected <= len(choices):
                return choices[selected - 1].value
        output_fn(f"Please enter a number from 1 to {len(choices)}.")


def _choices_with_current(
    choices: Sequence[Choice[int]],
    current: int,
) -> tuple[Choice[int], ...]:
    if any(choice.value == current for choice in choices):
        return tuple(choices)
    return tuple(sorted((*choices, Choice(str(current), current)), key=lambda choice: choice.value))


def load_existing_config(path: Path) -> tuple[AppConfig, str | None]:
    try:
        config = AppConfig.load(path, {})
    except AppConfigError as error:
        return AppConfig(), f"Existing config.ini is invalid; using defaults: {error}"

    valid = (
        config.engine in {choice.value for choice in ENGINE_CHOICES}
        and config.converter in {choice.value for choice in CONVERTER_CHOICES}
        and config.writing_format in {choice.value for choice in FORMAT_CHOICES}
        and config.log_level in {choice.value for choice in LOG_LEVEL_CHOICES}
        and config.stdout_level in {choice.value for choice in LOG_LEVEL_CHOICES}
    )
    if not valid:
        return AppConfig(), "Existing config.ini contains unsupported values; using defaults."
    return config, None


def prompt_for_config(
    current: AppConfig,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> AppConfig:
    """Prompt for every configuration value and return the selected config."""
    engine = ask_choice(
        "[1/10] Conversion engine",
        ENGINE_CHOICES,
        current.engine,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    converter = ask_choice(
        "[2/10] Conversion direction",
        CONVERTER_CHOICES,
        current.converter,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    writing_format = ask_choice(
        "[3/10] Book layout",
        FORMAT_CHOICES,
        current.writing_format,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    log_level = ask_choice(
        "[4/10] Log file level",
        LOG_LEVEL_CHOICES,
        current.log_level,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    stdout_level = ask_choice(
        "[5/10] Console log level",
        LOG_LEVEL_CHOICES,
        current.stdout_level,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    async_limit = ask_choice(
        "[6/10] Maximum concurrent zhconvert requests",
        _choices_with_current(ASYNC_LIMIT_CHOICES, current.async_limit),
        current.async_limit,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    async_limit_per_host = ask_choice(
        "[7/10] Maximum zhconvert requests per host",
        _choices_with_current(ASYNC_HOST_LIMIT_CHOICES, current.async_limit_per_host),
        current.async_limit_per_host,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    file_check = ask_choice(
        "[8/10] Verify that the input is a valid EPUB archive",
        BOOLEAN_CHOICES,
        current.file_check,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    enable_pause = ask_choice(
        "[9/10] Pause before epubconv.exe closes",
        BOOLEAN_CHOICES,
        current.enable_pause,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    add_suffix = ask_choice(
        "[10/10] Add the conversion mode to the output filename",
        BOOLEAN_CHOICES,
        current.add_suffix,
        input_fn=input_fn,
        output_fn=output_fn,
    )

    return AppConfig(
        engine=engine,
        converter=converter,
        writing_format=writing_format,
        log_level=log_level,
        stdout_level=stdout_level,
        async_limit=async_limit,
        async_limit_per_host=async_limit_per_host,
        file_check=file_check,
        enable_pause=enable_pause,
        add_suffix=add_suffix,
    )


def run_wizard(
    config_path: Path | None = None,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> Path | None:
    """Run the interactive wizard and save the selected configuration."""
    path = config_path or application_directory() / "config.ini"
    current, warning = load_existing_config(path)

    output_fn(APP_TITLE)
    output_fn(f"Configuration file: {path}")
    output_fn("Press Enter to keep the current choice.")
    if warning:
        output_fn(f"Warning: {warning}")

    selected = prompt_for_config(current, input_fn=input_fn, output_fn=output_fn)
    should_save = ask_choice(
        "Save this configuration?",
        BOOLEAN_CHOICES,
        True,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    if not should_save:
        output_fn("Configuration was not changed.")
        return None

    saved_path = selected.save(path)
    output_fn("")
    output_fn(f"Saved configuration to {saved_path}")
    return saved_path


def smoke_test(config_path: Path | None = None) -> int:
    """Validate that the frozen application can read and render its config."""
    path = config_path or application_directory() / "config.ini"
    AppConfig.load(path, {}).to_ini()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.smoke_test:
        return smoke_test()

    try:
        run_wizard()
    except EOFError, KeyboardInterrupt:
        print("\nConfiguration was not changed.")
        return 130
    except OSError as error:
        print(f"Could not save configuration: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
