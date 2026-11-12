$ErrorActionPreference = "Stop"
$Backend = Join-Path (Get-Location).Path "backend"
if (-not (Test-Path $Backend)) {
    $candidate = "D:\dokumen\aplikasi kaca fotoboth\V2\KACA-ID-Foundation-v4-Python-OpenCV-Camera\KACA-ID-Foundation-v5-Continuous-Frame-Diagnostics\KACA-ID-v0.9.18\backend"
    if (Test-Path $candidate) { $Backend = $candidate }
}
if (-not (Test-Path $Backend)) { throw "Folder backend tidak ditemukan. Jalankan dari folder proyek KACA.ID." }

$Source = Join-Path $PSScriptRoot "patch"
$Targets = @("canon_edsdk_live.py","canon_edsdk_worker.py")
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($name in $Targets) {
    $dest = Join-Path $Backend $name
    if (Test-Path $dest) {
        Copy-Item $dest "$dest.before_v2_$Stamp.bak" -Force
    }
    Copy-Item (Join-Path $Source $name) $dest -Force
}
try {
    Push-Location $Backend
    & python -m py_compile .\canon_edsdk_live.py .\canon_edsdk_worker.py .\canon_edsdk_native.py
    if ($LASTEXITCODE -ne 0) { throw "Pemeriksaan sintaks Python gagal." }
    Write-Host "`nPatch Canon EDSDK v2 terpasang dan lolos py_compile." -ForegroundColor Green
    Write-Host "camera_server.py, canon_edsdk_runtime.py, dan jalur webcam tidak diubah."
} catch {
    foreach ($name in $Targets) {
        $dest = Join-Path $Backend $name
        $backup = Get-ChildItem $Backend -Filter "$name.before_v2_$Stamp.bak" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($backup) { Copy-Item $backup.FullName $dest -Force }
    }
    throw
} finally {
    Pop-Location
}
