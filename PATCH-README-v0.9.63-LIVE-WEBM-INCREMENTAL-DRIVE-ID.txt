KACA.ID v0.9.63 - LIVE WEBM LOCAL PREVIEW + INCREMENTAL GOOGLE DRIVE UPLOAD

PATCH CONTENTS
- backend/camera_server.py
- backend/google_drive.py
- src/app.js
- tests/live_webm_and_incremental_drive_v0963_test.py
- updated tests/result_originals_unfiltered_v0963_test.py

CHANGES
1. Keep output_live.webm in the local session folder and copy it to:
   Live_Photos/Live_Photo_Frame.webm
2. Do not upload any .webm file to Google Drive. MP4 remains the Drive master.
3. Do not delete the final output_live.webm when leaving the customer result slide.
   Per-shot temporary WebM previews are still cleaned up.
4. Upload each original JPG to Google Drive as soon as its local archive copy exists.
5. Upload final JPG, MP4 Live Photo, and GIF individually as soon as each local archive copy exists.
6. Create/use the Drive session folder and its standard subfolders before asset uploads.
7. Keep QR generated in memory from the Drive folder URL; no QR image is saved to local or Drive.
8. Merge Drive folder metadata into the render manifest before committing, preventing an old render snapshot
   from erasing a Drive URL that was created asynchronously.
9. Output session detail prefers WebM preview and falls back to MP4.

INSTALL
1. Close KACA.ID completely.
2. Back up src and backend folders.
3. Extract this patch into the application root (the folder containing main.js and run-kaca-id.bat).
4. Allow files to be replaced.
5. Run run-kaca-id.bat.
6. Test using a NEW session. Existing sessions may have been created without a saved final WebM preview.

VALIDATION
- node --check src/app.js
- python -m py_compile backend/camera_server.py backend/google_drive.py
- session QR, result reliability, render worker, Google Drive mock, original-unfiltered,
  live-photo preview, and incremental-upload regression scripts passed in this environment.
- No live Google Drive account or the user's Windows camera/printer was exercised.
