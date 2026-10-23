# Compatibility Windows entry point.
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/windows/install-camera-bridge.ps1') @args
