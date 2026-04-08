from django.conf import settings
from django.db import models
from django.utils import timezone


class Chat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chats",
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")

    def __str__(self):
        return f"Chat({self.id}) user={self.user_id}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def save(self, *args, **kwargs):
        is_create = self._state.adding
        super().save(*args, **kwargs)
        if is_create:
            Chat.objects.filter(pk=self.chat_id).update(updated_at=timezone.now())

    def __str__(self):
        return f"Message({self.id}) chat={self.chat_id} role={self.role}"
