from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("message", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="link_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
