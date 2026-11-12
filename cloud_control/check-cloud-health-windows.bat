@echo off
setlocal
powershell.exe -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8086/api/health' -TimeoutSec 5; Write-Host ('Cloud Control: ' + $r.service + ' | Database: ' + $r.database + ' | OK: ' + $r.ok); exit 0 } catch { Write-Host 'Cloud Control belum berjalan atau port 8086 tidak bisa diakses.'; exit 1 }"
if errorlevel 1 pause
endlocal
