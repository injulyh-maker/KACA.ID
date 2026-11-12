"""Canon EDSDK discovery adapter for KACA.ID.

The bundled SDK package is preserved under backend/edsdk/SDK_Package/EDSDK.
The active x64 EDSDK.dll is loaded from backend/edsdk or KACA_EDSDK_DIR.
This adapter currently implements camera enumeration; native Live View and
tethered capture require additional camera-session/event integration.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path

from canon_edsdk_runtime import SDK_LOCK, get_live_camera

EDS_MAX_NAME = 256


class EdsDeviceInfo(ctypes.Structure):
    _fields_ = [
        ("szPortName", ctypes.c_char * EDS_MAX_NAME),
        ("szDeviceDescription", ctypes.c_char * EDS_MAX_NAME),
        ("deviceSubType", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
    ]


def _decode(value: bytes) -> str:
    value = bytes(value or b"").split(b"\0", 1)[0]
    for encoding in ("mbcs", "utf-8", "cp1252"):
        try:
            return value.decode(encoding, errors="strict").strip()
        except (LookupError, UnicodeDecodeError):
            continue
    return value.decode("latin-1", errors="replace").strip()


def _candidate_dirs() -> list[Path]:
    here = Path(__file__).resolve().parent
    app_root = here.parent
    candidates: list[Path] = []
    env_dir = os.environ.get("KACA_EDSDK_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.extend([
        here / "edsdk",
        here / "edsdk" / "SDK_Package" / "EDSDK",
        here / "edsdk" / "SDK_Package" / "EDSDK" / "Dll",
        here / "EDSDK",
        app_root / "EDSDK",
        app_root / "resources" / "EDSDK",
        Path(sys.executable).resolve().parent / "_internal" / "EDSDK",
    ])
    for root_var in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(root_var)
        if root:
            root_path = Path(root)
            candidates.extend([
                root_path / "Canon" / "EDSDK",
                root_path / "Canon" / "EOS Utility" / "EDSDK",
                root_path / "Canon" / "EOS Utility" / "EDSDK" / "Dll",
            ])
    # Include DLL directories already exposed through PATH.
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry and "canon" in entry.lower():
            candidates.append(Path(entry))
    unique = []
    seen = set()
    for item in candidates:
        key = os.path.normcase(os.path.abspath(str(item)))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _pe_machine(path: Path) -> int | None:
    """Read the PE machine field without loading the DLL."""
    try:
        with path.open("rb") as stream:
            header = stream.read(4096)
        if len(header) < 64 or header[:2] != b"MZ":
            return None
        pe_offset = int.from_bytes(header[0x3C:0x40], "little")
        if pe_offset + 6 > len(header) or header[pe_offset:pe_offset + 4] != b"PE\0\0":
            return None
        return int.from_bytes(header[pe_offset + 4:pe_offset + 6], "little")
    except (OSError, ValueError):
        return None


def find_edsdk_dll() -> Path | None:
    # Never load an x86 DLL into the x64 Python process used by KACA.ID.
    for folder in _candidate_dirs():
        candidate = folder / "EDSDK.dll"
        if candidate.is_file() and _pe_machine(candidate) == 0x8664:
            return candidate
    located = shutil.which("EDSDK.dll")
    if located:
        candidate = Path(located)
        if candidate.is_file() and _pe_machine(candidate) == 0x8664:
            return candidate
    return None


def sdk_package_diagnostics() -> dict:
    here = Path(__file__).resolve().parent
    package = here / "edsdk" / "SDK_Package" / "EDSDK"
    image_candidates = [package / "Dll" / "EdsImage.dll", package / "EdsImage.dll"]
    image_dll = next((p for p in image_candidates if p.is_file()), None)
    binding = None
    if sys.version_info[:2] == (3, 12):
        binding = package / "api.cp312-win_amd64.pyd"
    elif sys.version_info[:2] == (3, 9):
        binding = package / "api.cp39-win_amd64.pyd"
    return {
        "sdk_package_included": package.is_dir(),
        "python_version": sys.version.split()[0],
        "python_binding": str(binding) if binding and binding.is_file() else None,
        "python_binding_compatible": bool(binding and binding.is_file()),
        "edsimage_dll": str(image_dll) if image_dll else None,
        "edsimage_machine": hex(_pe_machine(image_dll)) if image_dll and _pe_machine(image_dll) is not None else None,
        "edsimage_usable_in_x64_process": bool(image_dll and _pe_machine(image_dll) == 0x8664),
    }


def _detect_canon_cameras_locked() -> dict:
    """Enumerate Canon cameras with EdsGetCameraList/GetDeviceInfo."""
    if sys.platform != "win32":
        return {
            "sdk_available": False,
            "available": False,
            "cameras": [],
            "message": "Canon EDSDK hanya tersedia pada Windows di build ini.",
        }
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return {
            "sdk_available": False,
            "available": False,
            "cameras": [],
            "message": "KACA.ID memerlukan Canon EDSDK 64-bit dan Python 64-bit.",
        }

    dll_path = find_edsdk_dll()
    if not dll_path:
        return {
            "sdk_available": False,
            "available": False,
            "cameras": [],
            "dll_found": False,
            "sdk_package": sdk_package_diagnostics(),
            "message": "Canon EDSDK.dll 64-bit belum ditemukan. Letakkan EDSDK.dll dan DLL pendamping dari paket resmi Canon di folder backend\\edsdk, lalu jalankan ulang KACA.ID.",
        }

    dll_dir_handle = None
    sdk = None
    camera_list = ctypes.c_void_p()
    initialized = False
    cameras = []
    errors = []
    try:
        if hasattr(os, "add_dll_directory"):
            dll_dir_handle = os.add_dll_directory(str(dll_path.parent))
        sdk = ctypes.WinDLL(str(dll_path))  # EDSDK uses the Windows stdcall ABI.
        sdk.EdsInitializeSDK.argtypes = []
        sdk.EdsInitializeSDK.restype = ctypes.c_uint32
        sdk.EdsTerminateSDK.argtypes = []
        sdk.EdsTerminateSDK.restype = ctypes.c_uint32
        sdk.EdsGetCameraList.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        sdk.EdsGetCameraList.restype = ctypes.c_uint32
        sdk.EdsGetChildCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        sdk.EdsGetChildCount.restype = ctypes.c_uint32
        sdk.EdsGetChildAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_void_p)]
        sdk.EdsGetChildAtIndex.restype = ctypes.c_uint32
        sdk.EdsGetDeviceInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(EdsDeviceInfo)]
        sdk.EdsGetDeviceInfo.restype = ctypes.c_uint32
        sdk.EdsRelease.argtypes = [ctypes.c_void_p]
        sdk.EdsRelease.restype = ctypes.c_uint32

        err = int(sdk.EdsInitializeSDK())
        if err != 0:
            raise RuntimeError(f"EdsInitializeSDK gagal (0x{err:08X}). Tutup EOS Utility/aplikasi kamera lain dan coba lagi.")
        initialized = True

        err = int(sdk.EdsGetCameraList(ctypes.byref(camera_list)))
        if err != 0:
            raise RuntimeError(f"EdsGetCameraList gagal (0x{err:08X}). Periksa driver Canon dan koneksi USB.")
        count = ctypes.c_uint32(0)
        err = int(sdk.EdsGetChildCount(camera_list, ctypes.byref(count)))
        if err != 0:
            raise RuntimeError(f"EdsGetChildCount gagal (0x{err:08X}).")

        for index in range(int(count.value)):
            camera_ref = ctypes.c_void_p()
            child_err = int(sdk.EdsGetChildAtIndex(camera_list, index, ctypes.byref(camera_ref)))
            if child_err != 0 or not camera_ref.value:
                errors.append(f"Kamera {index}: EdsGetChildAtIndex 0x{child_err:08X}")
                continue
            try:
                info = EdsDeviceInfo()
                info_err = int(sdk.EdsGetDeviceInfo(camera_ref, ctypes.byref(info)))
                if info_err != 0:
                    errors.append(f"Kamera {index}: EdsGetDeviceInfo 0x{info_err:08X}")
                    continue
                description = _decode(info.szDeviceDescription) or f"Canon EOS Camera {index + 1}"
                port = _decode(info.szPortName)
                cameras.append({
                    "id": f"canon_edsdk_{index}",
                    "name": description,
                    "port": port,
                    "device_sub_type": int(info.deviceSubType),
                    "type": "canon_edsdk",
                    "physical_identity": f"canon:{description}:{port}",
                })
            finally:
                try:
                    sdk.EdsRelease(camera_ref)
                except Exception:
                    pass

        return {
            "sdk_available": True,
            "dll_found": True,
            "dll_path": str(dll_path),
            "sdk_package": sdk_package_diagnostics(),
            "available": bool(cameras),
            "cameras": cameras,
            "errors": errors,
            "message": (
                f"Canon EDSDK berhasil mendeteksi {len(cameras)} kamera."
                if cameras else
                "EDSDK aktif, tetapi tidak menemukan kamera Canon. Pastikan EOS 1300D dalam mode pemotretan, kabel USB data terhubung langsung, dan EOS Utility/ aplikasi lain tidak sedang mengunci kamera."
            ),
        }
    except Exception as exc:
        return {
            "sdk_available": True,
            "dll_found": True,
            "dll_path": str(dll_path),
            "sdk_package": sdk_package_diagnostics(),
            "available": False,
            "cameras": [],
            "errors": errors,
            "message": f"Canon EDSDK gagal dijalankan: {exc}",
        }
    finally:
        if camera_list.value and sdk is not None:
            try:
                sdk.EdsRelease(camera_list)
            except Exception:
                pass
        if initialized and sdk is not None:
            try:
                sdk.EdsTerminateSDK()
            except Exception:
                pass
        if dll_dir_handle is not None:
            try:
                dll_dir_handle.close()
            except Exception:
                pass


def detect_canon_cameras() -> dict:
    """Discover Canon cameras without disrupting an active Live View session."""
    with SDK_LOCK:
        active = get_live_camera()
        if active:
            return {
                "sdk_available": True, "dll_found": True, "available": True,
                "busy": True, "cameras": [active],
                "message": "Canon sedang digunakan oleh Live View KACA.ID; sesi aktif dipertahankan."
            }
        return _detect_canon_cameras_locked()
