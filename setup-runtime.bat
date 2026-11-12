@echo off
setlocal
cd /d "%~dp0"
rem Kompatibilitas dengan workflow lama. Semua dependensi hanya dipasang di komputer BUILDER.
powershell -NoProfile -ExecutionPolicy Bypass -File "build\prepare-windows-runtime.ps1" %*
exit /b %errorlevel%
