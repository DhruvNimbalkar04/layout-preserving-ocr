from django.db import models

class Documents(models.Model):
    DOCUMENT_KIND_CHOICES = [
        ("normal", "Normal PDF"),
        ("scanned", "Scanned PDF"),
    ]

    file = models.FileField(upload_to="documents/", max_length=255)
    file_type = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    document_kind = models.CharField(
        max_length=20,
        choices=DOCUMENT_KIND_CHOICES,
        default="normal",
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class ExtractedText(models.Model):
    document = models.OneToOneField("Documents", on_delete=models.CASCADE, related_name="extracted_text")
    text = models.TextField()
    layout_data = models.JSONField(
        default=dict,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)