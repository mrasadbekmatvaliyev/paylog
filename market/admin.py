from django.contrib import admin

from .models import Category, Order, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "image_url", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "discount_price",
        "category",
        "stock",
        "is_available",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "description")
    list_filter = ("is_available", "category")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "quantity", "status", "created_at", "updated_at")
    search_fields = ("user__phone", "product__name")
    list_filter = ("status",)
