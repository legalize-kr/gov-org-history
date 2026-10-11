import io
import sys
import unittest
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_gvrn_org import post_json
from fetch_institution_list import fetch_text as institution_text
from fetch_reference_lists import fetch_text as reference_text


class SourceRetries(unittest.TestCase):
    @patch("source_http.time.sleep")
    def test_all_collectors_recover_from_disconnect(self, sleep):
        for call, body, expected in [
            (lambda: post_json("/test", {}), b'{"data": []}', {"data": []}),
            (lambda: institution_text("https://org.go.kr/test"), b"page", "page"),
            (lambda: reference_text("https://org.go.kr/test"), b"page", "page"),
        ]:
            with patch("source_http.request.urlopen", side_effect=[RemoteDisconnected(), io.BytesIO(body)]) as opened:
                self.assertEqual(call(), expected)
                self.assertEqual(opened.call_count, 2)

    @patch("source_http.time.sleep")
    def test_exhausted_disconnect_still_fails(self, sleep):
        with patch("source_http.request.urlopen", side_effect=RemoteDisconnected()) as opened:
            with self.assertRaises(RemoteDisconnected):
                post_json("/test", {})
            self.assertEqual(opened.call_count, 4)

    def test_permanent_http_error_is_not_retried(self):
        with patch("source_http.request.urlopen", side_effect=HTTPError("https://org.go.kr/test", 404, "missing", {}, None)) as opened:
            with self.assertRaises(HTTPError):
                post_json("/test", {})
            self.assertEqual(opened.call_count, 1)

    @patch("source_http.time.sleep")
    def test_transient_http_error_recovers(self, sleep):
        with patch("source_http.request.urlopen", side_effect=[HTTPError("https://org.go.kr/test", 503, "unavailable", {}, None), io.BytesIO(b"{}")]):
            self.assertEqual(post_json("/test", {}), {})
