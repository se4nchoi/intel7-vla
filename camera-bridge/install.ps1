$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$statusPath = Join-Path $root 'install-status.json'
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator rights are required to update the existing USB autoattach task.'
    }
    $autoPath = 'C:\ProgramData\usbipd-autoattach\usbipd-autoattach.ps1'
    $text = [IO.File]::ReadAllText($autoPath)
    if ($text.Contains('$ExcludeHardwareIds = @()')) {
        $text = $text.Replace('$ExcludeHardwareIds = @()', '$ExcludeHardwareIds = @(''32e6:9211'')')
    } elseif (-not $text.Contains("'32e6:9211'")) {
        throw 'Unexpected exclusion settings; no changes applied.'
    }
    Stop-ScheduledTask -TaskName usbipd-autoattach
    [IO.File]::WriteAllText($autoPath, $text, [Text.UTF8Encoding]::new($true))
    Start-ScheduledTask -TaskName usbipd-autoattach

    $python = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe'
    $server = Join-Path $root 'server.py'
    $action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $server + '"') -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 99 `
        -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName physical-ai-camera-bridge -Action $action -Trigger $trigger `
        -Principal $taskPrincipal -Settings $settings -Force | Out-Null
    $pidPath = Join-Path $root 'process-id.txt'
    if (Test-Path $pidPath) {
        $bridgeId = [int](Get-Content $pidPath)
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$bridgeId"
        if ($process -and $process.CommandLine.Contains('camera-bridge/server.py')) {
            Stop-Process -Id $bridgeId -ErrorAction SilentlyContinue
        }
    }
    Start-ScheduledTask -TaskName physical-ai-camera-bridge
    @{ok=$true; time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content $statusPath -Encoding UTF8
} catch {
    @{ok=$false; error=$_.Exception.Message} | ConvertTo-Json | Set-Content $statusPath -Encoding UTF8
    exit 1
}
