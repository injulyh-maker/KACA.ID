"""Bundled Python x64 health check. Never requires a physical camera."""
import importlib
import platform
import sys
from pathlib import Path

assert sys.version_info[:2] == (3, 12), f"Expected Python 3.12 for Canon SDK, got {sys.version}"
assert platform.architecture()[0] == "64bit", "Windows runtime must be x64"
for package in ("cv2", "numpy", "PIL", "qrcode", "fastapi", "uvicorn", "cryptography", "argon2"):
    module = importlib.import_module(package)
    print(f"[OK] {package}: {getattr(module, '__version__', 'available')}")
source = Path(__file__).resolve().parents[1] / "backend"
if source.is_dir():
    sys.path.insert(0, str(source))
    for local in ("canon_edsdk_runtime", "google_drive", "session_retention", "doku_qris", "whatsapp_gateway"):
        importlib.import_module(local)
        print(f"[OK] backend/{local}.py import")
print("[OK] Bundled Python runtime ready", sys.version.split()[0])
