from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .services import send_push_for_message


@receiver(post_save, sender=Message)
def send_message_created_push(sender, instance, created, **kwargs):
    if created:
        send_push_for_message(instance)
