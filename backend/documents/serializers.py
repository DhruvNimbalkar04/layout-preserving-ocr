import os
import pymupdf
from rest_framework import serializers
from django.conf import settings
from .models import Documents, ExtractedText


class ExtractedTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedText
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    extracted_text = ExtractedTextSerializer(read_only=True)
    num_pages = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = "__all__"
        read_only_fields = [
            "file_name",
            "file_type",
            "file_size",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_document_kind(self, value):
        if value not in ("normal", "scanned"):
            return "normal"
        return value

    def validate_file(self, value):
        extension = os.path.splitext(value.name)[1].lower().lstrip(".")
        allowed = {ext.lower().lstrip(".") for ext in settings.UPLOAD_ALLOWED_EXTENSIONS}

        if not extension or extension not in allowed:
            readable = ", ".join(sorted(allowed))
            raise serializers.ValidationError(
                f"Unsupported file type '.{extension or 'unknown'}'. Allowed: {readable}."
            )

        if value.size == 0:
            raise serializers.ValidationError("The uploaded file is empty.")

        if value.size > settings.UPLOAD_MAX_FILE_SIZE:
            limit_mb = settings.UPLOAD_MAX_FILE_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f"File is larger than the {limit_mb:.0f} MB limit."
            )

        return value

    def get_num_pages(self, obj):
        if not obj.file:
            return 1

        ext = (obj.file_type or obj.file_name.split(".")[-1]).lower()

        if ext == "pdf":
            try:
                doc = pymupdf.open(obj.file.path)
                count = len(doc)
                doc.close()
                return count
            except Exception:
                return 1

        return 1

    def create(self, validated_data):
        file = validated_data["file"]

        validated_data["file_name"] = file.name
        validated_data["file_type"] = file.name.split(".")[-1].lower()
        validated_data["file_size"] = file.size

        return Documents.objects.create(**validated_data)
