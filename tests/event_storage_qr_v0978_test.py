"""Offline regression: general/event archives, scoped Drive folders and session QR."""
import os, sys, tempfile, json
from pathlib import Path

with tempfile.TemporaryDirectory(prefix='kaca-event-qr-') as temp:
    os.environ['KACA_DATA_DIR'] = str(Path(temp) / 'data')
    os.environ['KACA_LOCAL_ARCHIVE_DIR'] = str(Path(temp) / 'KACA STUDIO')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    import camera_server as backend
    from google_drive import GoogleDriveManager

    e1='0123456789abcdef'; e2='fedcba9876543210'
    new=lambda sid, eid=None, name='': {
        'id':sid,'event_id':eid,'event_name':name,
        'created_at':'2026-11-09T17:00:00', 'status':'active','photos':[]}
    public = new('normal123456')
    wedding1 = new('wedding12345', e1, 'Wedding Aldi dan Diah')
    wedding2 = new('wedding67890', e1, 'Wedding Aldi dan Diah')
    birthday = new('birthday1234', e2, 'Birthday')
    for ss in [public,wedding1,wedding2,birthday]:
        backend.create_local_session_archive(ss)
        backend.write_manifest(ss)
        assert os.path.isdir(ss['local_archive_path'])
        assert os.path.isfile(os.path.join(ss['local_archive_path'],'Session_Info.json'))
    assert os.path.dirname(public['local_archive_path'])==backend.LOCAL_ARCHIVE_ROOT
    assert os.path.dirname(wedding1['local_archive_path'])==os.path.dirname(wedding2['local_archive_path'])
    assert wedding1['local_archive_path']!=wedding2['local_archive_path']
    assert os.path.dirname(wedding1['local_archive_path'])!=os.path.dirname(birthday['local_archive_path'])
    assert 'Events' + os.sep + 'Event_' + e1 in wedding1['local_archive_path']
    with open(os.path.join(os.path.dirname(wedding1['local_archive_path']), 'Event_Info.json'),encoding='utf-8') as f:
        assert json.load(f)['event_name']=='Wedding Aldi dan Diah'

    # Export one event photo at 1920x1080 with final JPG/Live Photo, and verify
    # that each asset is queued with the session ID for Google Drive upload.
    import cv2, numpy as np
    srcdir = Path(backend.SESSIONS_DIR) / wedding1['id']
    srcdir.mkdir(parents=True, exist_ok=True)
    sample=np.full((480,640,3),120,dtype=np.uint8)
    assert cv2.imwrite(str(srcdir/'photo_01.jpg'),sample)
    assert cv2.imwrite(str(srcdir/'output.jpg'),sample)
    (srcdir/'output_live.mp4').write_bytes(b'test-video-bytes')
    wedding1['photos']=[{'number':1,'original':'photo_01.jpg'}]
    backend.sync_local_session_archive(wedding1, final=True)
    folder=Path(wedding1['local_archive_path'])
    assert (folder/'Photos'/'Foto_01_Original.jpg').is_file()
    img=cv2.imread(str(folder/'Photos'/'Foto_01_Original.jpg'))
    assert img.shape[:2] == (1080,1920)
    assert (folder/'Final_Results'/'Hasil_Frame.jpg').is_file()
    assert (folder/'Live_Photos'/'Live_Photo_Frame.mp4').is_file()
    assert (folder/'KACA-ID-Hasil-Sesi.zip').is_file()
    upload_jobs=[v for v in backend.drive_jobs.values() if v.get('session_id')==wedding1['id'] and v.get('kind')=='asset']
    queued_paths={j['relative_path'] for j in upload_jobs}
    assert {'Photos/Foto_01_Original.jpg','Final_Results/Hasil_Frame.jpg','Live_Photos/Live_Photo_Frame.mp4'} <= queued_paths

    # A stubbed Drive manager validates folder isolation without OAuth/network.
    g=GoogleDriveManager(str(Path(temp)/'mock-drive'))
    paths={}; calls=[]
    def ensure(name, parent=None):
        calls.append((name,parent))
        key=(parent,name)
        if key not in paths: paths[key]='drivefolder'+str(len(paths)+1)
        return paths[key]
    g.ensure_root=lambda:'driveROOT'
    g.ensure_folder=ensure
    g._api=lambda method,path,payload=None,params=None: {'permissions':[]}
    p_general=g.create_session_folder('Sesi_001')
    p_wedding=g.create_session_folder('Sesi_001',event_id=e1)
    p_birthday=g.create_session_folder('Sesi_001',event_id=e2)
    assert len({p_general['folder_id'],p_wedding['folder_id'],p_birthday['folder_id']})==3
    assert ('Events','driveROOT') in calls
    assert ('Event_'+e1,paths[('driveROOT','Events')]) in calls
    assert ('Event_'+e2,paths[('driveROOT','Events')]) in calls
    assert p_general['url'].endswith(p_general['folder_id'])

    # The early Drive folder and QR must work for a wedding without waiting for rendering.
    orig_status=backend.google_drive.status
    orig_create=backend.google_drive.create_session_folder
    captured=[]
    backend.google_drive.status=lambda:{'connected':True}
    def mocked_create(folder_name,event_id=None):
        captured.append((folder_name,event_id))
        return {'folder_id':'unique-wedding-session',
                'url':'https://drive.google.com/drive/folders/unique-wedding-session',
                'share_warning':None}
    backend.google_drive.create_session_folder=mocked_create
    try:
        backend._prepare_session_drive_folder(wedding1['id'])
        session=backend.read_manifest(wedding1['id'])
        assert captured==[(os.path.basename(wedding1['local_archive_path']),e1)]
        assert session['drive_folder_status']=='ready'
        assert session['drive_qr_available']
        qr=os.path.join(wedding1['local_archive_path'],'Final_Results','QR_Google_Drive.png')
        assert os.path.isfile(qr)
        assert Path(qr).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        import cv2
        decoded,_,_=cv2.QRCodeDetector().detectAndDecode(cv2.imread(qr))
        assert decoded==session['drive_url'],(decoded,session['drive_url'])
        assert 'Event_'+e1 not in session['drive_url'], 'QR should point to per-session folder ID'
        assert not public.get('drive_url'), 'Unrelated general session cannot reuse event folder'
    finally:
        backend.google_drive.status=orig_status
        backend.google_drive.create_session_folder=orig_create

    # Standalone video upload is also event-scoped while default video remains unchanged.
    paths.clear(); calls.clear()
    demo_mp4=Path(temp)/'sample.mp4'; demo_mp4.write_bytes(b'fake-video-stream')
    g._upload_resumable=lambda path,parent:{'id':'uploaded-video','name':os.path.basename(path)}
    e_vid=g.upload_video(str(demo_mp4),'Video_ABC',event_id=e1)
    assert ('Event_'+e1, paths[('driveROOT','Events')]) in calls
    assert e_vid['folder_id']==paths[(paths[(paths[('driveROOT','Events')],'Event_'+e1)],'Video_ABC')]
    print('EVENT_LOCAL_DRIVE_QR_VIDEO_PASS')
