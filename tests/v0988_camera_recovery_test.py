"""Regression: recovery does not repeat a corrupted initial zero value."""
import os,sys,tempfile
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    os.environ['KACA_DATA_DIR']=temp
    spec=importlib.util.spec_from_file_location('kaca_camera_backend_0988',ROOT/'backend/camera_server.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cv2=module.cv2
    class Webcam:
        def __init__(self):
            self.values={cv2.CAP_PROP_BRIGHTNESS:0.0,cv2.CAP_PROP_SATURATION:0.0,
                         cv2.CAP_PROP_CONTRAST:100.0,cv2.CAP_PROP_GAIN:70.0,
                         cv2.CAP_PROP_EXPOSURE:-6.0}
            self.calls=[];self.blocked=set()
        def isOpened(self):return True
        def get(self,prop):return self.values.get(prop,0.0)
        def set(self,prop,val):
            self.calls.append((prop,val))
            if prop in self.blocked:return False
            self.values[prop]=float(val);return True
    mock=Webcam()
    module.cap=mock
    capabilities=module.get_camera_control_capabilities(0)
    assert capabilities['open'] and capabilities['controls']['brightness']['actual']==0
    result=module.recover_camera_controls(0)
    assert result['ok'] and result['source']=='safe_neutral', result
    assert mock.values[cv2.CAP_PROP_BRIGHTNESS]==50.0
    assert mock.values[cv2.CAP_PROP_SATURATION]==50.0
    assert not any(prop in (cv2.CAP_PROP_EXPOSURE,cv2.CAP_PROP_GAIN) for prop,_ in mock.calls)
    print('RECOVER_FROM_DARK_PASS: brightness/saturation 0 -> 50, exposure/gain unchanged')
    profile={'brightness':64,'saturation':66,'gain':40}
    result=module.recover_camera_controls(0,profile)
    assert result['source']=='saved_profile',result
    assert mock.values[cv2.CAP_PROP_BRIGHTNESS]==64.0
    assert mock.values[cv2.CAP_PROP_SATURATION]==66.0
    assert mock.values[cv2.CAP_PROP_GAIN]==40.0
    print('USER_SAVED_PROFILE_PASS')
    mock.blocked.add(cv2.CAP_PROP_SATURATION)
    result=module.recover_camera_controls(0,keys=['saturation'])
    assert not result['controls']['saturation']['applied'],result
    assert mock.values[cv2.CAP_PROP_SATURATION]==66.0
    print('REJECTED_DRIVER_NOT_REPORTED_SUCCESS_PASS')
