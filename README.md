# EpubConv Python

Convert EPUB text and filenames between Simplified and Traditional Chinese, and switch the
book layout between horizontal and vertical writing. Conversion can run locally through
[OpenCC](https://github.com/BYVoid/OpenCC) or through the
[Fanhuaji API](https://docs.zhconvert.org/api/convert/).

## Requirements

- Python 3.14
- Poetry 2.4.1 (the commands below run it through `uvx`, so a global Poetry install is not
  required)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Run from source

```powershell
uv python install 3.14
uvx --from poetry==2.4.1 poetry env use 3.14
uvx --from poetry==2.4.1 poetry sync --with dev --no-root
uvx --from poetry==2.4.1 poetry run python main.py book.epub
```

Multiple EPUB paths may be supplied in one invocation. The default configuration creates an
output such as `book_s2twp.epub` next to the source file. The original EPUB is not modified.

Edit `config.ini` to select the engine, converter, writing format, logging levels, and output
suffix behavior. Environment variables with the corresponding uppercase names override the
file; for example, `ENGINE=opencc` or `CONVERTER=t2s`.

To edit the same options with the interactive configuration wizard while running from source:

```powershell
uvx --from poetry==2.4.1 poetry run python setting.py
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

Open `setting.exe` in a terminal. It displays numbered choices for the OpenCC or zhconvert
engine, conversion direction, book layout, request limits, logging, and output preferences.
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
$pythonPath = (uv python find 3.14).Trim()
uvx --from poetry==2.4.1 poetry env use $pythonPath
uvx --from poetry==2.4.1 poetry sync --with dev --no-root
uvx --from poetry==2.4.1 poetry run pyinstaller main.spec --clean --noconfirm
uvx --from poetry==2.4.1 poetry run pyinstaller setting.spec --clean --noconfirm
Copy-Item config.ini dist\config.ini -Force
.\dist\epubconv.exe --version
.\dist\setting.exe --smoke-test
```

PyInstaller's OpenCC hook collects the native library and conversion data. `main.spec` embeds
`epub.ico` and the Windows version resource, enables console output, and creates a single-file
bundle. `setting.spec` creates a separate single-file interactive console application.
The GitHub Actions workflow in `.github/workflows/windows-build.yml` runs the same script and
uploads both executables with the editable configuration.

## Development checks

```powershell
uvx --from poetry==2.4.1 poetry check --lock --strict
uvx --from poetry==2.4.1 poetry run ruff format --check .
uvx --from poetry==2.4.1 poetry run ruff check .
uvx --from poetry==2.4.1 poetry run pytest
```

## License and third-party services

The project is licensed under Apache-2.0. OpenCC is used for local conversion. Fanhuaji has its
own [commercial-use terms](https://docs.zhconvert.org/commercial/); review them before using its
API commercially.

## Downloads and support

- [Published releases](https://github.com/ThanatosDi/EpubConv_Python/releases)
- [Support the original author](https://p.ecpay.com.tw/7D0E7)

Thank you to the donor recorded by the original project: 蕭先生/小姐 (2019-10-24).
