<#
  install-usbipd-autoattach.ps1  —  USB 자동 연결(WSL) 설치 / 제거  (관리자 PowerShell 에서 한 번)

  사용법 (로봇 팔 2개와 카메라를 먼저 꽂아 둔 상태에서):
      cd C:\Users\<사용자>\Documents\VLA수업\windows_setup
      powershell -ExecutionPolicy Bypass -File .\install-usbipd-autoattach.ps1
  카메라를 나중에 새 모델로 바꿨다면 꽂은 뒤 다시 한 번 실행하면 된다.
  특정 장치를 추가로 등록:   ... -File .\install-usbipd-autoattach.ps1 -ExtraHardwareIds 046d:0825
  제거:                     ... -File .\install-usbipd-autoattach.ps1 -Uninstall

  하는 일
    1) usbipd-autoattach.ps1 을 C:\ProgramData\usbipd-autoattach\ 로 복사
    2) SO-101 모터보드 + 지금 꽂혀 있는 USB 카메라의 VID:PID 를 AutoBind 정책으로 등록 (영구)
    3) 작업 스케줄러 'usbipd-autoattach' 등록 — 로그온할 때마다 사용자 권한으로 숨김 실행
    4) 지금 바로 실행
#>
param([switch]$Uninstall, [string[]]$ExtraHardwareIds = @(), [string]$Distro = 'Ubuntu-24.04')

$ErrorActionPreference = 'Stop'
$TaskName = 'usbipd-autoattach'
$Dest     = Join-Path $env:ProgramData 'usbipd-autoattach'
$Script   = Join-Path $Dest 'usbipd-autoattach.ps1'
$So101Ids = @('1a86:55d3', '1a86:7523', '1a86:55d4')

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw '관리자 권한 PowerShell 에서 실행하세요 (시작 → PowerShell 우클릭 → 관리자로 실행).' }
if (-not (Get-Command usbipd -ErrorAction SilentlyContinue)) {
    throw 'usbipd 가 없습니다. 먼저: winget install --id dorssel.usbipd-win -e  (설치 후 PowerShell 을 새로 여세요)'
}

if ($Uninstall) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like '*usbipd-autoattach.ps1*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "작업 '$TaskName' 제거 완료."
    Write-Host '정책까지 지우려면: usbipd policy list 로 GUID 확인 후  usbipd policy remove --guid <GUID>'
    return
}

# 1) 스크립트 복사 (UTF-8 BOM — Windows PowerShell 5.1 이 한글 주석을 깨뜨리지 않게)
New-Item -ItemType Directory -Force $Dest | Out-Null
$text = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'usbipd-autoattach.ps1'), [Text.Encoding]::UTF8)
$text = $text -replace "(?m)^\`$Distro\s*=\s*'[^']*'", "`$Distro             = '$Distro'"
[IO.File]::WriteAllText($Script, $text, (New-Object Text.UTF8Encoding($true)))
Write-Host "[1/4] 스크립트 복사: $Script"

# 2) AutoBind 정책 — SO-101 + 지금 연결된 USB 카메라 + 추가 지정
$cams = Get-PnpDevice -PresentOnly -Class Camera, Image -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -like 'USB\*' }
$camIds = foreach ($c in $cams) {
    if ($c.InstanceId -match 'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})') {
        $id = ('{0}:{1}' -f $Matches[1], $Matches[2]).ToLower()
        Write-Host "      카메라 발견: $($c.FriendlyName)  ($id)"
        $id
    }
}
$ids = @($So101Ids + $camIds + $ExtraHardwareIds) | ForEach-Object { $_.ToLower() } | Sort-Object -Unique
$existing = (usbipd policy list | Out-String).ToLower()
foreach ($id in $ids) {
    if ($existing -notmatch [regex]::Escape($id)) {
        usbipd policy add --effect Allow --operation AutoBind --hardware-id $id | Out-Null
    }
}
Write-Host "[2/4] AutoBind 정책: $($ids -join ', ')"

# 3) 작업 스케줄러 등록 (사용자 권한 — WSL 은 사용자별로 동작하므로 관리자 권한으로 띄우지 않는다)
$user      = "$env:USERDOMAIN\$env:USERNAME"
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
             -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`""
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
             -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
             -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal `
    -Settings $settings -Description 'SO-ARM101 / USB 카메라를 WSL2 로 자동 attach (usbipd)' -Force | Out-Null
Write-Host "[3/4] 작업 스케줄러 등록: $TaskName (로그온 시 자동 실행, $user)"

# 4) 지금 실행
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 6
Write-Host "[4/4] 실행 상태: $((Get-ScheduledTask -TaskName $TaskName).State)"
Write-Host ''
Write-Host '확인:  usbipd list   →  로봇/카메라 STATE 가 Attached 이면 성공'
Write-Host "로그:  $env:LOCALAPPDATA\usbipd-autoattach\autoattach.log"
