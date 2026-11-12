"""Isolated QR integration regression: uses the QR composite functions from camera_server source, without starting the server."""
import ast, hashlib, json, os, re, shutil, tempfile, unittest
from pathlib import Path
import numpy as np
import cv2

SERVER=Path(__file__).resolve().parents[1]/'camera_server.py'
module=ast.parse(SERVER.read_text(encoding='utf8'),str(SERVER))
names={'_blend_drive_qr','_refresh_drive_qr_output'}
functions=[node for node in module.body if isinstance(node,ast.FunctionDef) and node.name in names]
assert len(functions)==2
class QRTests(unittest.TestCase):
    def test_print_qr_in_saved_position_and_late_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessions=Path(tmp)/'sessions';frames=Path(tmp)/'frames'
            sid='qr-session-012345';folder=sessions/sid;folder.mkdir(parents=True);frames.mkdir()
            source=np.full((900,600,3),140,dtype=np.uint8)
            assert cv2.imwrite(str(folder/'output.jpg'),source)
            archive=Path(tmp)/'customer';archive.mkdir()
            env={'__builtins__':__builtins__,'cv2':cv2,'os':os,'re':re,'json':json,
                 'hashlib':hashlib,'shutil':shutil,'SESSIONS_DIR':str(sessions),'FRAMES_DIR':str(frames)}
            exec(compile(ast.Module(body=functions,type_ignores=[]),str(SERVER),'exec'),env)
            manifest={'id':sid,'drive_qr_enabled':True,'drive_url':'https://drive.google.com/drive/folders/TEST012345',
                      'drive_qr_layout':{'x':.1,'y':.2,'w':.2,'h':.2},
                      'local_archive_path':str(archive)}
            self.assertTrue(env['_refresh_drive_qr_output'](manifest))
            output=cv2.imread(str(folder/'output_print_qr.jpg'))
            self.assertIsNotNone(output)
            self.assertTrue((archive/'Final_Results'/'Hasil_Frame_Dengan_QR.jpg').is_file())
            # The QR belongs to x=.1..3 and y=.2..4, not a forced 200px area.
            difference=np.max(abs(output.astype(np.int16)-source.astype(np.int16)),axis=2)
            self.assertGreater(int(np.count_nonzero(difference[190:330,65:180])),100)
            self.assertLess(int(np.count_nonzero(difference[:100, :])),10)
            self.assertLess(int(np.count_nonzero(difference[:, 350:])),10)
            self.assertTrue(manifest['print_qr_ready'])
if __name__=='__main__':unittest.main()
