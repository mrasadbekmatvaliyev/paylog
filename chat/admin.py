from django.contrib import admin

from .models import DebtorChat, PayNoteChat


@admin.register(PayNoteChat)
class PayNoteChatAdmin(admin.ModelAdmin):
    list_display = ("owner", "message", "created_at", "updated_at")
    search_fields = ("owner__phone", "message")


@admin.register(DebtorChat)
class DebtorChatAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "owner", "created_at", "updated_at")
    search_fields = ("full_name", "phone", "owner__phone")
