KACA.ID v0.9.49 — CAMERA BACKEND, FRAME PICKER, RESULT PREVIEW & FASTER RESULT

Changes:
- Reuses a healthy KACA camera backend already listening on 127.0.0.1:8765 rather than spawning a duplicate process and rejecting its PID. A reused backend is not terminated when this Electron window closes.
- Customer frame selection shows only active PNG frame images. The "Tanpa frame PNG" choice and frame-name/metadata labels are removed. If no active PNG frame exists, the customer cannot continue until an operator adds/enables one.
- Result preview is constrained to its preview column and uses object-fit: contain to prevent clipping.
- Filter-to-result transition waits for the final still JPG, not the slower Live Photo render. Live Photo continues in the background and appears when ready.
- Google Drive folder/QR provisioning remains independent from file upload. The QR is displayed once Drive folder creation and QR generation have completed, even while assets are still uploading.

Important:
- A valid Google Drive OAuth connection is required to create a real folder URL and QR. An OAuth error such as invalid_client cannot produce a valid Drive QR until the configured client secret is corrected.
- The existing KACA backend on port 8765 is reused only when /health reports ok=true and a loaded OpenCV version. This avoids PID mismatch loops for a healthy KACA backend.
- Automated regression tests passed. Physical webcam/Canon DSLR verification and Windows installer build still need to be performed on the target PC.

Build:
  setup.bat
  npm.cmd install
  npm.cmd run dist:win
