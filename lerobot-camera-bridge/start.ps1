$ErrorActionPreference = 'Stop'
$bindAddress = (& "$env:WINDIR/System32/wsl.exe" -d Ubuntu-24.04 -- python3 /mnt/c/Users/user/rjsxo/workflows/camera_address.py | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $bindAddress) { throw 'Cannot determine Windows camera endpoint from WSL.' }
$python = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/pythonw.exe'
$listener = Get-NetTCPConnection -LocalAddress $bindAddress -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -FilePath $python -WindowStyle Hidden -ArgumentList @('"' + (Join-Path $PSScriptRoot 'relay.py') + '"', '--bind', $bindAddress)
}
Write-Host "LeRobot camera relay: tcp://${bindAddress}:5555"
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'camera-bridge/start-field.ps1')
$fieldListener = Get-NetTCPConnection -LocalAddress $bindAddress -LocalPort 5556 -State Listen -ErrorAction SilentlyContinue
if (-not $fieldListener) {
    Start-Process -FilePath $python -WindowStyle Hidden -ArgumentList @('"' + (Join-Path $PSScriptRoot 'relay.py') + '"','--bind',$bindAddress,'--port','5556','--camera-name','field_cam','--source','http://127.0.0.1:8766/camera.mjpg')
}
Write-Host "LeRobot field camera relay: tcp://${bindAddress}:5556"
