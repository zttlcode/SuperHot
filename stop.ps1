$ErrorActionPreference = 'Stop'
$runtimeDirectory = if ($env:SUPERHOT_RUNTIME) { $env:SUPERHOT_RUNTIME } else { Join-Path $PSScriptRoot '.runtime' }
$heartbeatFile = Join-Path $runtimeDirectory 'launcher.heartbeat'
if (-not (Test-Path -LiteralPath $heartbeatFile) -or ((Get-Date) - (Get-Item -LiteralPath $heartbeatFile).LastWriteTime).TotalSeconds -gt 20) { Write-Output 'SuperHot is not running.'; exit 0 }
New-Item -ItemType File -Force -Path (Join-Path $runtimeDirectory 'stop.request') | Out-Null
Write-Output 'Stop requested. The launcher will shut down API and monitoring.'
