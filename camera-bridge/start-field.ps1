$ErrorActionPreference = 'Stop'
try {
    if ((Invoke-RestMethod 'http://127.0.0.1:8766/health' -TimeoutSec 2).ok) { return }
} catch {}
$pythonw = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$listener = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    $arguments = '"{0}" --camera-name "USB HD" --name field_cam --port 8766' -f (Join-Path $PSScriptRoot 'server.py')
    Start-Process -FilePath $pythonw -WindowStyle Hidden -ArgumentList $arguments -RedirectStandardError (Join-Path $PSScriptRoot 'field-stderr.log') -RedirectStandardOutput (Join-Path $PSScriptRoot 'field-stdout.log')
}
$deadline=(Get-Date).AddSeconds(25)
do {
    Start-Sleep -Milliseconds 500
    try { if ((Invoke-RestMethod 'http://127.0.0.1:8766/health' -TimeoutSec 2).ok) { return } } catch {}
} while ((Get-Date) -lt $deadline)
throw 'Field camera USB HD not ready. Check camera-bridge/field-bridge.log.'
