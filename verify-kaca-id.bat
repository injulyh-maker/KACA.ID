@echo off
setlocal
cd /d "%~dp0"
echo Checking JavaScript syntax...
node --check main.js || goto failed
node --check preload.js || goto failed
node --check src\app.js || goto failed
echo Checking Python syntax...
if exist .venv\Scripts\python.exe (set "PY=.venv\Scripts\python.exe") else (set "PY=python")
%PY% -m py_compile backend\camera_server.py backend\google_drive.py backend\whatsapp_cloud.py backend\canon_edsdk_live.py backend\canon_edsdk_worker.py backend\canon_edsdk_native.py || goto failed
echo Running low-memory preview regression test...
%PY% tests\low_memory_preview_test.py || goto failed
echo Running MultiCam and Live Photo regression test...
%PY% tests\multicam_preview_regression_test.py || goto failed
echo Running backend smoke test...
%PY% tests\google_drive_test.py || goto failed
%PY% tests\session_qr_test.py || goto failed
%PY% tests\app_logs_test.py || goto failed
%PY% tests\ui_layout_test.py || goto failed
%PY% tests\whatsapp_cloud_test.py || goto failed
%PY% tests\smoke_test.py || goto failed
%PY% tests\v0926_video_test.py || goto failed
echo All available automated checks passed.
pause
exit /b 0
:failed
echo Verification failed. Review the error above.
pause
exit /b 1
