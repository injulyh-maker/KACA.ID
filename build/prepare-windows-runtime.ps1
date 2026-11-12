# KACA.ID v0.9.90 - Windows x64 release builder.
# Builder: cross-installs cp312 Windows wheels using an existing pip host (such as Python 3.14).
# Customer installer: includes embeddable Python 3.12 + dependencies and VC++.
[CmdletBinding()]
param([switch]$Force)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $root 'runtime'
$pythonDir = Join-Path $runtime 'python'
$pythonExe = Join-Path $pythonDir 'python.exe'
$vcExe = Join-Path $runtime 'vc_redist.x64.exe'
$pythonVersion = '3.12.10'   # Canon EDSDK binding is cp312-win_amd64.
$pythonZipUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$vcUrl = 'https://aka.ms/vc14/vc_redist.x64.exe'

function Show-Phase([string]$message) {
    Write-Host "`n[KACA BUILD] $message" -ForegroundColor Cyan
}

function Download([string]$url, [string]$destination) {
    Write-Host "Mengunduh: $url"
    Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing -MaximumRedirection 10
    if (!(Test-Path -LiteralPath $destination) -or (Get-Item -LiteralPath $destination).Length -lt 200000) {
        throw "Unduhan rusak atau terlalu kecil: $destination"
    }
}

# We intentionally do not install Python 3.12 on the build computer.
# pip's --platform/--python-version/--implementation/--abi options select
# CPython 3.12 Windows x64 binary wheels even if pip runs under Python 3.14.
function Test-PipHost([string]$candidate) {
    if ([string]::IsNullOrWhiteSpace($candidate) -or !(Test-Path -LiteralPath $candidate -PathType Leaf)) {
        return $false
    }
    try {
        & $candidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { return $false }
        & $candidate -m pip --version 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-PipHost {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    if ($env:KACA_PIP_PYTHON) { $candidates.Add($env:KACA_PIP_PYTHON) }
    foreach ($commandName in @('python.exe','python3.exe')) {
        foreach ($command in @(Get-Command $commandName -All -ErrorAction SilentlyContinue)) {
            if ($command.Source) { $candidates.Add($command.Source) }
        }
    }
    # Also find installations not first on PATH through Windows py launcher.
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @('-3.12','-3.13','-3.14','-3.15')) {
            try {
                $candidate = & $launcher.Source $version -c 'import sys;print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0 -and $candidate) {
                    $candidates.Add(([string]($candidate | Select-Object -First 1)).Trim())
                }
            } catch { }
        }
    }
    $seen = @{}
    foreach ($candidate in $candidates) {
        if (!$candidate -or $seen.ContainsKey($candidate)) { continue }
        $seen[$candidate] = $true
        if (Test-PipHost $candidate) { return $candidate }
    }
    return $null
}

function Install-Cp312Wheels([string]$pipHost, [string]$requirements) {
    # Cross-target constraints are essential: Python 3.14 wheels MUST NOT be
    # installed in the Python 3.12 embedded customer runtime.
    $pipArgs = @(
        '-m','pip','install',
        '--disable-pip-version-check', '--no-compile',
        '--only-binary=:all:',
        '--platform','win_amd64',
        '--python-version','3.12',
        '--implementation','cp',
        '--abi','cp312',
        '--ignore-installed',
        '--upgrade',
        '--target', $sitePackages,
        '-r', $requirements
    )
    Write-Host "Mengambil paket khusus CPython 3.12 Windows x64: $requirements"
    & $pipHost @pipArgs
    if ($LASTEXITCODE -ne 0) {
        throw "pip gagal mengambil wheel cp312-win_amd64 untuk $requirements. Periksa internet/PyPI atau versi requirement."
    }
}

New-Item -ItemType Directory -Force -Path $runtime | Out-Null
if ($Force -and (Test-Path $pythonDir)) { Remove-Item -LiteralPath $pythonDir -Recurse -Force }
if (!(Test-Path $pythonExe)) {
    Show-Phase "Menyiapkan Python Embeddable $pythonVersion (Windows x64)"
    $zip = Join-Path $env:TEMP "kaca-python-$pythonVersion-embed-amd64.zip"
    try {
        Download $pythonZipUrl $zip
        New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
        Expand-Archive -Path $zip -DestinationPath $pythonDir -Force
    } finally { Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue }
}
$pth = Join-Path $pythonDir 'python312._pth'
if (!(Test-Path $pythonExe) -or !(Test-Path $pth)) {
    throw 'Python 3.12 embeddable tidak lengkap. Gunakan -Force untuk membangun ulang.'
}
# Isolate packaged packages from global Python; only app-managed paths are loaded.
@('python312.zip', '.', 'Lib\site-packages', '..\app', '..\..', 'import site') | Set-Content -Path $pth -Encoding Ascii
$sitePackages = Join-Path $pythonDir 'Lib\site-packages'
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
$marker = Join-Path $runtime 'runtime-build-complete.json'
if ($Force -or !(Test-Path $marker)) {
    Show-Phase 'Memasang semua dependensi Python secara privat pada tahap BUILD'
    Show-Phase 'Memilih pip yang tersedia (Python 3.14 dapat digunakan sebagai host)'
    $pipHost = Find-PipHost
    if (!$pipHost) {
        throw 'Tidak ditemukan Python 3.8+ dengan pip. Periksa: python -m pip --version. Jika pip belum ada, gunakan python -m ensurepip --upgrade (sekali di PC builder), lalu ulangi build.'
    }
    Write-Host "pip host dipilih: $pipHost" -ForegroundColor Green
    & $pipHost -m pip --version
    # Strictly select Python 3.12 Windows wheels, regardless of the host version.
    Install-Cp312Wheels $pipHost (Join-Path $root 'requirements.txt')
    Install-Cp312Wheels $pipHost (Join-Path $root 'cloud_control\requirements.txt')
}

Show-Phase 'Memeriksa modul Python portable'
$preflight = Join-Path $root 'build\runtime_preflight.py'
& $pythonExe -I $preflight
if ($LASTEXITCODE -ne 0) { throw 'Preflight runtime Python gagal, installer tidak boleh dibuat.' }

if ($Force -or !(Test-Path $vcExe)) {
    Show-Phase 'Menyiapkan Microsoft Visual C++ Redistributable (offline)'
    Download $vcUrl $vcExe
}
$signature = Get-AuthenticodeSignature -FilePath $vcExe
if ($signature.Status -ne 'Valid' -or !$signature.SignerCertificate -or
    $signature.SignerCertificate.Subject -notmatch 'Microsoft') {
    throw 'VC++ Redistributable tidak memiliki tanda tangan Microsoft yang valid. Hentikan distribusi!'
}
$pythonVersionText = (& $pythonExe -I -c 'import sys; print(sys.version.split()[0])').Trim()
$manifest = @{
    created_utc = [DateTime]::UtcNow.ToString('o')
    python_version = $pythonVersionText
    python_arch = 'win_amd64'
    python_exe_sha256 = (Get-FileHash -Algorithm SHA256 $pythonExe).Hash
    vc_redist_sha256 = (Get-FileHash -Algorithm SHA256 $vcExe).Hash
    vc_redist_signed_by = $signature.SignerCertificate.Subject
    bundled_dependencies = @('opencv-python','numpy','Pillow','qrcode','fastapi','uvicorn','cryptography','argon2-cffi')
    verified = $true
} | ConvertTo-Json -Depth 4
$manifest | Set-Content -Path $marker -Encoding UTF8
Show-Phase 'Siap. Python dan VC++ sudah ada di folder runtime untuk dimasukkan ke installer.'
