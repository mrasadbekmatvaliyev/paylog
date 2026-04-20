from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0004_order_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="note",
            field=models.TextField(blank=True, default=""),
        ),
    ]
