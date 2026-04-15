from django.db import migrations, models


def copy_image_url_to_image_urls(apps, schema_editor):
    Product = apps.get_model("market", "Product")
    for product in Product.objects.exclude(image_url__isnull=True).exclude(image_url=""):
        product.image_urls = [product.image_url]
        product.save(update_fields=["image_urls"])


def clear_image_urls(apps, schema_editor):
    Product = apps.get_model("market", "Product")
    Product.objects.update(image_urls=[])


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0002_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_urls",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(
            code=copy_image_url_to_image_urls,
            reverse_code=clear_image_urls,
        ),
    ]

