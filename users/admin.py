from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import OTP, TelegramOTP, UserDevice

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["phone", "first_name", "last_name", "is_premium", "is_active"]
    search_fields = ["phone", "first_name", "last_name"]


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "attempts", "is_used", "created_at", "expires_at")
    search_fields = ("phone", "code")
    list_filter = ("is_used",)


@admin.register(TelegramOTP)
class TelegramOTPAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_user_id",
        "code",
        "attempts",
        "is_used",
        "created_at",
        "expires_at",
    )
    search_fields = ("telegram_user_id", "code")
    list_filter = ("is_used",)


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "device_id",
        "notifications_enabled",
        "app_version",
        "updated_at",
    )
    search_fields = ("device_id", "fcm_token", "user__phone")
    list_filter = ("platform", "notifications_enabled")
    readonly_fields = ("created_at", "updated_at")
