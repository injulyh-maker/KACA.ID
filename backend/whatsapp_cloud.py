"""WhatsApp Business Cloud API integration for KACA.ID (stdlib only)."""
import json, os, re, time, urllib.request, urllib.error

GRAPH_ROOT = 'https://graph.facebook.com'
DEFAULT_API_VERSION = 'v26.0'


def normalize_whatsapp_number(value):
    digits = re.sub(r'\D', '', str(value or ''))
    if digits.startswith('00'): digits = digits[2:]
    if digits.startswith('0'): digits = '62' + digits[1:]
    elif digits.startswith('8'): digits = '62' + digits
    if not re.fullmatch(r'[1-9]\d{7,14}', digits):
        raise ValueError('Nomor WhatsApp tidak valid. Gunakan nomor aktif dengan kode negara, misalnya 62812xxxxxxx.')
    return digits

class WhatsAppCloudManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.config_path = os.path.join(data_dir, 'whatsapp-cloud-config.json')

    def _read(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data):
        tmp = self.config_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.config_path)

    def configure(self, data):
        old = self._read()
        phone_id = str(data.get('phone_number_id') or '').strip()
        token = str(data.get('access_token') or '').strip() or old.get('access_token', '')
        template = str(data.get('template_name') or 'kaca_hasil_photobooth').strip()
        language = str(data.get('language') or 'id').strip()
        version = str(data.get('api_version') or DEFAULT_API_VERSION).strip()
        if phone_id and not re.fullmatch(r'\d{5,30}', phone_id):
            raise ValueError('Phone Number ID harus berupa angka dari Meta.')
        if token and len(token) < 20:
            raise ValueError('Access Token tampaknya tidak valid.')
        if not re.fullmatch(r'[a-z0-9_]{3,100}', template):
            raise ValueError('Nama template hanya boleh huruf kecil, angka, dan garis bawah.')
        if not re.fullmatch(r'[a-z]{2}(?:_[A-Z]{2})?', language):
            raise ValueError('Kode bahasa tidak valid, contoh: id atau en_US.')
        if not re.fullmatch(r'v\d+\.0', version):
            raise ValueError('Versi Graph API harus berformat vNN.0, contoh v26.0.')
        if not phone_id or not token:
            raise ValueError('Phone Number ID dan Access Token wajib diisi.')
        cfg = {'phone_number_id': phone_id, 'access_token': token, 'template_name': template,
               'language': language, 'api_version': version, 'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        self._write(cfg)
        return self.status()

    def status(self):
        cfg = self._read()
        return {'configured': bool(cfg.get('phone_number_id') and cfg.get('access_token')),
                'phone_number_id': cfg.get('phone_number_id', ''),
                'template_name': cfg.get('template_name', 'kaca_hasil_photobooth'),
                'language': cfg.get('language', 'id'),
                'api_version': cfg.get('api_version', DEFAULT_API_VERSION),
                'token_saved': bool(cfg.get('access_token'))}

    def send_result_template(self, recipient, drive_url, session_id):
        cfg = self._read()
        if not cfg.get('phone_number_id') or not cfg.get('access_token'):
            raise RuntimeError('WhatsApp Cloud API belum dikonfigurasi.')
        version = cfg.get('api_version', DEFAULT_API_VERSION)
        url = f"{GRAPH_ROOT}/{version}/{cfg['phone_number_id']}/messages"
        body = {
            'messaging_product': 'whatsapp', 'recipient_type': 'individual',
            'to': recipient, 'type': 'template',
            'template': {
                'name': cfg.get('template_name', 'kaca_hasil_photobooth'),
                'language': {'code': cfg.get('language', 'id')},
                'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': drive_url}]}]
            }
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + cfg['access_token'],
                     'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', 'replace')
            try:
                detail = json.loads(raw).get('error', {}).get('message', raw)
            except Exception:
                detail = raw
            raise RuntimeError(f'Meta WhatsApp API HTTP {exc.code}: {detail}')
        except Exception as exc:
            raise RuntimeError('Tidak dapat menghubungi WhatsApp Cloud API: ' + str(exc))
        messages = result.get('messages') or []
        if not messages or not messages[0].get('id'):
            raise RuntimeError('Meta tidak mengembalikan ID pesan. Respons: ' + json.dumps(result, ensure_ascii=False)[:500])
        return {'message_id': messages[0]['id'], 'recipient': recipient, 'session_id': session_id}
