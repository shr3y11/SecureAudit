$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements-dev.txt first.' }
Push-Location $PSScriptRoot
try {
    & $taskPython -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Build stopped.' }
    & $taskPython tools\build_portable.py
    if ($LASTEXITCODE -ne 0) { throw 'Portable central executable build failed.' }
    & $taskPython tools\package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Release ZIP verification failed.' }
    Write-Host 'Built the versioned portable folder and ZIP under dist. Keep the folder together; see docs/RELEASE_GUIDE.md.'
} finally { Pop-Location }
