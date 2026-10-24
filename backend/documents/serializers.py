import pymupdf
from rest_framework import serializers
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