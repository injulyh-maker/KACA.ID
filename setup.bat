@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo KACA.ID - Setup Build dan Runtime Portable
echo ================================================
call setup-runtime.bat
if errorlevel 1 goto failed
where npm.cmd >nul 2>nul
if errorlevel 1 (echo Node.js LTS belum ditemukan. Instal Node.js hanya untuk proses build developer.& goto failed)
echo Memasang dependensi aplikasi Electron...
call npm.cmd install
if errorlevel 1 goto failed
call npm.cmd rebuild electron
if errorlevel 1 goto failed
echo.
echo Setup selesai. Runtime Python sudah disiapkan di folder runtime.
echo Jalankan run-kaca-id.bat untuk pengujian, atau npm.cmd run dist:win untuk membuat installer.
exit /b 0
:failed
echo Setup gagal. Periksa koneksi dan pesan error di atas.
pause
exit /b 1
