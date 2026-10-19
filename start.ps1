$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$candidate = if ($env:SUPERHOT_PYTHON) { $env:SUPERHOT_PYTHON } elseif (Test-Path -LiteralPath '.venv\Scripts\python.exe') { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' } elseif (Test-Path -LiteralPath 'D:\anaconda3\envs\SuperHot-dev\python.exe') { 'D:\anaconda3\envs\SuperHot-dev\python.exe' } else { (Get-Command python -ErrorAction Stop).Source }
& $candidate scripts/run.py
exit $LASTEXITCODE
