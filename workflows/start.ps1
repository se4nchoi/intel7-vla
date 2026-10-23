# Compatibility entry point. Windows implementation lives in scripts/windows.
param(
    [Parameter(Mandatory=$true)][ValidateSet('Studio','LeRobot')][string]$Mode,
    [switch]$Headless
)
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/windows/start.ps1') @PSBoundParameters
