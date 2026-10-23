# Compatibility Windows entry point.
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/windows/open-dataset-ui.ps1') @args
