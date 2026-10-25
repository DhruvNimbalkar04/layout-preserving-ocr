import os
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from . import ocr_engine

OCRSPACE_PAYLOAD = {
    "ParsedResults": [
        {
            "FileParseExitCode": 1,
            "ParsedText": "Hello world",
            "TextOverlay": {
                "Lines": [
                    {
                        "Words": [
                            {"WordText": "Hello", "Left": 100, "Top": 50, "Width": 60, "Height": 20},
                            {"WordText": "world", "Left": 170, "Top": 52, "Width": 70, "Height": 20},
                        ],
                        "MaxHeight": 20,
                        "MinTop": 50,
                    }
                ],
                "HasOverlay": True,
            },
        }
    ],
    "OCRExitCode": 1,
    "IsErroredOnProcessing": False,
}


class BackendSelectionTests(SimpleTestCase):
    def test_explicit_backend_wins(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "ocrspace"}):
            self.assertEqual(ocr_engine.ocr_backend(), "ocrspace")
            self.assertFalse(ocr_engine.uses_local_paddle())

    def test_unknown_backend_falls_back(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "tesseract"}):
            with patch.object(ocr_engine, "_paddle_installed", return_value=False):
                self.assertEqual(ocr_engine.ocr_backend(), "none")

    def test_unset_backend_uses_paddle_when_available(self):
        env = {k: v for k, v in os.environ.items() if k != "OCR_BACKEND"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ocr_engine, "_paddle_installed", return_value=True):
                self.assertEqual(ocr_engine.ocr_backend(), "paddle")


class OcrSpaceParsingTests(SimpleTestCase):
    def test_words_are_merged_into_one_line(self):
        lines = ocr_engine._ocrspace_lines(OCRSPACE_PAYLOAD)
        self.assertEqual(len(lines), 1)
        text, x0, y0, x1, y1, confidence = lines[0]
        self.assertEqual(text, "Hello world")
        self.assertEqual((x0, y0, x1, y1), (100.0, 50.0, 240.0, 72.0))
        self.assertIsNone(confidence)

    def test_page_error_is_raised(self):
        payload = {
            "ParsedResults": [
                {"FileParseExitCode": -20, "ErrorMessage": "Timeout", "TextOverlay": None}
            ],
            "IsErroredOnProcessing": True,
            "ErrorMessage": "Timeout",
        }
        with self.assertRaises(RuntimeError):
            ocr_engine._ocrspace_lines(payload)

    def test_missing_overlay_falls_back_to_plain_text(self):
        payload = {
            "ParsedResults": [{"FileParseExitCode": 1, "ParsedText": "First\nSecond"}],
            "OCRExitCode": 1,
        }
        texts = [line[0] for line in ocr_engine._ocrspace_lines(payload)]
        self.assertEqual(texts, ["First", "Second"])


class OcrDispatchTests(SimpleTestCase):
    def test_ocrspace_elements_are_scaled_to_points(self):
        env = {"OCR_BACKEND": "ocrspace", "OCRSPACE_API_KEY": "test-key"}
        with patch.dict(os.environ, env), patch.object(
            ocr_engine, "_http_json", return_value=OCRSPACE_PAYLOAD
        ):
            elements = ocr_engine.ocr_upload_to_elements(
                b"jpeg-bytes", page_number=2, scale_x=0.5, scale_y=0.25,
                width_px=1200, height_px=1600,
            )

        self.assertEqual(len(elements), 1)
        element = elements[0]
        self.assertEqual(element["id"], "page-2-ocr-0")
        self.assertEqual(element["text"], "Hello world")
        self.assertEqual(element["source"], "ocrspace")
        self.assertEqual(element["bbox"]["x"], 50.0)
        self.assertEqual(element["bbox"]["y"], 12.5)
        self.assertNotIn("confidence", element)

    def test_missing_api_key_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "OCRSPACE_API_KEY"}
        env["OCR_BACKEND"] = "ocrspace"
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError):
                ocr_engine.ocr_upload_to_elements(b"x")

    def test_disabled_backend_raises(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "none"}):
            with self.assertRaises(RuntimeError):
                ocr_engine.ocr_upload_to_elements(b"x")


class HealthEndpointTests(SimpleTestCase):
    def test_health_reports_backend_without_credentials(self):
        client = APIClient()
        env = {k: v for k, v in os.environ.items() if k != "OCRSPACE_API_KEY"}
        env["OCR_BACKEND"] = "gemini"
        env.pop("GEMINI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            response = client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["ocr_backend"], "gemini")
        self.assertFalse(body["ocr_ready"])

    def test_health_reports_ready_when_key_is_present(self):
        client = APIClient()
        env = dict(os.environ, OCR_BACKEND="ocrspace", OCRSPACE_API_KEY="k")
        with patch.dict(os.environ, env):
            response = client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ocr_ready"])
