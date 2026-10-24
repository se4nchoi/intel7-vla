param(
    [Parameter(Mandatory=$true)][ValidateSet('Studio','LeRobot')][string]$Mode,
    [switch]$Headless
)
$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$wslRoot = '/mnt/' + $root.Substring(0,1).ToLower() + $root.Substring(2).Replace('\','/')
$runtimeRoot = Join-Path $root 'runtime'
New-Item -ItemType Directory -Force $runtimeRoot | Out-Null
$docker = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$wsl = "$env:WINDIR/System32/wsl.exe"
$usbipd = 'C:/Program Files/usbipd-win/usbipd.exe'
$pythonw = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/pythonw.exe"
$container = 'physical-ai-studio-cuda'
$logPath = Join-Path $runtimeRoot 'launcher.log'
$lock = $null

function Note([string]$message) {
    $line = '{0:yyyy-MM-dd HH:mm:ss} [{1}] {2}' -f (Get-Date), $Mode, $message
    Write-Host $message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}
function Wait-Ready([scriptblock]$Test, [string]$Name, [int]$Seconds=40) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (& $Test) { return }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Name. See runtime/launcher.log."
}
function Wsl-Run([string[]]$Arguments) {
    $result = & $wsl -d Ubuntu-24.04 -- @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $details = ($result | Out-String).Trim()
        if (-not $details) { $details = 'WSL returned no diagnostic output. Ubuntu may be unable to start new processes. After checking that no training/recording is running, restart Ubuntu with: wsl --terminate Ubuntu-24.04, then retry this launcher.' }
        throw "WSL failed (exit $exitCode; command: $($Arguments[0])): $details"
    }
    return $result
}
function Get-BridgeProcesses([string]$Script) {
    $target = (Join-Path $root $Script).Replace('\','/')
    @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains($target)
    })
}
function Docker-Running {
    $ErrorActionPreference = 'Continue'
    $result = & $docker inspect --format '{{.State.Running}}' $container 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Existing container '$container' not found. Install/restore Studio first; no new container was created." }
    return "$result".Trim() -eq 'true'
}
function Docker-Available {
    $ErrorActionPreference = 'Continue'
    & $docker info --format '{{.ServerVersion}}' *> $null
    return $LASTEXITCODE -eq 0
}
function Ensure-Docker {
    if (Docker-Available) { return }
    Note 'Starting Docker Desktop...'
    Start-Process -FilePath 'C:/Program Files/Docker/Docker/Docker Desktop.exe' -WindowStyle Hidden
    Wait-Ready { Docker-Available } 'Docker Desktop' 120
}
function Check-WslWork {
    $linuxPath = "$wslRoot/tools/diagnostics/check-processes.py"
    $result = Wsl-Run @('python3', $linuxPath)
    if ($result) { throw "Active LeRobot hardware/training process found. Stop it in its terminal before switching mode:`n$($result | Out-String)" }
}
function Stop-Relay {
    foreach ($process in @(Get-BridgeProcesses 'windows/relay.py')) {
        Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
    }
}
function Recorder-Status {
    $statusFile = Join-Path $runtimeRoot 'native-status.json'
    if (Test-Path $statusFile) {
        try {
            $native = Get-Content -Raw $statusFile | ConvertFrom-Json
            $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $native.updated_at
            if ($age -lt 8 -and $native.state -ne 'disconnected') { return $native }
        } catch {}
    }
    return $null
}
function Ensure-Usb {
    Note 'Preparing WSL and robot USB connections...'
    Wsl-Run @('true') | Out-Null
    try {
        $task = Get-ScheduledTask -TaskName usbipd-autoattach -ErrorAction Stop
        $autoPath = 'C:/ProgramData/usbipd-autoattach/usbipd-autoattach.ps1'
        if ((Test-Path $autoPath) -and -not ([IO.File]::ReadAllText($autoPath).Contains("'32e6:9211'"))) {
            throw 'Camera exclusion 32e6:9211 is missing from the USB autoattach configuration. See README.'
        }
        if ($task.State -ne 'Running') { Start-ScheduledTask -TaskName usbipd-autoattach }
    } catch {
        if ($_.Exception.Message -like '*Camera exclusion*') { throw }
        Note 'USB autoattach task unavailable; attempting direct attach for the existing shared devices.'
    }
    $state = (& $usbipd state | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'usbipd state failed.' }
    foreach ($serial in @('5B90149145','5B90150163')) {
        $device = @($state.Devices | Where-Object { $_.InstanceId.EndsWith('\' + $serial) -and $_.BusId })
        if ($device.Count -ne 1) { throw "Robot USB board $serial is not plugged in. Connect both robot USB cables and retry." }
        if (-not $device[0].PersistedGuid) { throw "USB board $serial is not shared. In Administrator PowerShell run: usbipd bind --busid $($device[0].BusId), then retry." }
        if (-not $device[0].ClientIPAddress) {
            & $usbipd attach --wsl Ubuntu-24.04 --busid $device[0].BusId
            if ($LASTEXITCODE -ne 0) { Note "USB board $serial is re-enumerating or autoattach is already in progress; waiting for its serial port..." }
        }
    }
    $camera = @($state.Devices | Where-Object { $_.InstanceId -like 'USB\VID_32E6&PID_9211\*' -and $_.BusId })
    foreach ($device in $camera) {
        if ($device.ClientIPAddress) {
            & $usbipd detach --busid $device.BusId
            if ($LASTEXITCODE -ne 0) { throw 'Could not return the webcam to Windows.' }
        }
    }
    Wait-Ready {
        & $wsl -d Ubuntu-24.04 -- test -e /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90149145-if00
        if ($LASTEXITCODE -ne 0) { return $false }
        & $wsl -d Ubuntu-24.04 -- test -e /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90150163-if00
        return $LASTEXITCODE -eq 0
    } 'both robot serial ports' 20
}
function Camera-Healthy {
    try { return (Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2).ok -eq $true } catch { return $false }
}
function Ensure-Camera {
    Note 'Preparing Windows camera bridge...'
    if (Camera-Healthy) { return }
    $listener = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
        try { Start-ScheduledTask -TaskName physical-ai-camera-bridge -ErrorAction Stop }
        catch {
            Start-Process -FilePath $pythonw -WindowStyle Hidden -ArgumentList ('"' + (Join-Path $PSScriptRoot 'camera_server.py') + '"')
        }
    }
    Wait-Ready { Camera-Healthy } 'fresh webcam frames (close other camera applications if needed)' 30
}

try {
    # Prevent simultaneous Studio/LeRobot launches, but release the lock after preparation.
    $lock = [IO.File]::Open((Join-Path $runtimeRoot 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    Note "Preparing $Mode mode..."
    foreach ($path in @($wsl,$usbipd,$pythonw)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Missing prerequisite: $path. See docs/OPERATIONS.ko.md." }
    }
    $dashboard = Recorder-Status
    if ($dashboard) {
        if ($dashboard.state -in @('recording','saving')) {
            throw 'LeRobot is recording or saving. Stop and save in its screen before switching to Studio.'
        }
        Note 'Releasing LeRobot robot connections...'
        Set-Content (Join-Path $runtimeRoot 'native-stop.request') 'stop' -Encoding ASCII
        Wait-Ready { -not (Recorder-Status) } 'LeRobot device disconnect' 60
        if ($Mode -eq 'LeRobot' -and $dashboard.error -match 'no status packet|Missing motor IDs|motor check failed') {
            Note 'Recovering stale robot USB connections after releasing all ports...'
            $usbState = (& $usbipd state | Out-String) | ConvertFrom-Json
            foreach ($device in $usbState.Devices) {
                if ($device.ClientIPAddress -and $device.InstanceId -match '\\(5B90149145|5B90150163)$') {
                    & $usbipd detach --busid $device.BusId
                    if ($LASTEXITCODE -ne 0) { throw 'Robot USB reset failed.' }
                }
            }
            Wait-Ready {
                $devices = ((& $usbipd state | Out-String) | ConvertFrom-Json).Devices
                return @($devices | Where-Object { $_.BusId -and $_.InstanceId -match '\\(5B90149145|5B90150163)$' }).Count -eq 2
            } 'robot USB re-enumeration' 20
        }
    }
    Check-WslWork
    if ($Mode -eq 'LeRobot') {
        # Do not start Docker just to stop it. Running container processes have this exact name.
        if (Test-Path -LiteralPath $docker) {
            if ((Docker-Available) -and (Docker-Running)) {
                Note 'Checking Studio jobs before releasing its robot ports...'
                try { $jobs = Invoke-RestMethod 'http://127.0.0.1:7860/api/jobs' -TimeoutSec 8 }
                catch { throw 'Studio is running but its jobs API is unavailable. Stop it manually after checking training/recording, then retry.' }
                $items = if ($jobs.PSObject.Properties.Name -contains 'jobs') { @($jobs.jobs) } elseif ($jobs.PSObject.Properties.Name -contains 'items') { @($jobs.items) } else { @($jobs) }
                $active = @($items | Where-Object { $_ -and "$($_.status)" -notmatch '^(completed|failed|cancelled|canceled|done|finished|success|succeeded)$' })
                if ($active.Count) { throw 'Studio has active jobs. Finish or stop them in Studio before switching mode; no jobs were terminated.' }
                try {
                    $sessionResponse = Invoke-RestMethod 'http://127.0.0.1:7860/api/runtime/sessions' -TimeoutSec 8
                    $sessions = @($sessionResponse)
                }
                catch { throw 'Cannot check Studio recording/robot sessions. Check and stop Studio manually before switching mode.' }
                $busy = @($sessions | Where-Object {
                    $_ -and ($_.activity.is_recording -eq $true -or $_.activity.follower_source -in @('teleop','policy') -or $_.status -in @('starting','unreachable'))
                })
                if ($busy.Count) { throw 'Studio is recording, controlling a robot, or has an unknown session state. Turn off Recording/Teleoperate/Inference before switching mode.' }
                foreach ($session in $sessions) {
                    if ($session -and $session.session_name) {
                        $name = [Uri]::EscapeDataString($session.session_name)
                        Invoke-RestMethod -Method Post "http://127.0.0.1:7860/api/runtime/sessions/$name/stop" -TimeoutSec 20 | Out-Null
                    }
                }
                Note 'Stopping idle Studio container to release robot ports...'
                & $docker stop --timeout 20 $container
                if ($LASTEXITCODE -ne 0) { throw 'Could not stop Studio container.' }
            }
        }
    }
    Ensure-Usb
    Ensure-Camera
    if ($Mode -eq 'LeRobot') { & (Join-Path $PSScriptRoot 'start-field-camera.ps1') }
    if ($Mode -eq 'Studio') {
        if (-not (Test-Path -LiteralPath $docker)) { throw 'Docker Desktop is not installed. See README.' }
        Ensure-Docker
        Stop-Relay
        if (-not (Docker-Running)) {
            Note 'Starting the existing patched Studio container...'
            & $docker start $container
            if ($LASTEXITCODE -ne 0) { throw 'Studio container start failed.' }
        }
        Wait-Ready { try { Invoke-WebRequest 'http://127.0.0.1:7860/' -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { return $false } } 'Studio HTTP service' 120
        Note 'READY: Studio http://localhost:7860 (ZMQ relay is not needed in this mode).'
        if (-not $Headless) { Start-Process 'http://localhost:7860' }
    } else {
        Note 'Preparing LeRobot ZMQ camera relay...'
        # Restart only our relay, so changes to WSL adapter addresses are handled automatically.
        Stop-Relay
        & (Join-Path $PSScriptRoot 'start-camera-relay.ps1')
        $gateway = (Wsl-Run @('python3',"$wslRoot/src/intel7_vla/common/camera_address.py") | Out-String).Trim()
        Wait-Ready { @(Get-NetTCPConnection -LocalAddress $gateway -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue).Count -gt 0 } 'ZMQ relay' 15
        Wait-Ready { @(Get-NetTCPConnection -LocalAddress $gateway -LocalPort 5556 -State Listen -ErrorAction SilentlyContinue).Count -gt 0 } 'field camera ZMQ relay' 15
        Wsl-Run @('bash',"$wslRoot/wsl/prepare-wsl.sh") | ForEach-Object { Note "$_" }
        if ($Headless) {
            Note 'READY: Prerequisites verified. Headless mode does not start recording or connect motors.'
        } else {
            Note 'Checking actual replies from all 12 motors (no movement)...'
            Wsl-Run @('bash','-lc',"cd ~/lerobot && .venv/bin/python '$wslRoot/tools/diagnostics/check_motors.py'") | ForEach-Object { Note "$_" }
            & (Join-Path $PSScriptRoot 'open-dataset-ui.ps1')
            Note 'Dataset Desk opened. Connect robots and explicitly press Record in the web screen; startup does not record or follow.'
        }
    }
    @{mode=$Mode;ready=$true;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $runtimeRoot 'last-run.json') -Encoding UTF8
} catch {
    Note "FAILED: $($_.Exception.Message)"
    Write-Host 'Check docs/OPERATIONS.ko.md and runtime/launcher.log.' -ForegroundColor Yellow
    exit 1
} finally {
    if ($lock) { $lock.Dispose() }
}
