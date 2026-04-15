from rest_framework import serializers

from .models import Category, Order, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "discount_price",
            "image_urls",
            "category",
            "category_id",
            "stock",
            "is_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "category"]

    def validate(self, attrs):
        image_urls = attrs.get("image_urls", serializers.empty)
        image_url = self.initial_data.get("image_url")

        if image_urls is not serializers.empty:
            attrs["image_urls"] = [url for url in image_urls if url]

        if image_urls is serializers.empty and image_url:
            attrs["image_urls"] = [image_url]

        if "image_urls" not in attrs:
            return attrs

        normalized_urls = self._merge_image_urls(attrs.get("image_urls", []))
        attrs["image_urls"] = normalized_urls
        attrs["image_url"] = normalized_urls[0] if normalized_urls else None
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        image_urls = instance.image_urls or []
        if not image_urls and instance.image_url:
            image_urls = [instance.image_url]
        data["image_urls"] = image_urls
        return data

    @staticmethod
    def _merge_image_urls(image_urls):
        merged = []
        for url in image_urls or []:
            if url and url not in merged:
                merged.append(url)
        return merged


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_available=True),
        source="product",
        write_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "product",
            "product_id",
            "quantity",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "product"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_status(self, value):
        allowed = {Order.Status.PENDING, Order.Status.CONFIRMED}
        if value not in allowed:
            raise serializers.ValidationError("Status must be pending or confirmed.")
        return value
