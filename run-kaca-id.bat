@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo KACA.ID - Menjalankan aplikasi
echo ================================================
where node >nul 2>nul
if errorlevel 1 goto node_missing
where npm.cmd >nul 2>nul
if errorlevel 1 goto npm_missing
if not exist "runtime\python\python.exe" if not exist ".venv\Scripts\python.exe" (
  echo [PERINGATAN] Runtime Python portable belum ditemukan.
  echo Jalankan setup.bat pada komputer developer untuk menyiapkannya.
  pause
  exit /b 1
)
if not exist "node_modules\electron\dist\electron.exe" (
  echo Dependensi Electron belum tersedia. Memasang sekarang...
  call npm.cmd install
  if errorlevel 1 goto npm_failed
)
echo Membuka KACA.ID...
call npm.cmd start
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
  echo.
  echo KACA.ID berhenti dengan kode %APP_EXIT%.
  echo Jalankan run-kaca-id-debug.bat dan kirim file logs\startup.log.
  pause
)
exit /b %APP_EXIT%

:node_missing
echo Node.js tidak ditemukan. Instal Node.js LTS lalu buka terminal baru.
pause
exit /b 1
:npm_missing
echo npm.cmd tidak ditemukan. Periksa instalasi Node.js.
pause
exit /b 1
:npm_failed
echo Instalasi Electron gagal. Periksa koneksi internet dan pesan npm di atas.
pause
exit /b 1
