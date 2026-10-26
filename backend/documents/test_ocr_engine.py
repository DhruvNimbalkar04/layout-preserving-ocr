import os
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from . import ocr_engine


class OcrSelectionTests(SimpleTestCase):
    def test_none_disables_ocr(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "none"}):
            self.assertEqual(ocr_engine.ocr_backend(), "none")
            self.assertFalse(ocr_engine.ocr_ready())

    def test_unset_uses_paddle_when_installed(self):
        env = {k: v for k, v in os.environ.items() if k != "OCR_BACKEND"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ocr_engine, "paddle_installed", return_value=True):
                self.assertEqual(ocr_engine.ocr_backend(), "paddle")
                self.assertTrue(ocr_engine.ocr_ready())

    def test_unset_without_paddle_reports_none(self):
        env = {k: v for k, v in os.environ.items() if k != "OCR_BACKEND"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ocr_engine, "paddle_installed", return_value=False):
                self.assertEqual(ocr_engine.ocr_backend(), "none")
                self.assertFalse(ocr_engine.ocr_ready())

    def test_explicit_paddle_without_install_is_not_ready(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "paddle"}):
            with patch.object(ocr_engine, "paddle_installed", return_value=False):
                self.assertFalse(ocr_engine.ocr_ready())


class HealthEndpointTests(SimpleTestCase):
    def test_reports_none_without_paddle(self):
        env = {k: v for k, v in os.environ.items() if k != "OCR_BACKEND"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ocr_engine, "paddle_installed", return_value=False):
                body = APIClient().get("/api/health/").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["ocr_backend"], "none")
        self.assertFalse(body["ocr_ready"])

    def test_reports_ready_with_paddle(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "paddle"}):
            with patch.object(ocr_engine, "paddle_installed", return_value=True):
                body = APIClient().get("/api/health/").json()
        self.assertTrue(body["ocr_ready"])
