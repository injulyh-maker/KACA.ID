@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo KACA.ID startup diagnostics > logs\startup.log
echo Date: %DATE% %TIME%>> logs\startup.log
where node >> logs\startup.log 2>&1
node --version >> logs\startup.log 2>&1
where npm.cmd >> logs\startup.log 2>&1
npm.cmd --version >> logs\startup.log 2>&1
if not exist "node_modules\electron\dist\electron.exe" (
  echo Installing Electron...>> logs\startup.log
  call npm.cmd install >> logs\startup.log 2>&1
  if errorlevel 1 goto failed
)
echo Launching Electron...>> logs\startup.log
call npm.cmd start >> logs\startup.log 2>&1
set "APP_EXIT=%ERRORLEVEL%"
echo Exit code: %APP_EXIT%>> logs\startup.log
notepad logs\startup.log
pause
exit /b %APP_EXIT%
:failed
echo npm install failed.>> logs\startup.log
notepad logs\startup.log
pause
exit /b 1
