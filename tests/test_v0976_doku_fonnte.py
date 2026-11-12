import base64
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from doku_qris import DokuQris
from whatsapp_gateway import FonnteGateway


class DokuGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []
        def mock(method, url, headers, body):
            self.calls.append((method, url, headers, body))
            if method == 'POST':
                self.order = json.loads(body)
                return 200, json.dumps({'response': {'payment': {'url': 'https://sandbox.doku.com/checkout/link/KACA-TEST'}}}).encode(), {}
            invoice = url.split('/')[-1]
            return 200, json.dumps({'order': {'invoice_number': invoice, 'amount': self.order['order']['amount']},
                                    'transaction': {'status': self.provider_status}}).encode(), {}
        self.provider_status = 'PENDING'
        self.gateway = DokuQris(self.temp.name, http=mock)
        self.gateway.configure({'client_id': 'MCH-DEMO-ONLY', 'secret_key': 'test-secret-for-mock', 'environment': 'sandbox'})

    def tearDown(self):
        self.temp.cleanup()

    def test_checkout_uses_qris_only_and_signed_headers(self):
        created = self.gateway.create(25000)
        self.assertEqual(created['status'], 'pending')
        body = self.order
        self.assertEqual(body['payment']['payment_method_types'], ['QRIS'])
        self.assertEqual(body['order']['amount'], 25000)
        self.assertEqual(self.calls[0][2]['Signature'], DokuQris.signature(
            'MCH-DEMO-ONLY', 'test-secret-for-mock', self.calls[0][2]['Request-Id'],
            self.calls[0][2]['Request-Timestamp'], '/checkout/v1/payment', self.calls[0][3]))
        self.assertFalse(self.gateway.public_config().get('secret_key'))

    def test_not_paid_until_authenticated_success(self):
        checkout = self.gateway.create(25000)
        invoice = checkout['invoice']
        self.assertEqual(self.gateway.check(invoice, now=time.time()), checkout)
        self.assertEqual(len(self.calls), 1)  # no status query before 60 s
        created = self.gateway.ledger[invoice]['created_at']
        self.gateway.check(invoice, now=created + 61)
        self.assertEqual(self.gateway.ledger[invoice]['status'], 'pending')
        self.provider_status = 'SUCCESS'
        result = self.gateway.check(invoice, now=created + 80)
        self.assertEqual(result['status'], 'paid')
        self.assertTrue(self.gateway.consume_paid(invoice))
        with self.assertRaisesRegex(ValueError, 'sudah digunakan'):
            self.gateway.consume_paid(invoice)

    def test_amount_mismatch_never_marks_paid(self):
        created = self.gateway.create(25000)
        invoice = created['invoice']
        self.provider_status = 'SUCCESS'
        original_request = self.gateway._request
        self.gateway._request = lambda *args, **kwargs: {'order': {'invoice_number': invoice, 'amount': 1}, 'transaction': {'status': 'SUCCESS'}}
        with self.assertRaisesRegex(RuntimeError, 'tidak cocok'):
            self.gateway.check(invoice, now=self.gateway.ledger[invoice]['created_at'] + 61)
        self.assertEqual(self.gateway.ledger[invoice]['status'], 'pending')


class FonnteGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sent = []
        def fake_post(fields, token):
            self.sent.append((fields, token))
            return {'status': True, 'id': ['abc123']}
        self.gateway = FonnteGateway(self.temp.name, http=fake_post)
        self.gateway._device_http=lambda token:{'status':True,'device':'6282396674553','device_status':'connect','quota':'20'}
        self.gateway.configure('DEMO-MOCK-TOKEN')

    def tearDown(self):
        self.temp.cleanup()

    def test_accept_only_not_delivered(self):
        response = self.gateway.send('0123456789ab', '081234567890', 'https://drive.google.com/drive/folders/abc', True)
        self.assertEqual(response['status'], 'accepted')
        self.assertIn('belum tentu', response['note'])
        self.assertEqual(self.sent[0][0]['target'], '6281234567890')
        duplicate = self.gateway.send('0123456789ab', '081234567890', 'https://drive.google.com/drive/folders/abc', True)
        self.assertTrue(duplicate['duplicate'])
        self.assertEqual(len(self.sent), 1)

    def test_refuse_without_consent_or_drive(self):
        with self.assertRaises(ValueError):
            self.gateway.send('0123456789ab', '081234567890', 'https://drive.google.com/drive/folders/abc', False)
        with self.assertRaises(ValueError):
            self.gateway.send('0123456789ab', '081234567890', 'https://example.org/bad', True)
        self.assertEqual(self.sent, [])

if __name__ == '__main__':
    unittest.main(verbosity=2)
