KACA.ID Canon EDSDK command-pipe correction — v0.9.18

Files to replace:
  backend/canon_edsdk_live.py
  src/app.js

Root cause found in the supplied project:
  multiprocessing.Pipe(duplex=False) returns (receive_end, send_end).
  The command pipe was assigned in the reverse order. The parent therefore
  held the receive-only endpoint while trying to send capture/stop commands,
  and the worker held the send-only endpoint while polling/receiving commands.
  This breaks the worker command channel and can cause an exception before
  the normal worker_exit message is reported.

Changes:
  1. Correct command pipe endpoint order: command_recv, command_send.
  2. Expose worker traceback in CanonLiveView.status().
  3. Include worker last_error and traceback in the CANON DIAG UI log.

No camera settings, EDSDK DLLs, capture protocol, or EVF properties are changed.

Validation performed in the build environment:
  - Python syntax compilation for canon_edsdk_live.py, canon_edsdk_worker.py,
    canon_edsdk_native.py, and camera_server.py.
  - Node syntax check for src/app.js.
  - Spawn-process integration test using a fake Canon controller:
      * worker startup and first-frame pipe delivery
      * capture command parent -> worker
      * stop command parent -> worker
      * worker_exit reason/native status delivered back to parent
      * clean exitcode 0

Hardware limitation:
  This environment cannot connect to or validate a physical Canon EOS 1300D.
  After applying this patch, test continuous Live View and shutter on the camera.
