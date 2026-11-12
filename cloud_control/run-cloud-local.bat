@echo off
setlocal
cd /d "%~dp0.."
if not exist cloud-env\Scripts\python.exe (
 echo [KACA CLOUD] Buat dulu environment: py -m venv cloud-env
 pause
 exit /b 1
)
cloud-env\Scripts\python.exe -m uvicorn cloud_control.server:app --host 127.0.0.1 --port 8086
