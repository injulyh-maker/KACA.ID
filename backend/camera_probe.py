"""Isolated webcam driver probe. Launched only by camera_server.py."""
import json, sys

def main():
    index=int(sys.argv[1]); name=sys.argv[2]
    if not (0<=index<=10 and name in ('DirectShow','MSMF')):return 2
    import cv2
    api=cv2.CAP_DSHOW if name=='DirectShow' else cv2.CAP_MSMF
    capture=None
    try:
        capture=cv2.VideoCapture(index,api)
        if capture is None or not capture.isOpened():return 3
        # Do not change resolution when probing: unsupported mode changes may
        # trigger native driver resets and make the active camera unusable.
        ok,frame=capture.read()
        if not ok or frame is None or not getattr(frame,'size',0):return 4
        print('KACA_PROBE_RESULT='+json.dumps({'ok':True,'index':index,'backend':name,
            'width':int(frame.shape[1]),'height':int(frame.shape[0])}),flush=True)
        return 0
    finally:
        if capture is not None:capture.release()
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('KACA_PROBE_ERROR='+repr(exc),flush=True);sys.exit(5)
