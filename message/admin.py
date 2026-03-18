from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "link_name", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__phone", "text", "link", "link_name")
    fields = ("user", "text", "link", "link_name", "is_read", "created_at")
