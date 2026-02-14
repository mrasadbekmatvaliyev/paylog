from django.conf import settings
from django.db import models


class PayNoteChat(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paynote_chat",
    )

    # Chat listda ko‘rinadigan preview (oxirgi yozuv). Bo‘lmasa null.
    message = models.CharField(max_length=255, null=True, blank=True)

    photo_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "paynote_chat"

    def __str__(self):
        return f"PayNote({self.owner_id})"


class DebtorChat(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="debtor_chats",
    )

    # CHATNING O‘Z MA’LUMOTLARI
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    photo_url = models.URLField(null=True, blank=True)

    # Chat preview
    message = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debtor_chat"
        unique_together = ("owner", "phone")

    def __str__(self):
        return f"DebtorChat({self.full_name})"
