# EpubConv Python

Convert EPUB text and filenames between Simplified and Traditional Chinese, and switch the
book layout between horizontal and vertical writing. Conversion can run locally through
[OpenCC](https://github.com/BYVoid/OpenCC) or online through the
[Fanhuaji (zhconvert) API](https://docs.zhconvert.org/api/convert/).

This is a fork of [ThanatosDi/EpubConv_Python](https://github.com/ThanatosDi/EpubConv_Python)
by ThanatosDi, rebased on upstream v3.1.0.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Run from source

```powershell
uv python install 3.14
uv sync --locked
uv run python main.py book.epub
```

Multiple EPUB paths may be supplied in one invocation. With the bundled `config.ini`
(converter `s2twp`, suffix enabled), the output is written next to the source file as, for
example, `book_s2twp.epub`. The original EPUB is not modified.

Edit `config.ini` to select the engine, converter, writing format, logging levels, and output
suffix behavior. Without `config.ini`, built-in defaults apply: OpenCC, `s2t`, horizontal.

Environment variables override the file. Their names are the uppercase setting names:
`ENGINE`, `CONVERTER`, `WRITING_FORMAT`, `LOG_LEVEL`, `STDOUT_LEVEL`, `ASYNC_LIMIT`,
`ASYNC_LIMIT_PER_HOST`, `FILE_CHECK`, `ENABLE_PAUSE`, and `ADD_SUFFIX`. Three differ from their
`config.ini` keys: `format` is `WRITING_FORMAT`, `loglevel` is `LOG_LEVEL`, and `stdlevel` is
`STDOUT_LEVEL`. For example, `CONVERTER=t2s` or `WRITING_FORMAT=vertical`.

To edit the same options with the interactive configuration wizard while running from source:

```powershell
uv run python setting.py
```

## Build a standalone Windows executable

PyInstaller bundles for the operating system on which it runs, so the Windows `.exe` must be
built on Windows. Python does not need to be installed on the destination computer.

### Automated local build

1. Install `uv` in PowerShell:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Open a new PowerShell window in the repository and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
   ```

3. The script writes `dist\epubconv.exe` and `dist\setting.exe`, copies `config.ini` beside
   them, and smoke-tests both applications.

Open `setting.exe` in a terminal. It displays numbered choices for the engine (OpenCC offline,
or zhconvert online, synchronous or async), conversion direction, book layout, request limits, logging, and output preferences.
Press Enter to keep the current choice. After confirmation, it atomically writes a formatted
`config.ini` in the same directory. `epubconv.exe` reads that file the next time it starts.

`epubconv.exe` also works without `config.ini` by using built-in defaults. EPUB files can be
dragged onto it in Windows Explorer or passed on the command line:

```powershell
.\dist\setting.exe
.\dist\epubconv.exe .\book.epub
```

### Manual build commands

The build script performs these steps explicitly:

```powershell
uv python install 3.14
uv sync --locked --python 3.14
uv run --no-sync pyinstaller main.spec --clean --noconfirm
uv run --no-sync pyinstaller setting.spec --clean --noconfirm
Copy-Item config.ini dist\config.ini -Force
.\dist\epubconv.exe --version
.\dist\setting.exe --smoke-test
```

PyInstaller bundles OpenCC's native extension through normal import analysis, and the OpenCC
hook from `pyinstaller-hooks-contrib` adds its conversion dictionaries. `main.spec` embeds
`epub.ico` and the Windows version resource, enables console output, and creates a single-file
bundle. `setting.spec` creates a separate single-file interactive console application.

### GitHub Actions

- `.github/workflows/windows-build.yml` runs on pushes and pull requests to `main`. It runs the
  build script and uploads both executables with the editable configuration as a workflow
  artifact.
- `.github/workflows/release.yml` runs when a `v*` tag is pushed. It checks that the tag
  matches the version in `app/__init__.py`, `pyproject.toml`, `file_version_info.txt`, and
  `setting_version_info.txt`, runs the tests, builds with the same script, and publishes
  `EpubConv.ver<version>.zip` (both executables and `config.ini`) as a GitHub release. A tag
  containing `-`, such as `v3.2.0-rc1`, is published as a pre-release. Running the workflow
  manually builds and uploads the zip without creating a release.

## Development checks

```powershell
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

## License and third-party services

The project is licensed under Apache-2.0. OpenCC is used for local conversion. Fanhuaji has its
own [commercial-use terms](https://docs.zhconvert.org/commercial/); review them before using its
API commercially.
