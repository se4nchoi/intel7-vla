<#
  usbipd-autoattach.ps1  —  SO-ARM101 모터보드 + USB 카메라를 WSL2 로 "항상" 자동 연결

  동작 (2초마다 반복, 로그온한 사용자 권한으로 실행)
    1) Ubuntu(WSL)가 꺼져 있으면 깨워서 계속 켜 둔다 (keep-alive)
    2) 대상 장치 = AutoBind 정책에 등록된 VID:PID + 아래 $HardwareIds
    3) 대상 장치 중 지금 꽂혀 있는데 WSL 에 안 붙은 것을 attach
  → 케이블을 뺐다 꽂아도, 다른 포트에 꽂아도, 재부팅해도 자동으로 WSL 에 붙는다.

  설치/제거: install-usbipd-autoattach.ps1 (관리자 PowerShell, 한 번만)
  로그:      %LOCALAPPDATA%\usbipd-autoattach\autoattach.log
#>

# ----------------------------------------------------------------- 설정
$Distro             = 'Ubuntu-24.04'                # 장치를 붙일 WSL 배포판 (docker-desktop 아님)
$HardwareIds        = @('1a86:55d3', '1a86:7523',   # SO-101 모터보드 (CH343 / CH340)
                        '1a86:55d4')                 # CH9102 변형 보드
$ExcludeHardwareIds = @()                            # 절대 WSL 로 보내지 않을 장치 (예: '0c45:6366')
$IntervalSec        = 2
$LogDir             = Join-Path $env:LOCALAPPDATA 'usbipd-autoattach'
$LogFile            = Join-Path $LogDir 'autoattach.log'
# ----------------------------------------------------------------------

New-Item -ItemType Directory -Force $LogDir | Out-Null
function Log($msg) {
    $line = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $msg
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    if ((Get-Item $LogFile).Length -gt 1MB) { Move-Item $LogFile "$LogFile.old" -Force }
}

function Get-VidPid([string]$instanceId) {
    if ($instanceId -match 'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})') { return ('{0}:{1}' -f $Matches[1], $Matches[2]).ToLower() }
    return $null
}

function Get-PolicyHardwareIds {
    # 'usbipd policy list' 는 관리자 권한 없이 읽을 수 있다. Allow + AutoBind 규칙의 VID:PID 만 모은다.
    (usbipd policy list | Out-String) -split "`r?`n" |
        Where-Object { $_ -match '\bAllow\b' -and $_ -match 'AutoBind' -and $_ -match '\b([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\b' } |
        ForEach-Object { $Matches[1].ToLower() }
}

$keepAlive = $null
function Ensure-WslRunning {
    if ($script:keepAlive -and -not $script:keepAlive.HasExited) { return }
    # WSL VM 이 꺼지면 붙어 있던 USB 가 모두 떨어지므로, 잠들지 않게 sleep 프로세스를 하나 띄워 둔다
    $script:keepAlive = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d', $Distro, '--exec', 'sleep', 'infinity') `
        -WindowStyle Hidden -PassThru
    Log "WSL keep-alive started (pid $($script:keepAlive.Id))"
    Start-Sleep -Seconds 3
}

Log "=== usbipd-autoattach started (user $env:USERNAME, distro $Distro) ==="
$lastMsg = @{}
while ($true) {
    try {
        Ensure-WslRunning
        $targets = @($HardwareIds + @(Get-PolicyHardwareIds)) | ForEach-Object { $_.ToLower() } |
                   Where-Object { $ExcludeHardwareIds -notcontains $_ } | Sort-Object -Unique
        $state = (usbipd state | Out-String) | ConvertFrom-Json
        foreach ($d in $state.Devices) {
            if (-not $d.BusId) { continue }                 # 지금 꽂혀 있지 않음
            if ($d.ClientIPAddress) { continue }            # 이미 WSL 에 붙어 있음
            $vp = Get-VidPid $d.InstanceId
            if ($targets -notcontains $vp) { continue }
            $out = (usbipd attach --wsl $Distro --busid $d.BusId 2>&1 | Out-String).Trim()
            $msg = if ($LASTEXITCODE -eq 0) { 'OK' } else { "FAILED: $out" }
            if ($lastMsg[$d.BusId] -ne $msg -or $msg -eq 'OK') { Log "attach $($d.BusId) $vp $($d.Description) -> $msg" }
            $lastMsg[$d.BusId] = $msg
        }
    } catch {
        Log "error: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $IntervalSec
}
