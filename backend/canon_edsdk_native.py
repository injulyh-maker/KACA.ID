
"""Native Canon EDSDK Live View controller for KACA.ID (Windows x64)."""
from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import time
from pathlib import Path

from canon_edsdk_runtime import SDK_LOCK, set_live_camera

EDS_MAX_NAME = 256
PROP_EVF_OUTPUT_DEVICE = 0x00000500
PROP_EVF_MODE = 0x00000501
EVF_MODE_ON = 1
EVF_MODE_OFF = 0
EVF_OUTPUT_PC_AND_TFT = 3

CMD_PRESS_SHUTTER = 0x00000004
SHUTTER_HALFWAY = 0x00000001
SHUTTER_COMPLETELY = 0x00000003
SHUTTER_OFF = 0x00000000

TRANSIENT_EVF_ERRORS = {
    0x0000A102,
    0x00000081,
    0x00002019,
}


class EdsDeviceInfo(ctypes.Structure):
    _fields_ = [
        ("szPortName", ctypes.c_char * EDS_MAX_NAME),
        ("szDeviceDescription", ctypes.c_char * EDS_MAX_NAME),
        ("deviceSubType", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
    ]


def _decode(value):
    raw = bytes(value or b"").split(b"\0", 1)[0]

    for encoding in ("mbcs", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding).strip()
        except (LookupError, UnicodeDecodeError):
            pass

    return raw.decode("latin-1", errors="replace").strip()


class CanonLiveView:

    def __init__(self, on_frame, camera_index=0, on_progress=None):
        self.on_frame = on_frame
        self.on_progress = on_progress
        self.camera_index = int(camera_index)

        self.dll = None
        self.dll_dir = None

        self.camera_list = ctypes.c_void_p()
        self.camera = ctypes.c_void_p()

        self.initialized = False
        self.session_open = False

        self.running = threading.Event()
        self.thread = None
        self.startup_event = threading.Event()
        self.startup_error = None
        self.thread_exception = None
        self.thread_exception_traceback = None
        self.command_queue = queue.Queue()

        self.lock = threading.RLock()
        self.cleanup_lock = threading.RLock()

        self.cleaned = False
        self.last_error = None

        self.frames = 0
        self.last_frame_at = None

        # Diagnostic counters: make silent EVF failures visible to the UI/log.
        self.download_attempts = 0
        self.download_error_counts = {}
        self.event_error_counts = {}
        self.empty_stream_count = 0
        self.invalid_pointer_count = 0
        self.non_jpeg_count = 0
        self.last_download_code = None
        self.last_stream_length = None
        self.last_payload_header = None

        # Diagnostik pemanggilan native EDSDK
        self.last_stage = "belum dimulai"
        self.download_call_pending = False
        self.download_call_started_at = None
        self.download_call_elapsed = None
        self.last_download_return_at = None

        self.device_name = "Canon EOS"
        self.width = 0
        self.height = 0

    @staticmethod
    def _dll_path():
        here = Path(__file__).resolve().parent

        candidates = [
            here / "edsdk" / "EDSDK.dll",
            here / "EDSDK.dll",
        ]

        for candidate in candidates:
            if not candidate.is_file():
                continue

            try:
                with candidate.open("rb") as f:
                    header = f.read(4096)

                pe_offset = int.from_bytes(
                    header[0x3C:0x40], "little"
                )

                is_pe = (
                    header[:2] == b"MZ"
                    and header[pe_offset:pe_offset + 4] == b"PE\0\0"
                )

                is_x64 = (
                    int.from_bytes(
                        header[pe_offset + 4:pe_offset + 6],
                        "little"
                    ) == 0x8664
                )

                if is_pe and is_x64:
                    return candidate

            except Exception:
                pass

        raise RuntimeError(
            "EDSDK.dll 64-bit tidak ditemukan di backend/edsdk."
        )

    def _progress(self, stage, detail):
        """Report the exact native EDSDK operation currently in progress."""
        callback = self.on_progress
        if callback is not None:
            try:
                callback(stage, detail)
            except Exception:
                # Diagnostics must never interrupt camera control.
                pass

    def _bind(self):
        d = self.dll

        d.EdsInitializeSDK.argtypes = []
        d.EdsInitializeSDK.restype = ctypes.c_uint32

        d.EdsTerminateSDK.argtypes = []
        d.EdsTerminateSDK.restype = ctypes.c_uint32

        d.EdsGetCameraList.argtypes = [
            ctypes.POINTER(ctypes.c_void_p)
        ]
        d.EdsGetCameraList.restype = ctypes.c_uint32

        d.EdsGetChildCount.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32)
        ]
        d.EdsGetChildCount.restype = ctypes.c_uint32

        d.EdsGetChildAtIndex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_void_p)
        ]
        d.EdsGetChildAtIndex.restype = ctypes.c_uint32

        d.EdsGetDeviceInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(EdsDeviceInfo)
        ]
        d.EdsGetDeviceInfo.restype = ctypes.c_uint32

        d.EdsOpenSession.argtypes = [ctypes.c_void_p]
        d.EdsOpenSession.restype = ctypes.c_uint32

        d.EdsCloseSession.argtypes = [ctypes.c_void_p]
        d.EdsCloseSession.restype = ctypes.c_uint32

        d.EdsRelease.argtypes = [ctypes.c_void_p]
        d.EdsRelease.restype = ctypes.c_uint32

        d.EdsSetPropertyData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int32,
            ctypes.c_uint32,
            ctypes.c_void_p
        ]
        d.EdsSetPropertyData.restype = ctypes.c_uint32

        d.EdsGetPropertyData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int32,
            ctypes.c_uint32,
            ctypes.c_void_p
        ]
        d.EdsGetPropertyData.restype = ctypes.c_uint32

        d.EdsCreateMemoryStream.argtypes = [
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_void_p)
        ]
        d.EdsCreateMemoryStream.restype = ctypes.c_uint32

        d.EdsCreateEvfImageRef.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p)
        ]
        d.EdsCreateEvfImageRef.restype = ctypes.c_uint32

        d.EdsDownloadEvfImage.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p
        ]
        d.EdsDownloadEvfImage.restype = ctypes.c_uint32

        d.EdsGetPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p)
        ]
        d.EdsGetPointer.restype = ctypes.c_uint32

        d.EdsGetLength.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint64)
        ]
        d.EdsGetLength.restype = ctypes.c_uint32

        d.EdsGetEvent.argtypes = []
        d.EdsGetEvent.restype = ctypes.c_uint32

        d.EdsSendCommand.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int32
        ]
        d.EdsSendCommand.restype = ctypes.c_uint32

    def _check(self, code, label):
        code = int(code)

        if code != 0:
            raise RuntimeError(
                f"{label} gagal (EDSDK 0x{code:08X}). "
                "Pastikan EOS 1300D dalam mode foto, "
                "tutup EOS Utility, dan periksa koneksi USB."
            )

    def start(self):
        """Start the dedicated EDSDK thread and wait for its first frame.

        Every EDSDK entry point is called by this one thread. The caller only
        waits on Python events and never invokes the native SDK directly.
        """
        if sys.platform != "win32" or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise RuntimeError("Canon Live View memerlukan Windows 64-bit.")

        if self.thread and self.thread.is_alive():
            raise RuntimeError("Thread Canon EDSDK sudah berjalan.")

        self.cleaned = False
        self.startup_error = None
        self.startup_event.clear()
        self.running.clear()
        self.thread = threading.Thread(
            target=self._sdk_thread_main,
            name="KACA-Canon-EDSDK-Owner",
            daemon=True,
        )
        self.thread.start()

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if self.frames:
                return {
                    "ok": True,
                    "camera_open": True,
                    "reader_alive": True,
                    "selected": f"canon_edsdk_{self.camera_index}",
                    "name": self.device_name,
                    "frames": self.frames,
                    "frames_read": self.frames,
                    "width": self.width,
                    "height": self.height,
                    "frame_width": self.width,
                    "frame_height": self.height,
                    "backend": "Canon EDSDK Live View (single-thread)",
                }
            if self.startup_error:
                raise RuntimeError(self.startup_error)
            if self.startup_event.is_set() and not self.thread.is_alive():
                raise RuntimeError(self.startup_error or "Thread Canon berhenti sebelum frame pertama.")
            time.sleep(0.05)

        error = self.last_error or self._diagnostic_timeout_error()
        # Never call EDSDK cleanup from this caller thread. If a native call is
        # blocked, the isolated worker process is the safe teardown boundary.
        self.running.clear()
        raise RuntimeError(error)

    def _sdk_thread_main(self):
        """Own the complete EDSDK lifecycle on one stable OS thread."""
        try:
            self._initialize_sdk_on_owner_thread()
            self.running.set()
            self.startup_event.set()
            self._loop()  # event pump, EVF download, capture and cleanup
        except BaseException as exc:
            import traceback
            self.startup_error = str(exc)
            self.thread_exception = repr(exc)
            self.thread_exception_traceback = traceback.format_exc()
            self.last_error = str(exc)
            self.startup_event.set()
            self.running.clear()
            try:
                self._cleanup_sdk()
            except Exception:
                pass

    def _initialize_sdk_on_owner_thread(self):
        path = self._dll_path()
        if hasattr(os, "add_dll_directory"):
            self.dll_dir = os.add_dll_directory(str(path.parent))

        with SDK_LOCK:
            self._progress("load_native_dll", f"Memuat EDSDK dari {path}.")
            self.dll = ctypes.WinDLL(str(path))
            self._bind()

            self._progress("eds_initialize", "Memanggil EdsInitializeSDK().")
            self._check(self.dll.EdsInitializeSDK(), "EdsInitializeSDK")
            self.initialized = True

            self._progress("get_camera_list", "Memanggil EdsGetCameraList().")
            self._check(self.dll.EdsGetCameraList(ctypes.byref(self.camera_list)), "EdsGetCameraList")

            self._progress("count_cameras", "Memanggil EdsGetChildCount().")
            count = ctypes.c_uint32()
            self._check(self.dll.EdsGetChildCount(self.camera_list, ctypes.byref(count)), "EdsGetChildCount")
            if self.camera_index < 0 or self.camera_index >= count.value:
                raise RuntimeError(
                    f"Kamera Canon indeks {self.camera_index} tidak tersedia; ditemukan {count.value} kamera."
                )

            self._progress("get_camera_ref", "Memanggil EdsGetChildAtIndex().")
            self._check(
                self.dll.EdsGetChildAtIndex(self.camera_list, self.camera_index, ctypes.byref(self.camera)),
                "EdsGetChildAtIndex",
            )

            self._progress("get_device_info", "Memanggil EdsGetDeviceInfo().")
            info = EdsDeviceInfo()
            self._check(self.dll.EdsGetDeviceInfo(self.camera, ctypes.byref(info)), "EdsGetDeviceInfo")
            self.device_name = _decode(info.szDeviceDescription) or "Canon EOS"

            self._progress("open_session", "Memanggil EdsOpenSession().")
            self._check(self.dll.EdsOpenSession(self.camera), "EdsOpenSession")
            self.session_open = True

            evf_mode = ctypes.c_uint32(EVF_MODE_ON)
            self._progress("set_evf_mode", "Mengaktifkan EVF Mode (value=1).")
            self._check(
                self.dll.EdsSetPropertyData(
                    self.camera, PROP_EVF_MODE, 0, ctypes.sizeof(evf_mode), ctypes.byref(evf_mode)
                ),
                "Mengaktifkan EVF Mode",
            )

            time.sleep(0.2)
            output = ctypes.c_uint32(EVF_OUTPUT_PC_AND_TFT)
            self._progress("set_evf_output_pc", "Mengatur EVF Output Device ke PC + TFT (value=3).")
            self._check(
                self.dll.EdsSetPropertyData(
                    self.camera, PROP_EVF_OUTPUT_DEVICE, 0, ctypes.sizeof(output), ctypes.byref(output)
                ),
                "Mengaktifkan EVF ke PC + TFT",
            )

            self._progress("evf_camera_warmup", "Menunggu 750 ms agar kamera menyiapkan frame Live View.")
            time.sleep(0.75)
            self._progress("pump_initial_events", "Memproses event awal Canon melalui EdsGetEvent().")
            self._check(self.dll.EdsGetEvent(), "EdsGetEvent setelah mengaktifkan EVF")

            set_live_camera({
                "id": f"canon_edsdk_{self.camera_index}",
                "name": self.device_name,
                "type": "canon_edsdk",
            })

        self._progress(
            "start_evf_frame_loop_single_thread",
            "Inisialisasi selesai; EdsGetEvent dan EdsDownloadEvfImage akan berjalan pada thread pemilik EDSDK yang sama.",
        )

    def _diagnostic_timeout_error(self):
        if self.frames:
            return (
                f"Live View sempat menerima {self.frames} frame, "
                "tetapi proses preview berhenti."
            )

        if self.download_attempts == 0:
            detail = "Loop EVF belum menjalankan EdsDownloadEvfImage."
        elif self.download_call_pending:
            elapsed = (
                time.monotonic() - self.download_call_started_at
                if self.download_call_started_at is not None else 0
            )
            detail = (
                "EdsDownloadEvfImage masih tertahan/tidak kembali. "
                f"Sudah menunggu {elapsed:.1f} detik; "
                f"tahap terakhir: {self.last_stage}."
            )
        elif self.last_download_code is not None:
            code = self.last_download_code
            count = self.download_error_counts.get(code, 0)
            detail = (
                f"EdsDownloadEvfImage terakhir menghasilkan "
                f"0x{code:08X} ({count} kali untuk kode terakhir)."
            )
        elif self.non_jpeg_count:
            detail = (
                f"EDSDK mengembalikan stream, tetapi {self.non_jpeg_count} "
                f"payload bukan JPEG; header terakhir "
                f"{self.last_payload_header!r}."
            )
        elif self.empty_stream_count:
            detail = (
                f"EDSDK belum mengisi stream: {self.empty_stream_count} "
                f"kali stream kosong; panjang terakhir "
                f"{self.last_stream_length} byte."
            )
        elif self.invalid_pointer_count:
            detail = (
                f"EDSDK memberi panjang stream tetapi pointer tidak valid "
                f"({self.invalid_pointer_count} kali)."
            )
        else:
            detail = (
                "Tidak ada frame JPEG yang dapat diproses. "
                f"Percobaan download: {self.download_attempts}; "
                f"panjang stream terakhir: {self.last_stream_length}."
            )

        if self.event_error_counts:
            event_summary = ", ".join(
                f"0x{code:08X}:{count}"
                for code, count in sorted(self.event_error_counts.items())
            )
            detail += f" Error EdsGetEvent: {event_summary}."

        return (
            "Canon belum menghasilkan frame Live View untuk KACA.ID "
            "dalam 8 detik. Diagnostik: " + detail
        )

    def _loop(self):

        try:
            while self.running.is_set():

                # Jalankan perintah kamera pada thread pemilik EDSDK juga.
                self._process_pending_commands()
                if not self.running.is_set():
                    break

                # Proses event EDSDK pada setiap iterasi dan catat kegagalan.
                if self.download_attempts == 0:
                    self._progress(
                        "evf_process_events",
                        "Thread Live View mulai memproses EdsGetEvent()."
                    )
                try:
                    event_code = int(self.dll.EdsGetEvent())
                    if event_code != 0:
                        self.event_error_counts[event_code] = (
                            self.event_error_counts.get(event_code, 0) + 1
                        )
                except Exception:
                    pass

                stream = ctypes.c_void_p()
                evf = ctypes.c_void_p()

                try:
                    if self.download_attempts == 0:
                        self._progress(
                            "evf_create_memory_stream",
                            "Membuat stream EVF melalui EdsCreateMemoryStream()."
                        )
                    self._check(
                        self.dll.EdsCreateMemoryStream(
                            0,
                            ctypes.byref(stream)
                        ),
                        "EdsCreateMemoryStream"
                    )

                    if self.download_attempts == 0:
                        self._progress(
                            "evf_create_image_ref",
                            "Membuat referensi gambar melalui EdsCreateEvfImageRef()."
                        )
                    self._check(
                        self.dll.EdsCreateEvfImageRef(
                            stream,
                            ctypes.byref(evf)
                        ),
                        "EdsCreateEvfImageRef"
                    )

                    self.download_attempts += 1
                    self.last_stage = "memanggil EdsDownloadEvfImage"
                    if self.download_attempts == 1:
                        self._progress(
                            "evf_download_call",
                            "Memanggil EdsDownloadEvfImage(); menunggu frame pertama dari EOS 1300D."
                        )
                    self.download_call_pending = True
                    self.download_call_started_at = time.monotonic()

                    try:
                        code = int(
                            self.dll.EdsDownloadEvfImage(
                                self.camera,
                                evf
                            )
                        )
                    finally:
                        self.download_call_elapsed = (
                            time.monotonic()
                            - self.download_call_started_at
                        )
                        self.last_download_return_at = time.time()
                        self.download_call_pending = False
                        self.last_stage = "EdsDownloadEvfImage selesai"

                    if self.download_attempts == 1:
                        self._progress(
                            "evf_download_returned",
                            f"EdsDownloadEvfImage selesai dengan kode 0x{code:08X}."
                        )
                    self.last_download_code = code if code else None

                    if code in TRANSIENT_EVF_ERRORS:
                        self.download_error_counts[code] = (
                            self.download_error_counts.get(code, 0) + 1
                        )
                        self.last_error = None
                        time.sleep(0.08)
                        continue

                    self._check(
                        code,
                        "EdsDownloadEvfImage"
                    )

                    length = ctypes.c_uint64()

                    self._check(
                        self.dll.EdsGetLength(
                            stream,
                            ctypes.byref(length)
                        ),
                        "EdsGetLength"
                    )
                    self.last_stream_length = int(length.value)
                    if self.download_attempts == 1:
                        self._progress(
                            "evf_stream_length",
                            f"Stream EVF diterima dengan panjang {length.value} byte."
                        )

                    pointer = ctypes.c_void_p()

                    self._check(
                        self.dll.EdsGetPointer(
                            stream,
                            ctypes.byref(pointer)
                        ),
                        "EdsGetPointer"
                    )

                    if not pointer.value:
                        self.invalid_pointer_count += 1
                    elif length.value <= 4:
                        self.empty_stream_count += 1
                    elif length.value >= 20_000_000:
                        self.last_error = (
                            f"Ukuran stream EVF tidak wajar: {length.value} byte."
                        )
                    else:
                        payload = ctypes.string_at(
                            pointer.value,
                            int(length.value)
                        )
                        self.last_payload_header = payload[:16].hex(" ")

                        if payload[:2] == bytes((0xFF, 0xD8)):
                            if self.frames == 0:
                                self._progress(
                                    "evf_jpeg_received",
                                    f"JPEG EVF diterima ({length.value} byte); meneruskan frame ke aplikasi."
                                )
                            try:
                                dimensions = self.on_frame(payload)
                            except Exception as frame_exc:
                                self.last_error = (
                                    "JPEG EVF diterima tetapi gagal didekode/"
                                    f"ditampilkan: {frame_exc}"
                                )
                                dimensions = None

                            if dimensions and len(dimensions) == 2:
                                self.width = int(dimensions[0])
                                self.height = int(dimensions[1])
                                self.frames += 1
                                self.last_frame_at = time.time()
                                self.last_error = None
                                if self.frames == 1:
                                    self._progress(
                                        "evf_first_frame_delivered",
                                        f"Frame pertama berhasil dikirim ({self.width}x{self.height})."
                                    )
                        else:
                            self.non_jpeg_count += 1
                except Exception as exc:

                    message = str(exc)

                    if any(
                        f"0x{error_code:08X}" in message
                        for error_code in TRANSIENT_EVF_ERRORS
                    ):
                        self.last_error = None
                        time.sleep(0.08)

                    else:
                        self.last_error = message

                        if self.frames == 0:
                            time.sleep(0.15)
                        else:
                            time.sleep(0.25)

                finally:

                    if evf.value:
                        try:
                            self.dll.EdsRelease(evf)
                        except Exception:
                            pass

                    if stream.value:
                        try:
                            self.dll.EdsRelease(stream)
                        except Exception:
                            pass

                time.sleep(0.015)

        finally:
            if not self.running.is_set():
                self._cleanup_sdk()

    def take_picture(self):
        """Queue shutter work for execution by the EDSDK owner thread."""
        if not self.running.is_set() or not self.thread or not self.thread.is_alive():
            raise RuntimeError("Sesi Canon belum aktif.")
        completed = threading.Event()
        request = {"action": "capture", "event": completed, "result": None, "error": None}
        self.command_queue.put(request)
        if not completed.wait(12.0):
            raise RuntimeError("Perintah shutter Canon belum mendapat respons dari thread EDSDK.")
        if request["error"]:
            raise RuntimeError(request["error"])
        return request["result"]

    def _process_pending_commands(self):
        while self.running.is_set():
            try:
                request = self.command_queue.get_nowait()
            except queue.Empty:
                return
            try:
                if request.get("action") == "capture":
                    request["result"] = self._take_picture_on_owner_thread()
            except Exception as exc:
                request["error"] = str(exc)
            finally:
                event = request.get("event")
                if event is not None:
                    event.set()
                self.command_queue.task_done()

    def _take_picture_on_owner_thread(self):
        if not self.session_open or not self.camera.value:
            raise RuntimeError("Sesi Canon belum terbuka.")

        self._check(
            self.dll.EdsSendCommand(self.camera, CMD_PRESS_SHUTTER, SHUTTER_HALFWAY),
            "Tekan setengah shutter Canon",
        )
        time.sleep(0.08)
        try:
            self._check(
                self.dll.EdsSendCommand(self.camera, CMD_PRESS_SHUTTER, SHUTTER_COMPLETELY),
                "Tekan penuh shutter Canon",
            )
            time.sleep(0.15)
        finally:
            try:
                self.dll.EdsSendCommand(self.camera, CMD_PRESS_SHUTTER, SHUTTER_OFF)
            except Exception:
                pass

        return {
            "ok": True,
            "command": "PressShutterButton",
            "device": self.device_name,
            "note": (
                "Perintah shutter dikirim. Transfer JPEG resolusi penuh dari kamera "
                "ke folder sesi belum tersedia pada build ini."
            ),
        }

    def _cleanup_sdk(self):

        with self.cleanup_lock, SDK_LOCK:

            if self.cleaned:
                return

            self.cleaned = True

            if (
                self.dll
                and self.session_open
                and self.camera.value
            ):

                try:
                    output = ctypes.c_uint32(1)

                    self.dll.EdsSetPropertyData(
                        self.camera,
                        PROP_EVF_OUTPUT_DEVICE,
                        0,
                        ctypes.sizeof(output),
                        ctypes.byref(output)
                    )

                except Exception:
                    pass

                try:
                    self.dll.EdsCloseSession(self.camera)
                except Exception:
                    pass

            self.session_open = False

            if self.dll:

                for ref in (
                    self.camera,
                    self.camera_list
                ):

                    if ref.value:
                        try:
                            self.dll.EdsRelease(ref)
                        except Exception:
                            pass

                        ref.value = None

            if self.initialized and self.dll:

                try:
                    self.dll.EdsTerminateSDK()
                except Exception:
                    pass

            self.initialized = False

            set_live_camera(None)

            if self.dll_dir:

                try:
                    self.dll_dir.close()
                except Exception:
                    pass

                self.dll_dir = None

    def stop(self):
        """Stop the owner thread; SDK cleanup is performed by that thread."""
        self.running.clear()
        if self.thread and self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=8.0)
            if self.thread.is_alive():
                self.last_error = (
                    "Thread pemilik EDSDK masih menunggu respons native. "
                    "SDK tidak dilepas dari thread lain; worker terisolasi perlu dihentikan."
                )
                return False
        return True

    def status(self):

        return {
            "active": self.running.is_set(),
            "startup_error": self.startup_error,
            "thread_exception": self.thread_exception,
            "thread_exception_traceback": self.thread_exception_traceback,
            "sdk_owner_thread_id": self.thread.ident if self.thread else None,
            "sdk_owner_thread_alive": bool(self.thread and self.thread.is_alive()),
            "name": self.device_name,
            "frames": self.frames,
            "width": self.width,
            "height": self.height,
            "last_error": self.last_error,
            "last_frame_at": self.last_frame_at,
            "download_attempts": self.download_attempts,
            "download_error_counts": dict(self.download_error_counts),
            "event_error_counts": dict(self.event_error_counts),
            "empty_stream_count": self.empty_stream_count,
            "invalid_pointer_count": self.invalid_pointer_count,
            "non_jpeg_count": self.non_jpeg_count,
            "last_download_code": (
                f"0x{self.last_download_code:08X}"
                if self.last_download_code is not None else None
            ),
            "last_stream_length": self.last_stream_length,
            "last_payload_header": self.last_payload_header,
            "last_stage": self.last_stage,
            "download_call_pending": self.download_call_pending,
            "download_call_elapsed": self.download_call_elapsed,
            "last_download_return_at": self.last_download_return_at,
        }
