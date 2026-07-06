@echo off
taskkill /F /IM glazewm.exe
ping 127.0.0.1 -n 2 >nul
start "" "glazewm.exe"
exit