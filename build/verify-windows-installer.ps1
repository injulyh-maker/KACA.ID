[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$installer = Join-Path $root 'dist\KACA-ID-Setup-0.9.90-x64.exe'
$unpacked = Join-Path $root 'dist\win-unpacked'
$python = Join-Path $unpacked 'resources\python\python.exe'
$vc = Join-Path $unpacked 'resources\vc_redist.x64.exe'
$manifest = Join-Path $unpacked 'resources\runtime-build-complete.json'
$cameraServer = Join-Path $unpacked 'resources\app\backend\camera_server.py'
foreach ($file in @($installer, $python, $vc, $manifest, $cameraServer)) {
    if (!(Test-Path $file)) { throw "Windows release tidak lengkap: $file" }
}
$vcSignature=Get-AuthenticodeSignature -FilePath $vc
if ($vcSignature.Status -ne 'Valid' -or $vcSignature.SignerCertificate.Subject -notmatch 'Microsoft') {
    throw 'Visual C++ Redistributable tidak ditandatangani Microsoft.'
}
$runtimeManifest = Get-Content $manifest -Raw | ConvertFrom-Json
if (!$runtimeManifest.verified -or !$runtimeManifest.python_version.StartsWith('3.12')) {
    throw 'Manifest Python runtime tidak valid atau versi bukan 3.12.'
}
# Disallow any example/customer media in the published installer.
$appAssets = Join-Path $unpacked 'resources\app\src\assets'
$leaked = @()
if (Test-Path $appAssets) {
  $leaked = @(Get-ChildItem $appAssets -File -Recurse | Where-Object {
    $_.Extension -in @('.mp4','.webm','.gif','.jpg','.jpeg') -or
    $_.Name -match '^frame[-_]' -or $_.Name -eq 'dashboard-background.mp4'
  })
}
if ($leaked.Count -gt 0) {
  throw "Installer berisi media contoh/pelanggan: $($leaked.FullName -join ', ')"
}
$licenseUi = Join-Path $unpacked 'resources\app\src\app.js'
if (!(Test-Path $licenseUi) -or !(Select-String -Path $licenseUi -SimpleMatch -Quiet 'licenseActivate')) {
  throw 'Menu aktivasi lisensi tidak ditemukan di installer.'
}
$agentUi = Join-Path $unpacked 'resources\app\cloud_control\agent.js'
if (!(Test-Path $agentUi) -or !(Select-String -Path $agentUi -SimpleMatch -Quiet 'DEFAULT_CLOUD_ORIGIN')) {
  throw 'Cloud Agent tidak ditemukan di installer.'
}
$exeSize=(Get-Item $installer).Length
if ($exeSize -lt 30MB) { throw 'Ukuran installer tidak wajar. Dependensi mungkin tidak terbundel.' }
$pythonExeHash=(Get-FileHash -Algorithm SHA256 $python).Hash
if ($pythonExeHash -ne $runtimeManifest.python_exe_sha256) {
    throw 'Checksum Python executable tidak cocok dengan manifest build.'
}
$vcHash=(Get-FileHash -Algorithm SHA256 $vc).Hash
if ($vcHash -ne $runtimeManifest.vc_redist_sha256) {
    throw 'Checksum VC runtime tidak cocok dengan manifest build.'
}
& $python -I -c 'import cv2,numpy,PIL,qrcode; print("PACKAGED_PYTHON_OK",cv2.__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Bundled Python gagal menjalankan OpenCV dalam paket unpacked.' }
& $python -I -m py_compile $cameraServer
if ($LASTEXITCODE -ne 0) { throw 'Backend Python gagal preflight syntax.' }
$hash=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLower()
"$hash  KACA-ID-Setup-0.9.90-x64.exe" | Set-Content -Encoding Ascii "$installer.sha256"
Write-Host "[OK] Windows installer siap, $([Math]::Round($exeSize/1MB,1)) MB" -ForegroundColor Green
Write-Host "[OK] Python 3.12, OpenCV, VC++ offline, serta manifest tersedia."
Write-Host "[OK] SHA256: $hash"
