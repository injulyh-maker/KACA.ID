"""DOKU Checkout QRIS: signed server-to-server initiation and verified status.

Do not mark a transaction paid based on a checkout URL or a browser callback.
All state transitions to paid require an authenticated DOKU status response over HTTPS.
"""
import base64
import datetime as dt
import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class DokuQris:
    def __init__(self, data_dir, http=None):
        self.config_path = os.path.join(data_dir, 'doku-qris-config.json')
        self.ledger_path = os.path.join(data_dir, 'doku-qris-payments.json')
        self.lock = threading.RLock()
        self.http = http or self._http
        self.config = self._read(self.config_path, {})
        self.ledger = self._read(self.ledger_path, {})

    @staticmethod
    def _read(path, fallback):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else fallback
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def _save(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as out:
            json.dump(data, out, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def public_config(self):
        with self.lock:
            return {'client_id': self.config.get('client_id', ''),
                    'environment': self.config.get('environment', 'sandbox'),
                    'secret_saved': bool(self.config.get('secret_key')),
                    'configured': bool(self.config.get('client_id') and self.config.get('secret_key'))}

    def configure(self, data):
        with self.lock:
            environment = str(data.get('environment', 'sandbox')).lower()
            if environment not in ('sandbox', 'production'):
                raise ValueError('Lingkungan DOKU harus sandbox atau production.')
            client = str(data.get('client_id', '')).strip()
            secret = str(data.get('secret_key', '')).strip()
            if not client or len(client) > 150:
                raise ValueError('Client ID DOKU belum valid.')
            if not secret and client == self.config.get('client_id') and environment == self.config.get('environment'):
                secret = self.config.get('secret_key', '')
            elif not secret and environment != self.config.get('environment'):
                raise ValueError('Pindah DOKU Sandbox/Production memerlukan Secret Key untuk environment tujuan.')
            if not secret:
                raise ValueError('Secret Key DOKU harus diisi.')
            if len(secret) > 1000:
                raise ValueError('Secret Key terlalu panjang.')
            self.config = {'client_id': client, 'secret_key': secret, 'environment': environment}
            self._save(self.config_path, self.config)
            return self.public_config()

    @staticmethod
    def signature(client_id, secret, request_id, timestamp, target, raw=b'', *, response=False):
        pieces = [f'Client-Id:{client_id}', f'Request-Id:{request_id}',
                  f'{"Response" if response else "Request"}-Timestamp:{timestamp}',
                  f'Request-Target:{target}']
        if raw:
            digest = base64.b64encode(hashlib.sha256(raw).digest()).decode('ascii')
            pieces.append('Digest:' + digest)
        encoded = '\n'.join(pieces).encode('utf-8')
        mac = hmac.new(secret.encode('utf-8'), encoded, hashlib.sha256).digest()
        return 'HMACSHA256=' + base64.b64encode(mac).decode('ascii')

    @staticmethod
    def _http(method, url, headers, body):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, response.read(1024 * 1024), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(4096), dict(error.headers)

    def _request(self, method, target, payload=None):
        with self.lock:
            cfg = dict(self.config)
        if not (cfg.get('client_id') and cfg.get('secret_key')):
            raise ValueError('DOKU belum dikonfigurasi.')
        url = ('https://api-sandbox.doku.com' if cfg['environment'] == 'sandbox'
               else 'https://api.doku.com') + target
        body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode() if payload is not None else b''
        request_id = secrets.token_hex(16)
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        headers = {'Client-Id': cfg['client_id'], 'Request-Id': request_id,
                   'Request-Timestamp': timestamp, 'Signature': self.signature(
                       cfg['client_id'], cfg['secret_key'], request_id, timestamp, target, body),
                   'Accept': 'application/json'}
        if body:
            headers['Content-Type'] = 'application/json'
        status, response_body, response_headers = self.http(method, url, headers, body or None)
        if status < 200 or status >= 300:
            # Never include secrets or full payment response in messages/logs.
            # Show safe provider validation detail without leaking credentials or payloads.
            try:
                detail=json.loads(response_body.decode('utf-8','replace'))
                if isinstance(detail,dict):
                    err=detail.get('error') or {}
                    if isinstance(err,dict):
                        explanation=err.get('message') or err.get('description') or err.get('code')
                    else:explanation=str(err)
                    explanation=explanation or detail.get('message') or detail.get('error_message') or detail.get('responseMessage')
                else:explanation=''
            except (ValueError,TypeError,UnicodeError):explanation=''
            explanation=str(explanation or '').replace(str(cfg.get('secret_key') or ''),'[REDACTED]')[:200]
            raise RuntimeError('DOKU HTTP '+str(status)+(': '+explanation if explanation else '')+
                               '. Periksa environment, aktivasi QRIS merchant, serta parameter transaksi.')
        try:
            result = json.loads(response_body)
        except (ValueError, TypeError):
            raise RuntimeError('Respons DOKU bukan JSON yang valid.')
        if not isinstance(result, dict):
            raise RuntimeError('Respons DOKU tidak valid.')
        return result

    def create(self, amount):
        amount = int(amount)
        # Provider-specific minima are validated by DOKU; a local free session
        # (Rp0) must never be submitted as a paid checkout.
        if not 1 <= amount <= 999999999999:
            raise ValueError('Checkout DOKU memerlukan nominal positif; sesi gratis tidak memakai gateway.')
        with self.lock:
            if not self.public_config()['configured']:
                raise ValueError('Client ID dan Secret Key DOKU belum diatur.')
        invoice = 'KACA' + dt.datetime.now(dt.timezone.utc).strftime('%y%m%d%H%M%S') + secrets.token_hex(3).upper()
        result = self._request('POST', '/checkout/v1/payment',
                               {'order': {'invoice_number': invoice, 'amount': amount},
                                'payment': {'payment_method_types': ['QRIS'], 'payment_due_date': 15}})
        payment = result.get('response', result).get('payment', {})
        url = str(payment.get('url') or '')
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not (parsed.hostname == 'doku.com' or parsed.hostname.endswith('.doku.com')):
            raise RuntimeError('DOKU tidak memberikan tautan Checkout HTTPS yang valid.')
        now = time.time()
        with self.lock:
            item = {'invoice': invoice, 'amount': amount, 'status': 'pending',
                    'created_at': now, 'checked_at': 0, 'checkout_url': url,
                    'environment': self.config['environment'], 'consumed': False}
            self.ledger[invoice] = item
            self._save(self.ledger_path, self.ledger)
        return self.public_payment(invoice)

    def public_payment(self, invoice):
        with self.lock:
            row = self.ledger.get(str(invoice))
            if not row:
                raise ValueError('Invoice QRIS tidak ditemukan.')
            return {**{k: row.get(k) for k in ('invoice', 'amount', 'status', 'checkout_url', 'created_at')}, 'provider':'doku'}

    def check(self, invoice, *, now=None):
        """Provider-authenticated read; DOKU recommends querying after 60 seconds."""
        invoice = str(invoice or '')
        now = time.time() if now is None else now
        with self.lock:
            row = self.ledger.get(invoice)
            if not row:
                raise ValueError('Invoice QRIS tidak ditemukan.')
            if row['status'] == 'paid':
                return self.public_payment(invoice)
            if row['environment'] != self.config.get('environment'):
                raise RuntimeError('Environment DOKU berubah. Selesaikan transaksi di environment asal.')
            # Polling status immediately is explicitly discouraged by DOKU.
            if now - row['created_at'] < 60 or now - row.get('checked_at', 0) < 12:
                return self.public_payment(invoice)
            row['checked_at'] = now
            self._save(self.ledger_path, self.ledger)
        response = self._request('GET', '/orders/v1/status/' + urllib.parse.quote(invoice, safe=''))
        # DOKU may serialize amounts as 1000, "1000" or "1000.00".
        # Compare monetary values, not string representations, but never
        # accept missing identifiers, missing amounts or a merely successful page.
        payload = response.get('response') if isinstance(response.get('response'),dict) else response
        transaction = payload.get('transaction') or {}
        order = payload.get('order') or {}
        if str(order.get('invoice_number') or '') != invoice:
            raise RuntimeError('Invoice status DOKU tidak cocok. Pembayaran belum dikonfirmasi.')
        try:
            expected=Decimal(str(row['amount']))
            actual=Decimal(str(order['amount']))
            if not actual.is_finite() or actual != expected:
                raise ValueError('wrong amount')
        except (KeyError,ValueError,InvalidOperation,TypeError):
            raise RuntimeError('Nominal dari status DOKU tidak cocok atau tidak tersedia; transaksi belum dikonfirmasi.')
        state = str(transaction.get('status') or '').upper()
        with self.lock:
            row = self.ledger[invoice]
            if state == 'SUCCESS':
                row['status'] = 'paid'
                row['paid_at'] = now
            elif state in ('EXPIRED', 'FAILED'):
                row['status'] = state.lower()
            self._save(self.ledger_path, self.ledger)
        return self.public_payment(invoice)

    def consume_paid(self, invoice):
        with self.lock:
            row = self.ledger.get(str(invoice))
            if not row or row.get('status') != 'paid' or row.get('consumed'):
                raise ValueError('QRIS belum terverifikasi berhasil atau invoice sudah digunakan.')
            row['consumed'] = True
            row['consumed_at'] = time.time()
            self._save(self.ledger_path, self.ledger)
            return True
