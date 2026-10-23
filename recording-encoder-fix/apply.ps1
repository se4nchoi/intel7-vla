param([string]$Container = 'physical-ai-studio-cuda')
$ErrorActionPreference = 'Stop'
$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$dockerExe = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe' }
if (-not (Test-Path $dockerExe)) { throw 'Docker CLI not found.' }
$patch = Get-Content (Join-Path $PSScriptRoot 'apply-lazy-depth.py') -Raw
$patch | & $dockerExe exec -i $Container .venv/bin/python -
if ($LASTEXITCODE -ne 0) { throw 'Patch failed. See output above. Container was not restarted.' }
Write-Host 'Patch installed. Stop recording and Teleoperate before restarting Studio:'
Write-Host "docker restart $Container"
