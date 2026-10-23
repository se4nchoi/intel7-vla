# Compatibility Windows entry point.
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/windows/start-field-camera.ps1') @args
