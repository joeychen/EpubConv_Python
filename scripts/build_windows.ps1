$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "PyInstaller must run on Windows to produce epubconv.exe and setting.exe."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot

try {
    & uv python install 3.14
    if ($LASTEXITCODE -ne 0) { throw "uv python install failed." }

    $pythonPath = (& uv python find 3.14).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $pythonPath) { throw "Python 3.14 was not found." }

    & uvx --from poetry==2.4.1 poetry env use $pythonPath
    if ($LASTEXITCODE -ne 0) { throw "Poetry could not select Python 3.14." }

    & uvx --from poetry==2.4.1 poetry sync --with dev --no-root
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

    & uvx --from poetry==2.4.1 poetry run pyinstaller main.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "epubconv.exe build failed." }

    & uvx --from poetry==2.4.1 poetry run pyinstaller setting.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "setting.exe build failed." }

    Copy-Item config.ini dist\config.ini -Force
    & .\dist\epubconv.exe --version
    if ($LASTEXITCODE -ne 0) { throw "epubconv.exe smoke test failed." }

    & .\dist\setting.exe --smoke-test
    if ($LASTEXITCODE -ne 0) { throw "setting.exe smoke test failed." }

    Write-Host "Built $projectRoot\dist\epubconv.exe"
    Write-Host "Built $projectRoot\dist\setting.exe"
}
finally {
    Pop-Location
}
