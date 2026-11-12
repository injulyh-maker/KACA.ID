"""Isolated Canon EDSDK worker for KACA.ID. Reports startup progress."""
from __future__ import annotations
import multiprocessing
import traceback
import time

def run_worker(camera_index, frame_sender, status_sender, command_receiver):
    controller = None
    def report(kind, **data):
        try:
            status_sender.send({"type": kind, **data})
        except Exception:
            pass

    report("progress", stage="worker_boot", detail="Proses Canon worker mulai berjalan.")
    try:
        report("progress", stage="import_native", detail="Memuat modul canon_edsdk_native.")
        from canon_edsdk_native import CanonLiveView as NativeCanonLiveView

        def forward_frame(payload):
            try:
                frame_sender.send_bytes(payload)
                return (1, 1)
            except Exception as exc:
                raise RuntimeError(
                    "Pengiriman frame Canon melalui Pipe gagal: " + str(exc)
                ) from exc

        report("progress", stage="create_controller", detail="Membuat controller EDSDK.")
        controller = NativeCanonLiveView(on_frame=forward_frame, camera_index=int(camera_index))

        report("progress", stage="native_start", detail="Menjalankan NativeCanonLiveView.start(); proses dapat menunggu respons native EDSDK.")
        result = controller.start()
        report("started", result=result)

        last_heartbeat = 0.0
        exit_reason = "loop_ended_without_reason"
        while True:
            now = time.monotonic()
            if now - last_heartbeat >= 1.0:
                try:
                    native_status = controller.status()
                    report("heartbeat", worker_time=now, native=native_status)
                except Exception as diag_exc:
                    report("heartbeat", worker_time=now, diagnostic_error=str(diag_exc))
                last_heartbeat = now
            if command_receiver.poll(0.05):
                try:
                    command = command_receiver.recv()
                except EOFError:
                    exit_reason = "command_pipe_eof"
                    break
                action = command.get("action")
                if action == "capture":
                    try:
                        value = controller.take_picture()
                        report("capture_result", request_id=command.get("request_id"), result=value)
                    except Exception as exc:
                        report("capture_result", request_id=command.get("request_id"), error=str(exc))
                elif action == "stop":
                    exit_reason = "stop_command_received"
                    report("progress", stage="stopping_native", detail="Meminta controller Canon berhenti.")
                    try:
                        stopped = controller.stop()
                    except Exception as exc:
                        report("stop_result", stopped=False, error=str(exc))
                        break
                    report("stop_result", stopped=bool(stopped))
                    break
            if not controller.running.is_set():
                exit_reason = "native_running_event_cleared"
                break
        try:
            final_native = controller.status()
        except Exception as final_exc:
            final_native = {"diagnostic_error": str(final_exc)}
        report(
            "worker_exit",
            detail="Loop worker selesai.",
            reason=exit_reason,
            native=final_native,
            startup_error=getattr(controller, "startup_error", None),
            thread_exception=getattr(controller, "thread_exception", None),
            thread_exception_traceback=getattr(controller, "thread_exception_traceback", None),
        )
    except BaseException as exc:
        report("error", error=str(exc), traceback=traceback.format_exc())
    finally:
        try:
            frame_sender.close()
            status_sender.close()
            command_receiver.close()
        except Exception:
            pass
