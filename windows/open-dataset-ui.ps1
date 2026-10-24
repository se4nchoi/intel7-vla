$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$wslRoot = '/mnt/' + $root.Substring(0,1).ToLower() + $root.Substring(2).Replace('\','/')
try {
    try { $ready = (Invoke-RestMethod 'http://127.0.0.1:8877/api/status' -TimeoutSec 2).state } catch { $ready = $null }
    if (-not $ready) {
        Start-Process -FilePath "$env:WINDIR/System32/wsl.exe" -WindowStyle Hidden -ArgumentList @('-d','Ubuntu-24.04','--','bash',"$wslRoot/wsl/start-dataset-ui.sh")
        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 500
            try { $ready = (Invoke-RestMethod 'http://127.0.0.1:8877/api/status' -TimeoutSec 2).state } catch {}
        } until ($ready -or (Get-Date) -gt $deadline)
        if (-not $ready) { throw 'Dataset UI did not start. Check runtime/dataset-ui.log.' }
    }
    Start-Process 'http://localhost:8877/'
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }
