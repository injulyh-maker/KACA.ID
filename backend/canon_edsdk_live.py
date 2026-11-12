"""Process-isolated Canon EDSDK Live View wrapper for KACA.ID."""
from __future__ import annotations
import multiprocessing
import threading
import time
import uuid

class CanonLiveView:
    def __init__(self, on_frame, camera_index=0):
        self.on_frame = on_frame
        self.camera_index = int(camera_index)
        self.ctx = multiprocessing.get_context("spawn")
        self.process = None
        self.frame_receiver = None
        self.status_receiver = None
        self.command_sender = None
        self.reader_thread = None
        self.frame_thread = None
        self.lock = threading.RLock()
        self.active = False
        self.frames = 0
        self.width = 0
        self.height = 0
        self.device_name = "Canon EOS"
        self.last_error = None
        self.last_frame_at = None
        self.startup_stage = "not_started"
        self.startup_detail = "Worker belum dijalankan."
        self._capture_results = {}
        self._capture_events = {}
        self._stop_requested = False
        self.native_diagnostics = {}
        self.last_worker_heartbeat_at = None
        self.last_worker_time = None
        self.frame_reader_stopped_at = None
        self.worker_exit_info = None
        self.worker_exit_reason = None

    def _terminate_worker(self):
        p = self.process
        if p is not None:
            try:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=3)
                if p.is_alive() and hasattr(p, "kill"):
                    p.kill()
                    p.join(timeout=2)
            except Exception:
                pass
        self.active = False

    def _read_frames(self):
        while self.process is not None and self.process.is_alive():
            try:
                if self.frame_receiver.poll(0.2):
                    payload = self.frame_receiver.recv_bytes()
                    dimensions = self.on_frame(payload)
                    if dimensions and len(dimensions) == 2:
                        self.width, self.height = int(dimensions[0]), int(dimensions[1])
                    self.frames += 1
                    self.last_frame_at = time.time()
            except (EOFError, OSError):
                break
            except Exception as exc:
                self.last_error = "Gagal meneruskan frame Canon: " + str(exc)
        self.active = False
        self.frame_reader_stopped_at = time.time()

    def _read_status(self):
        # Drain final worker messages after process exit. A short grace window
        # avoids racing Process.is_alive() against delivery of the final Pipe data.
        process_exit_seen_at = None
        while True:
            try:
                if not self.status_receiver.poll(0.2):
                    process_alive = bool(self.process is not None and self.process.is_alive())
                    if process_alive:
                        process_exit_seen_at = None
                        continue
                    if process_exit_seen_at is None:
                        process_exit_seen_at = time.monotonic()
                    # The sender closes its endpoint in worker finally. Keep
                    # polling briefly so the final worker_exit/error message
                    # can arrive before the reader gives up.
                    if time.monotonic() - process_exit_seen_at < 2.0:
                        continue
                    break
                msg = self.status_receiver.recv()
                kind = msg.get("type")
                if kind == "progress":
                    self.startup_stage = msg.get("stage", self.startup_stage)
                    self.startup_detail = msg.get("detail", self.startup_detail)
                elif kind == "heartbeat":
                    self.last_worker_heartbeat_at = time.time()
                    self.last_worker_time = msg.get("worker_time")
                    if isinstance(msg.get("native"), dict):
                        self.native_diagnostics = msg["native"]
                    if msg.get("diagnostic_error"):
                        self.native_diagnostics = {"diagnostic_error": msg["diagnostic_error"]}
                elif kind == "capture_result":
                    rid = msg.get("request_id")
                    self._capture_results[rid] = msg
                    event = self._capture_events.get(rid)
                    if event:
                        event.set()
                elif kind == "error":
                    self.last_error = msg.get("error") or "Worker Canon mengalami kesalahan."
                    self.startup_stage = "error"
                    self.startup_detail = self.last_error
                    self._worker_traceback = msg.get("traceback")
                elif kind == "stop_result":
                    self._stop_result = msg
                elif kind == "worker_exit":
                    self.worker_exit_info = dict(msg)
                    self.worker_exit_reason = msg.get("reason") or msg.get("detail") or "worker_exit_received_without_reason"
                    self.startup_stage = "worker_exit"
                    self.startup_detail = msg.get("detail", "")
                    if isinstance(msg.get("native"), dict):
                        self.native_diagnostics = msg["native"]
                    if msg.get("thread_exception"):
                        self.last_error = "Thread EDSDK berhenti: " + str(msg.get("thread_exception"))
            except (EOFError, OSError):
                break
            except Exception as exc:
                self.last_error = "Pembacaan status worker gagal: " + str(exc)
                break

    def start(self):
        with self.lock:
            if self.process is not None and self.process.is_alive():
                raise RuntimeError("Worker Canon sebelumnya masih berjalan.")
            self.frames = 0
            self.width = self.height = 0
            self.last_error = None
            self.native_diagnostics = {}
            self.last_worker_heartbeat_at = None
            self.last_worker_time = None
            self.frame_reader_stopped_at = None
            self.worker_exit_info = None
            self.worker_exit_reason = None
            self.startup_stage = "starting"
            self.startup_detail = "Menyiapkan proses Canon worker."
            self._worker_traceback = None
            self._stop_result = None

            frame_recv, frame_send = self.ctx.Pipe(duplex=False)
            status_recv, status_send = self.ctx.Pipe(duplex=False)
            # Pipe(duplex=False) returns (receive_end, send_end).
            # The parent sends commands; the worker receives them.
            command_recv, command_send = self.ctx.Pipe(duplex=False)
            from canon_edsdk_worker import run_worker
            self.frame_receiver = frame_recv
            self.status_receiver = status_recv
            self.command_sender = command_send
            self.process = self.ctx.Process(
                target=run_worker,
                args=(self.camera_index, frame_send, status_send, command_recv),
                name="KACA-Canon-EDSDK-Worker",
                daemon=True
            )
            self.process.start()
            frame_send.close()
            status_send.close()
            command_recv.close()

            # IMPORTANT: drain the frame pipe before waiting for the worker's
            # "started" message. The worker's native controller waits for its
            # first frame callback to return; a large send_bytes() can block if
            # the parent has not started reading yet. Starting the reader only
            # after "started" creates a startup deadlock.
            if self.frame_thread and self.frame_thread.is_alive():
                self.frame_thread.join(timeout=1.0)
                if self.frame_thread.is_alive():
                    self._terminate_worker()
                    raise RuntimeError(
                        "Pembaca frame Canon dari percobaan sebelumnya masih berjalan."
                    )
            self.frame_thread = threading.Thread(
                target=self._read_frames,
                name="KACA-Canon-Frame-Reader",
                daemon=True,
            )
            self.frame_thread.start()

            deadline = time.monotonic() + 24.0
            startup_message = None
            while time.monotonic() < deadline:
                if self.status_receiver.poll(0.2):
                    try:
                        msg = self.status_receiver.recv()
                    except (EOFError, OSError):
                        break
                    kind = msg.get("type")
                    if kind == "progress":
                        self.startup_stage = msg.get("stage", self.startup_stage)
                        self.startup_detail = msg.get("detail", self.startup_detail)
                        continue
                    if kind in ("started", "error"):
                        startup_message = msg
                        break
                    # Preserve asynchronous messages if any arrive before startup.
                if self.process is not None and not self.process.is_alive():
                    break

            if startup_message and startup_message.get("type") == "error":
                self.last_error = startup_message.get("error")
                trace = startup_message.get("traceback", "")
                self._terminate_worker()
                detail = self.last_error or "Kesalahan worker Canon."
                if trace:
                    detail += "\n" + trace[-1800:]
                raise RuntimeError(detail)

            if not startup_message or startup_message.get("type") != "started":
                p = self.process
                exitcode = getattr(p, "exitcode", None) if p else None
                alive = bool(p and p.is_alive())
                stage = self.startup_stage
                detail = self.startup_detail
                self._terminate_worker()
                raise RuntimeError(
                    "Worker Canon tidak menyelesaikan startup dalam 24 detik. "
                    f"Tahap terakhir: {stage}. {detail} "
                    f"PID={getattr(p, 'pid', None)}, exitcode={exitcode}, alive={alive}. "
                    "Jika tahap terakhir native_start, kemungkinan proses tertahan di pemanggilan native EDSDK."
                )

            result = startup_message.get("result") or {}
            self.device_name = result.get("name") or self.device_name
            self.width = int(result.get("width") or 0)
            self.height = int(result.get("height") or 0)
            self.active = True
            self.startup_stage = "started"
            self.startup_detail = "Canon worker berhasil membuka Live View."
            # Frame reader is already running from before the startup wait.
            self.reader_thread = threading.Thread(
                target=self._read_status,
                name="KACA-Canon-Status-Reader",
                daemon=True,
            )
            self.reader_thread.start()
            return result

    def take_picture(self):
        if not self.active or not self.command_sender:
            raise RuntimeError("Sesi Canon belum aktif.")
        rid = uuid.uuid4().hex
        event = threading.Event()
        self._capture_events[rid] = event
        self.command_sender.send({"action": "capture", "request_id": rid})
        if not event.wait(15):
            self._capture_events.pop(rid, None)
            raise RuntimeError("Worker Canon tidak mengirim hasil perintah shutter dalam 15 detik.")
        msg = self._capture_results.pop(rid, {})
        self._capture_events.pop(rid, None)
        if msg.get("error"):
            raise RuntimeError(msg["error"])
        return msg.get("result") or {"ok": True, "command": "PressShutterButton"}

    def stop(self):
        with self.lock:
            p = self.process
            if p is None:
                self.active = False
                return True
            try:
                if p.is_alive() and self.command_sender:
                    self.command_sender.send({"action": "stop"})
                    p.join(timeout=3)
            except Exception:
                pass
            self._terminate_worker()
            for conn in (self.frame_receiver, self.status_receiver, self.command_sender):
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
            self.active = False
            return True

    def status(self):
        p = self.process
        return {
            "active": bool(self.active and p and p.is_alive()),
            "name": self.device_name,
            "frames": self.frames,
            "width": self.width,
            "height": self.height,
            "last_error": self.last_error,
            "worker_traceback": getattr(self, "_worker_traceback", None),
            "last_frame_at": self.last_frame_at,
            "startup_stage": self.startup_stage,
            "startup_detail": self.startup_detail,
            "worker_pid": getattr(p, "pid", None) if p else None,
            "worker_alive": bool(p and p.is_alive()),
            # Exit code is essential to distinguish a normal worker exit from
            # a native EDSDK/DLL crash (for example, a Windows exception code).
            "worker_exitcode": getattr(p, "exitcode", None) if p else None,
            "worker_exit_info": dict(self.worker_exit_info) if self.worker_exit_info else None,
            "worker_exit_reason": self.worker_exit_reason,
            "frame_reader_alive": bool(self.frame_thread and self.frame_thread.is_alive()),
            "status_reader_alive": bool(self.reader_thread and self.reader_thread.is_alive()),
            "last_worker_heartbeat_at": self.last_worker_heartbeat_at,
            "worker_heartbeat_age_ms": (
                round((time.time() - self.last_worker_heartbeat_at) * 1000)
                if self.last_worker_heartbeat_at else None
            ),
            "native": dict(self.native_diagnostics),
        }
