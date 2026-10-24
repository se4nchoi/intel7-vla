param([string]$PythonExe, [string]$CameraHardwareId = '32e6:9211')
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run PowerShell as administrator under the same Windows account used for Studio.'
}
if ($CameraHardwareId -notmatch '^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$') { throw 'Invalid camera VID:PID.' }
$CameraHardwareId = $CameraHardwareId.ToLower()
$destination = Join-Path $env:LOCALAPPDATA 'PhysicalAICameraBridge'
$autoPath = Join-Path $env:ProgramData 'usbipd-autoattach\usbipd-autoattach.ps1'
$usbipd = (Get-Command usbipd.exe -ErrorAction Stop).Source
if (-not (Test-Path $autoPath)) { throw "USB autoattach script not found: $autoPath" }
$autoTask = Get-ScheduledTask -TaskName usbipd-autoattach -ErrorAction Stop
if (-not $PythonExe) {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $PythonExe = (& py.exe -3 -c 'import sys; print(sys.executable)' | Select-Object -Last 1)
    } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
        $PythonExe = (Get-Command python.exe).Source
    }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) { throw 'Install Python 3.12+ or pass -PythonExe C:\path\python.exe.' }
& $PythonExe -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12+ required.' }
New-Item -ItemType Directory -Force $destination | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'server.py') (Join-Path $destination 'server.py') -Force
Copy-Item (Join-Path $PSScriptRoot 'requirements.txt') $destination -Force
$venv = Join-Path $destination '.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install -r (Join-Path $destination 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; USB settings have not been changed.' }
& $python -m py_compile (Join-Path $destination 'server.py')
if ($LASTEXITCODE -ne 0) { throw 'Server validation failed.' }

$backup = Join-Path $destination 'original-autoattach.ps1'
if (-not (Test-Path $backup)) { Copy-Item $autoPath $backup }
$text = [IO.File]::ReadAllText($autoPath)
$pattern = '(?m)^(\$ExcludeHardwareIds\s*=\s*@\()([^\r\n]*?)(\))'
$match = [regex]::Match($text, $pattern)
if (-not $match.Success) { throw 'Unexpected autoattach script format; USB settings unchanged.' }
$oldIds = $match.Groups[2].Value.Trim()
if ($oldIds -notmatch [regex]::Escape($CameraHardwareId)) {
    $newIds = if ($oldIds) { "$oldIds, '$CameraHardwareId'" } else { "'$CameraHardwareId'" }
    $replacement = $match.Groups[1].Value + $newIds + $match.Groups[3].Value
    $text = $text.Substring(0,$match.Index) + $replacement + $text.Substring($match.Index+$match.Length)
}

Stop-ScheduledTask -TaskName usbipd-autoattach
try {
    [IO.File]::WriteAllText($autoPath,$text,[Text.UTF8Encoding]::new($true))
    $stateJson = (& $usbipd state | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'usbipd state failed.' }
    $state = $stateJson | ConvertFrom-Json
    $vid,$pidPart = $CameraHardwareId.Split(':')
    foreach ($device in $state.Devices) {
        if ($device.BusId -and $device.ClientIPAddress -and
            $device.InstanceId -match "VID_$vid&PID_$pidPart") {
            & $usbipd detach --busid $device.BusId
            if ($LASTEXITCODE -ne 0) { throw "Camera detach failed: $($device.BusId)" }
        }
    }
} finally { Start-ScheduledTask -TaskName usbipd-autoattach }

$action = New-ScheduledTaskAction -Execute (Join-Path $venv 'Scripts\pythonw.exe') `
    -Argument ('"' + (Join-Path $destination 'server.py') + '"') -WorkingDirectory $destination
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$principal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1)
if (Get-ScheduledTask -TaskName physical-ai-camera-bridge -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName physical-ai-camera-bridge
}
Register-ScheduledTask -TaskName physical-ai-camera-bridge -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName physical-ai-camera-bridge
$ready = $false
for ($attempt=0; $attempt -lt 15; $attempt++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod http://127.0.0.1:8765/health -TimeoutSec 2
        if ($health.ok) { $ready=$true; break }
    } catch { }
}
if (-not $ready) { throw "Bridge installed but camera not ready. See $destination\bridge.log; check camera and port 8765." }
Write-Host 'Camera bridge is ready. Add an IP camera in Studio:'
Write-Host 'http://host.docker.internal:8765/camera.mjpg  (640 x 480, 30 FPS)'
Write-Host "Installed at: $destination"
