"""Optional Fonnte WhatsApp gateway: provider-accepted is NOT delivered."""
import json
import os
import threading
import urllib.parse
import urllib.request
import urllib.error

class FonnteGateway:
    def __init__(self, data_dir, http=None):
        self.lock = threading.RLock()
        self.path = os.path.join(data_dir, 'fonnte-config.json')
        self.sent_path = os.path.join(data_dir, 'fonnte-send-log.json')
        self.http = http or self._http
        try:
            with open(self.path, encoding='utf-8') as f: self.config = json.load(f)
        except (ValueError, OSError):
            self.config = {}
        try:
            with open(self.sent_path, encoding='utf-8') as f: self.sent = json.load(f)
        except (ValueError, OSError): self.sent = {}
        # Persist duplicate protection across backend restarts.

    @staticmethod
    def _http(fields, token):
        body = urllib.parse.urlencode(fields).encode('utf-8')
        req = urllib.request.Request('https://api.fonnte.com/send', data=body, method='POST',
                                     headers={'Authorization': token,
                                              'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read(100000).decode('utf-8'))

    def status(self):
        with self.lock:
            return {'configured': bool(self.config.get('token'))}

    @staticmethod
    def _device_http(token):
        request = urllib.request.Request('https://api.fonnte.com/device', data=b'', method='POST',
                                         headers={'Authorization': token})
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read(100000).decode('utf-8'))

    def device_profile(self):
        """Check Fonnte device authentication without exposing the saved API token."""
        with self.lock:
            token = self.config.get('token', '')
        if not token:
            raise ValueError('Token Fonnte belum disimpan. Masukkan token di Pengaturan Umum.')
        try:
            payload = self._device_http(token)
        except urllib.error.HTTPError as err:
            raise RuntimeError('Koneksi Fonnte mengembalikan HTTP '+str(err.code)+'. Periksa token dan status perangkat.')
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise RuntimeError('Tidak dapat menghubungi Fonnte. Periksa koneksi internet atau coba lagi.') from err
        if not isinstance(payload, dict) or payload.get('status') is not True:
            reason = str(payload.get('reason') or 'token tidak valid atau perangkat tidak tersedia') if isinstance(payload, dict) else 'respons API tidak valid'
            raise ValueError('Fonnte menolak pemeriksaan perangkat: '+reason[:160])
        connection = str(payload.get('device_status') or 'unknown').lower()
        return {'device':str(payload.get('device') or ''),
                'device_status':connection,'quota':str(payload.get('quota') or '0'),
                'package':str(payload.get('package') or ''),'expired':str(payload.get('expired') or ''),
                'warning':'Perangkat Fonnte belum terhubung.' if connection!='connect' else ''}

    @staticmethod
    def _normalize_token(raw):
        token = str(raw or '').strip().strip('\"\'')
        if token.lower().startswith('bearer '):
            token = token[7:].strip()  # Fonnte requires raw device token, not Bearer.
        return token

    @staticmethod
    def _provider_reason(payload):
        raw = str((payload or {}).get('reason') or (payload or {}).get('detail') or '').strip()
        reason = raw.lower()
        if 'token invalid' in reason or 'invalid token' in reason or 'unknown user' in reason:
            return ('Token Fonnte ditolak (invalid token). Salin TOKEN PERANGKAT dari menu Devices '
                    'di dashboard Fonnte, bukan token akun atau nomor WhatsApp. '
                    'Pastikan token lengkap, tanpa kata Bearer atau spasi tambahan.')
        if 'disconnect' in reason:
            return 'Perangkat WhatsApp pada Fonnte tidak terhubung. Hubungkan melalui dashboard Fonnte lalu coba lagi.'
        if 'quota' in reason:
            return 'Kuota pesan Fonnte habis. Periksa paket dan kuota pada dashboard Fonnte.'
        return 'Fonnte menolak permintaan: ' + (raw[:150] or 'respons tidak valid')

    def configure(self, token):
        # Validate the new device token against Fonnte before overwriting the
        # previously working token; authentication never uses an account token.
        token = self._normalize_token(token)
        with self.lock:
            old = self.config.get('token', '')
        if not token:
            token = old
        if not token or len(token) > 2048:
            raise ValueError('Masukkan token perangkat Fonnte dari menu Devices.')
        if any(ord(ch) < 32 or ch.isspace() for ch in token):
            raise ValueError('Token mengandung spasi atau baris baru. Salin ulang token perangkat dari Fonnte.')
        try:
            profile = self._device_http(token)
        except urllib.error.HTTPError as err:
            raise RuntimeError('Fonnte gagal memeriksa token (HTTP ' + str(err.code) + '). Token sebelumnya tidak diganti.') from err
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise RuntimeError('Tidak dapat memeriksa token karena jaringan tidak tersedia. Token sebelumnya tidak diganti.') from err
        if not isinstance(profile, dict) or profile.get('status') is not True:
            raise ValueError(self._provider_reason(profile if isinstance(profile, dict) else {}))
        with self.lock:
            self.config = {'token': token}
            with open(self.path+'.tmp', 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
            os.replace(self.path+'.tmp', self.path)
        return {**self.status(), 'verified': True,
                'device': str(profile.get('device') or ''),
                'device_status': str(profile.get('device_status') or 'unknown'),
                'quota': str(profile.get('quota') or '0')}

    def send(self, session_id, phone, url, consent):
        if consent is not True:
            raise ValueError('Pelanggan harus menyetujui penerimaan pesan.')
        import re
        digits = re.sub(r'\D', '', str(phone or ''))
        digits = '62' + digits[1:] if digits.startswith('0') else ('62' + digits if digits.startswith('8') else digits)
        if not re.fullmatch(r'62\d{8,13}', digits):
            raise ValueError('Nomor WhatsApp tidak valid.')
        parsed = urllib.parse.urlparse(str(url or ''))
        if parsed.scheme != 'https' or parsed.hostname != 'drive.google.com':
            raise ValueError('Tautan Google Drive belum tersedia atau bukan alamat yang diizinkan.')
        key = str(session_id) + ':' + digits
        with self.lock:
            if key in self.sent:
                return dict(self.sent[key], duplicate=True)
            token = self.config.get('token', '')
            if not token: raise ValueError('Token Fonnte belum diatur.')
            fields = {'target': digits,
                      'message': ('Halo, kami dari KACA.ID Photobooth Studio 😊\n\n'
                                  'Terima kasih telah berfoto bersama kami! ✨\n'
                                  'Hasil foto dan Live Photo kakak sudah bisa diakses melalui link Google Drive berikut:\n\n'
                                  + url + '\n\n'
                                  'Silakan lihat dan unduh hasilnya ya, kak. Terima kasih! 😊'),
                      'countryCode': '62', 'connectOnly': 'true'}
            # Keep the duplicate guard under lock while submitting to provider.
            try:
                result = self.http(fields, token)
            except urllib.error.HTTPError as err:
                raise RuntimeError(f'Fonnte mengembalikan HTTP {err.code}. Periksa token, perangkat, atau kuota.') from err
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                raise RuntimeError('Tidak dapat terhubung ke Fonnte. Periksa internet dan perangkat Fonnte.') from err
            if not isinstance(result, dict) or result.get('status') is not True:
                reason = str(result.get('reason') or result.get('detail') or 'perangkat, token, atau kuota bermasalah') if isinstance(result, dict) else 'respons tidak valid'
                raise RuntimeError(self._provider_reason(result))
            reqid = str(result.get('requestid') or '')
            ids = result.get('id') or []
            message_id = str(ids[0]) if isinstance(ids, list) and ids else ''
            accepted = {'ok': True, 'status': 'accepted', 'provider': 'fonnte',
                        'request_id':reqid,'message_id':message_id,
                        'note': 'Gateway menerima permintaan; belum tentu terkirim ke penerima.'}
            self.sent[key] = accepted
            with open(self.sent_path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(self.sent, f, ensure_ascii=False, indent=2)
            os.replace(self.sent_path + '.tmp', self.sent_path)
            return accepted
