KACA.ID v0.9.18 - Canon worker final status Pipe drain fix

Install with KACA.ID and backend fully closed. Extract this ZIP into the project root and overwrite the two files.

Changes:
- Status reader allows a 2-second drain grace after worker process exit instead of immediately abandoning the Pipe when Process.is_alive() turns false.
- Exposes worker_exit_reason and falls back to the final worker_exit detail in the diagnostic UI.
- No changes to EDSDK camera commands, frame acquisition, or capture behavior.

Validation performed: Python syntax compilation for the patched backend module and related worker/native modules; JavaScript syntax checked separately when Node.js is available. Hardware behavior still requires testing with the EOS camera.
