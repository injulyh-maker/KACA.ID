"""Shared EDSDK lifecycle coordination for KACA.ID.

EDSDK is process-global: enumeration must not initialize/terminate it while a
Canon Live View session is using it. All lifecycle transitions are serialized.
"""
import threading

SDK_LOCK = threading.RLock()
_live_camera = None

def set_live_camera(camera):
    global _live_camera
    with SDK_LOCK:
        _live_camera = dict(camera) if camera else None

def get_live_camera():
    with SDK_LOCK:
        return dict(_live_camera) if _live_camera else None
