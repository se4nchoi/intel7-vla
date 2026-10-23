@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0workflows\open-dataset-ui.ps1"
if errorlevel 1 pause
