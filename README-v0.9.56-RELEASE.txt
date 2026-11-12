KACA.ID v0.9.56 — CAMERA ORIENTATION, PREVIEW CONTROLS & FILTER FIT

Included changes:
- Reduced the filter-result canvas display size to keep it inside its preview column.
- Added camera rotation (0/90/180/270), horizontal flip and vertical flip.
- Applied orientation consistently to the capture preview, saved still image, and Live Photo recording.
- Added preview-only JPEG quality, display brightness, and stream FPS controls.
- Preview settings are isolated from capture settings and saved still files.
- Saved still JPEG quality now follows the configured capture quality, with new default 100; no additional downscaling is performed by the save path.
- Google Drive uploads the session's local files; it does not separately recompress them.

Important Canon DSLR limitation:
The current EDSDK implementation sends the shutter command but does not yet implement transfer of the camera's native full-resolution JPEG/RAW file to the session folder. Canon still photos therefore still originate from the Live View frame. JPEG quality 100 does not make that Live View frame equivalent to the camera's native still file and JPEG is still a lossy format. A separate EDSDK object-event/file-transfer implementation is required before KACA.ID can guarantee that saved files match the camera's native resolution and image-quality settings exactly. This limitation is stated rather than hidden.

Verification:
- 23 project test scripts passed when run individually.
- JavaScript syntax checks passed for shipping and mirrored UI copies.
- Python compilation passed for camera server and Canon EDSDK modules.
- ZIP integrity verified after packaging.
- Physical Canon/webcam/printer and live Google Drive upload tests were not performed in this environment.

Build on Windows:
1. Extract the full source archive to a new folder.
2. Run setup.bat.
3. Run npm.cmd run dist:win.
4. Test the resulting installer and camera behavior on the actual booth PC before deployment.
