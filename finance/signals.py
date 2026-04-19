from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import User

from .services import ensure_virtual_card_for_user


@receiver(post_save, sender=User)
def create_virtual_card_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    ensure_virtual_card_for_user(instance)
