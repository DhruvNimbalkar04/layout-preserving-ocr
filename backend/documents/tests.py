import json
import shutil
import tempfile
from unittest.mock import patch

import pymupdf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Documents, ExtractedText
from .pymupdf_extractor import LAYOUT_VERSION, _apply_reading_order

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="ocr-tests-")


def make_pdf(text="Hello world"):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    payload = doc.tobytes()
    doc.close()
    return payload


def pdf_upload(name="sample.pdf"):
    return SimpleUploadedFile(name, make_pdf(), content_type="application/pdf")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DocumentApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

    def _create_document(self, name="stored.pdf"):
        return Documents.objects.create(
            file=SimpleUploadedFile(name, make_pdf(), content_type="application/pdf"),
            file_name=name,
            file_type="pdf",
            file_size=1024,
            document_kind="normal",
        )

    @patch("documents.views._start_extraction")
    def test_upload_pdf_returns_metadata(self, start_extraction):
        response = self.client.post(
            "/api/documents/",
            {"file": pdf_upload(), "document_kind": "normal"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["file_type"], "pdf")
        self.assertEqual(response.data["file_name"], "sample.pdf")
        self.assertEqual(response.data["num_pages"], 1)
        self.assertGreater(response.data["file_size"], 0)
        self.assertTrue(start_extraction.called)

    def test_upload_rejects_unsupported_extension(self):
        upload = SimpleUploadedFile("payload.exe", b"MZ binary", content_type="application/octet-stream")
        response = self.client.post(
            "/api/documents/",
            {"file": upload, "document_kind": "normal"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
        self.assertEqual(Documents.objects.count(), 0)

    def test_upload_rejects_empty_file(self):
        upload = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/",
            {"file": upload, "document_kind": "normal"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)

    @override_settings(UPLOAD_MAX_FILE_SIZE=10)
    def test_upload_rejects_oversized_file(self):
        response = self.client.post(
            "/api/documents/",
            {"file": pdf_upload("large.pdf"), "document_kind": "normal"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("larger than", response.data["file"][0])

    def test_list_documents(self):
        self._create_document("one.pdf")
        self._create_document("two.pdf")

        response = self.client.get("/api/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_delete_document(self):
        document = self._create_document()

        response = self.client.delete(f"/api/documents/{document.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Documents.objects.filter(pk=document.id).exists())

    def test_layout_patch_and_exports(self):
        document = self._create_document()
        layout = {
            "pages": [
                {
                    "page_number": 1,
                    "width": 595.2,
                    "height": 841.92,
                    "elements": [
                        {
                            "id": "el-1",
                            "type": "text-line",
                            "text": "Hello layout",
                            "bbox": {"x": 72, "y": 72, "width": 180, "height": 14},
                            "style": {"fontSize": 12},
                        }
                    ],
                }
            ],
            "layout_version": LAYOUT_VERSION,
        }

        patch_response = self.client.patch(
            f"/api/documents/{document.id}/layout/",
            {"layout_data": layout},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)

        status_response = self.client.get(f"/api/documents/{document.id}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["has_layout"])

        json_response = self.client.get(
            f"/api/documents/{document.id}/export/?export_format=json"
        )
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json.loads(json_response.content)["pages"][0]["elements"][0]["text"], "Hello layout")

        txt_response = self.client.get(
            f"/api/documents/{document.id}/export/?export_format=txt"
        )
        self.assertEqual(txt_response.status_code, 200)
        self.assertIn("Hello layout", txt_response.content.decode("utf-8"))

    def test_export_rejects_unknown_format(self):
        document = self._create_document()
        ExtractedText.objects.create(document=document, text="x", layout_data={"pages": []})

        response = self.client.get(
            f"/api/documents/{document.id}/export/?export_format=csv"
        )

        self.assertEqual(response.status_code, 400)


def text_line(element_id, x, y, width=180, height=12):
    return {
        "id": element_id,
        "type": "text-line",
        "text": element_id,
        "bbox": {"x": x, "y": y, "width": width, "height": height},
        "style": {},
    }


class ReadingOrderTests(TestCase):
    def test_single_column_order_is_preserved(self):
        elements = [text_line(f"line-{i}", 72, 100 + i * 20, width=440) for i in range(8)]

        ordered = _apply_reading_order(elements, 612)

        self.assertEqual([el["id"] for el in ordered], [el["id"] for el in elements])

    def test_two_columns_are_sorted_column_major(self):
        elements = []
        for row in range(5):
            elements.append(text_line(f"left-{row}", 50, 100 + row * 20, width=200))
            elements.append(text_line(f"right-{row}", 340, 100 + row * 20, width=200))

        ordered = _apply_reading_order(elements, 612)

        expected = [f"left-{i}" for i in range(5)] + [f"right-{i}" for i in range(5)]
        self.assertEqual([el["id"] for el in ordered], expected)

    def test_short_pages_are_left_alone(self):
        elements = [text_line("only-1", 50, 100, width=200), text_line("only-2", 340, 100, width=200)]

        ordered = _apply_reading_order(elements, 612)

        self.assertEqual([el["id"] for el in ordered], ["only-1", "only-2"])
