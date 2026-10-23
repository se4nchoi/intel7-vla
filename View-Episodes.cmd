@echo off
chcp 65001 >nul
wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/Users/user/rjsxo/workflows/view-episodes.sh %*
if errorlevel 1 pause
