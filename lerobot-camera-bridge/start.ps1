# Compatibility Windows entry point.
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/windows/start-camera-relay.ps1') @args
