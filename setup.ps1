$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($env:SUPERHOT_PYTHON) { $candidate = $env:SUPERHOT_PYTHON }
elseif (Test-Path -LiteralPath 'D:\anaconda3\envs\SuperHot-dev\python.exe') { $candidate = 'D:\anaconda3\envs\SuperHot-dev\python.exe' }
else {
    $basePython = (Get-Command python -ErrorAction Stop).Source
    & $basePython -c 'import sys; assert sys.version_info[:2] == (3, 13), "Use Python 3.13"'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 is required.' }
    & $basePython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment.' }
    $candidate = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}
& $candidate -m pip install --index-url https://pypi.org/simple -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
Push-Location -LiteralPath frontend
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Write-Output 'Setup complete. Run .\start.ps1 to start SuperHot.'
