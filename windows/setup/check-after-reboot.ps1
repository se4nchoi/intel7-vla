<#
  check-after-reboot.ps1 — 재부팅(로그온) 후 실습 환경이 자동으로 살아났는지 한 번에 확인
  실행 (일반 PowerShell):  powershell -ExecutionPolicy Bypass -File .\check-after-reboot.ps1
#>
$env:WSL_UTF8 = 1
function Head($t) { Write-Host ''; Write-Host "=== $t ===" -ForegroundColor Cyan }

Head 'WSL 배포판 (Ubuntu-24.04 앞에 * , Running)'
wsl -l -v

Head 'USB 자동 연결 작업'
$t = Get-ScheduledTask -TaskName 'usbipd-autoattach' -ErrorAction SilentlyContinue
if ($t) { "작업 상태: $($t.State)" } else { '작업 없음 → install-usbipd-autoattach.ps1 실행 필요' }
Get-Content "$env:LOCALAPPDATA\usbipd-autoattach\autoattach.log" -Tail 5 -ErrorAction SilentlyContinue

Head 'usbipd list (로봇·카메라 = Attached)'
usbipd list

Head 'Ubuntu 안 장치 · 메모리'
wsl -d Ubuntu-24.04 -- bash -c 'ls -l /dev/ttyACM* /dev/ttyUSB* /dev/video* 2>/dev/null; free -h | head -2'

Head 'Docker · Studio 컨테이너 (Up (healthy))'
wsl -d Ubuntu-24.04 -- docker ps --format '{{.Names}}={{.Status}}'
try { (Invoke-WebRequest -UseBasicParsing http://localhost:7860/api/health -TimeoutSec 5).Content } catch { 'Studio 응답 없음 — Docker Desktop 실행 확인 후: cd ~/physical-ai-studio/application/docker && docker compose up -d' }
