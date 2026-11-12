"""Print QR should be in a separate JPG, scannable, while digital photo stays pristine."""
import os, sys, tempfile, hashlib, importlib
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import camera_server as cs

def test_printable_qr():
    with tempfile.TemporaryDirectory(prefix='kaca-qr-print-') as td:
        old=cs.SESSIONS_DIR
        cs.SESSIONS_DIR=td
        try:
            sid='aabbccddeeff';folder=Path(td)/sid;folder.mkdir()
            src=folder/'output.jpg'
            output=np.full((1800,1200,3),(205,225,245),np.uint8)
            cv2.putText(output,'ORIGINAL DIGITAL',(80,340),cv2.FONT_HERSHEY_SIMPLEX,1.8,(80,80,80),3)
            assert cv2.imwrite(str(src),output)
            original_hash=hashlib.sha256(src.read_bytes()).hexdigest()
            url='https://drive.google.com/drive/folders/realistic-kaca-folder-123456'
            session={'id':sid,'drive_qr_enabled':True,'drive_url':url,
                     'drive_qr_layout':{'x':.7,'y':.72,'w':.22,'h':.22}}
            assert cs._refresh_drive_qr_output(session)
            dst=folder/'output_print_qr.jpg'
            assert dst.is_file()
            assert original_hash==hashlib.sha256(src.read_bytes()).hexdigest(),'digital JPG overwritten by print QR!'
            printed=cv2.imread(str(dst))
            data,points,_=cv2.QRCodeDetector().detectAndDecode(printed)
            assert data==url,(data,url)
            assert points is not None
            meta_before=dst.stat().st_mtime_ns
            assert cs._refresh_drive_qr_output(session)
            assert dst.stat().st_mtime_ns==meta_before,'print-ready regenerated without changes'
            session['drive_url']=''
            assert not cs._refresh_drive_qr_output(session)
            print('PASS print-only QR decoded from JPG; source original intact; re-render idempotent')
        finally:
            cs.SESSIONS_DIR=old

if __name__=='__main__':test_printable_qr()
