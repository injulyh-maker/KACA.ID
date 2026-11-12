@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===============================================================
echo KACA.ID v0.9.90 - BUILD WINDOWS SETUP (FULLY OFFLINE RUNTIME)
echo ===============================================================
if not exist "build\prepare-windows-runtime.ps1" (
  echo [ERROR] Build script tidak tersedia.
  goto failed
)
where node.exe >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js v22 atau kompatibel diperlukan pada komputer BUILDER.
  goto failed
)
echo [KACA BUILD] Uji lisensi dan validasi antarmuka sebelum mengunduh runtime...
call node.exe tests\publish_license_offline_test.js
if errorlevel 1 goto failed
call node.exe tests\final_release_regression_test.js
if errorlevel 1 goto failed
powershell -NoProfile -ExecutionPolicy Bypass -File "build\prepare-windows-runtime.ps1"
if errorlevel 1 goto failed
runtime\python\python.exe -I build\check-publish-assets.py
if errorlevel 1 goto failed
runtime\python\python.exe -I build\test_packaging_configuration.py
if errorlevel 1 goto failed
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm diperlukan pada mesin BUILDER, bukan komputer pelanggan.
  goto failed
)
if exist "package-lock.json" (
  call npm.cmd ci --no-audit --no-fund
) else (
  call npm.cmd install --no-audit --no-fund
)
if errorlevel 1 goto failed
call npm.cmd run dist:win
if errorlevel 1 goto failed
powershell -NoProfile -ExecutionPolicy Bypass -File "build\verify-windows-installer.ps1"
if errorlevel 1 goto failed
if not exist "dist\KACA-ID-Setup-0.9.90-x64.exe" (
  echo [ERROR] Installer EXE tidak ditemukan di dist.
  goto failed
)
echo.
echo [OK] dist\KACA-ID-Setup-0.9.90-x64.exe
echo Runtime Python 3.12 dan VC++ tercakup dalam installer.
exit /b 0
:failed
echo.
echo [ERROR] Build dihentikan. Jangan distribusikan installer yang belum terverifikasi.
exit /b 1
