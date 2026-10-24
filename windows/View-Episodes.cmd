@echo off
chcp 65001 >nul
wsl.exe -d Ubuntu-24.04 --cd "%~dp0.." -- bash wsl/view-episodes.sh %*
if errorlevel 1 pause
