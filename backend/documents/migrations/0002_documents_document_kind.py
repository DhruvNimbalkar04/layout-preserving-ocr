from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="documents",
            name="document_kind",
            field=models.CharField(
                choices=[("normal", "Normal PDF"), ("scanned", "Scanned PDF")],
                default="normal",
                max_length=20,
            ),
        ),
    ]
