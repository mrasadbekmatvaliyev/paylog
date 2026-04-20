from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0003_product_image_urls"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("virtual_card", "Virtual card"),
                ],
                default="cash",
                max_length=20,
            ),
        ),
    ]
