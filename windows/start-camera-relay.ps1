$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$wslRoot = '/mnt/' + $root.Substring(0,1).ToLower() + $root.Substring(2).Replace('\','/')
$relay = Join-Path $PSScriptRoot 'relay.py'
$bindAddress = (& "$env:WINDIR/System32/wsl.exe" -d Ubuntu-24.04 -- python3 "$wslRoot/src/intel7_vla/common/camera_address.py" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $bindAddress) { throw 'Cannot determine Windows camera endpoint from WSL.' }
$python = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/pythonw.exe'
$listener = Get-NetTCPConnection -LocalAddress $bindAddress -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -FilePath $python -WindowStyle Hidden -ArgumentList @('"' + $relay + '"', '--bind', $bindAddress)
}
Write-Host "LeRobot camera relay: tcp://${bindAddress}:5555"
& (Join-Path $PSScriptRoot 'start-field-camera.ps1')
$fieldListener = Get-NetTCPConnection -LocalAddress $bindAddress -LocalPort 5556 -State Listen -ErrorAction SilentlyContinue
if (-not $fieldListener) {
    Start-Process -FilePath $python -WindowStyle Hidden -ArgumentList @('"' + $relay + '"','--bind',$bindAddress,'--port','5556','--camera-name','field_cam','--source','http://127.0.0.1:8766/camera.mjpg')
}
Write-Host "LeRobot field camera relay: tcp://${bindAddress}:5556"
