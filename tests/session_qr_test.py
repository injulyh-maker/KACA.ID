"""QR Code generation test for the early-created Google Drive session folder."""
import os, sys, tempfile, struct, zlib
from pathlib import Path

with tempfile.TemporaryDirectory(prefix='kaca-qr-test-') as temp:
    os.environ['KACA_DATA_DIR'] = os.path.join(temp, 'data')
    os.environ['KACA_LOCAL_ARCHIVE_DIR'] = os.path.join(temp, 'archive')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    import camera_server
    archive = os.path.join(temp, 'archive', 'Sesi_20261107_001')
    os.makedirs(os.path.join(archive, 'Final_Results'), exist_ok=True)
    url = 'https://drive.google.com/drive/folders/drive-folder-test-123'
    session = {'id':'qrtest123456', 'local_archive_path':archive, 'drive_url':url}
    qr_marker = camera_server._write_session_qr(session)
    assert qr_marker == os.path.join(camera_server.SESSIONS_DIR, 'qrtest123456', 'google_drive_qr.png')
    assert os.path.isfile(qr_marker), 'QR PNG was not persisted in the local session folder'
    assert os.path.isfile(os.path.join(archive, 'Final_Results', 'QR_Google_Drive.png')), 'QR archive copy must persist locally'
    png = camera_server._session_qr_png_bytes(session)
    assert png and png[:8] == b'\x89PNG\r\n\x1a\n', 'In-memory QR output is not a PNG'
    # Validate PNG structure and decoded grayscale pixels without importing Pillow.
    offset = 8; chunks = []; width = height = None
    while offset < len(png):
        length = struct.unpack('!I', png[offset:offset+4])[0]
        kind = png[offset+4:offset+8]
        payload = png[offset+8:offset+8+length]
        crc = struct.unpack('!I', png[offset+8+length:offset+12+length])[0]
        assert crc == (zlib.crc32(kind + payload) & 0xffffffff)
        if kind == b'IHDR':
            width, height, bit_depth, color_type, *_ = struct.unpack('!IIBBBBB', payload)
            assert bit_depth == 8 and color_type == 0
        elif kind == b'IDAT': chunks.append(payload)
        offset += 12 + length
        if kind == b'IEND': break
    assert width >= 200 and height >= 200
    pixels = zlib.decompress(b''.join(chunks))
    assert min(pixels) == 0 and max(pixels) == 255
    import qrcode
    matrix = qrcode.QRCode(box_size=10, border=4)
    matrix.add_data(url); matrix.make(fit=True)
    assert matrix.get_matrix() and len(matrix.get_matrix()) >= 21

    # Simulate the session-start Drive provisioning path without contacting Google.
    session_id = 'provisiontest12'
    manifest = {'id':session_id,'status':'active','local_archive_path':archive,'created_at':'2026-11-07T00:00:00'}
    camera_server.write_manifest(manifest)
    original_status = camera_server.google_drive.status
    original_create = camera_server.google_drive.create_session_folder
    camera_server.google_drive.status = lambda: {'connected':True}
    camera_server.google_drive.create_session_folder = lambda name: {
        'folder_id':'early-folder-id','url':'https://drive.google.com/drive/folders/early-folder-id',
        'share_warning':None,'subfolders':{'Photos':'p','Live_Photos':'l','Final_Results':'f','Video_Results':'v'}}
    try:
        camera_server._prepare_session_drive_folder(session_id)
        saved = camera_server.read_manifest(session_id)
        assert saved['drive_folder_status'] == 'ready'
        assert saved['drive_url'].endswith('/early-folder-id')
        assert saved['drive_qr_available'] is True
        assert saved.get('drive_qr_path') and os.path.isfile(saved['drive_qr_path'])
        assert os.path.isfile(os.path.join(archive, 'Final_Results', 'QR_Google_Drive.png')), 'QR archive copy must persist locally'
    finally:
        camera_server.google_drive.status = original_status
        camera_server.google_drive.create_session_folder = original_create

    # QR is display-only and is not composited into the printable customer photo.
    assert '_blend_drive_qr(canvas,session)' not in open(camera_server.__file__, encoding='utf-8').read()
    print('Google Drive early folder provisioning + locally persisted display-only QR: PASS (mock API)')
