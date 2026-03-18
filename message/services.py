from users.models import UserDevice
from users.services.push_notifications import send_bulk_fcm_notifications

from .models import Message


MESSAGE_PUSH_TITLE = "New message"
MESSAGE_PUSH_TYPE = "in_app_message"
MESSAGE_PUSH_TARGET = "system_messages"


def build_message_push_payload(message: Message) -> dict[str, str]:
    payload = {
        "message_id": str(message.id),
        "type": MESSAGE_PUSH_TYPE,
        "target": MESSAGE_PUSH_TARGET,
    }
    if message.link:
        payload["link"] = message.link
    if message.link_name:
        payload["link_name"] = message.link_name
    return payload


def send_push_for_message(message: Message) -> tuple[int, int]:
    tokens = list(
        UserDevice.objects.filter(user=message.user, notifications_enabled=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
        .distinct()
    )
    if not tokens:
        return 0, 0

    body = message.text[:500]
    return send_bulk_fcm_notifications(
        tokens=tokens,
        title=MESSAGE_PUSH_TITLE,
        body=body,
        data=build_message_push_payload(message),
    )


def create_messages_for_users(user_qs, text: str, link: str | None = None, link_name: str | None = None) -> tuple[int, int, int]:
    user_ids = list(user_qs.values_list("id", flat=True))
    if not user_ids:
        return 0, 0, 0

    Message.objects.bulk_create(
        [
            Message(user_id=user_id, text=text, link=link, link_name=link_name)
            for user_id in user_ids
        ],
        batch_size=1000,
    )

    tokens = list(
        UserDevice.objects.filter(user_id__in=user_ids, notifications_enabled=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
        .distinct()
    )
    if not tokens:
        return len(user_ids), 0, 0

    sent, failed = send_bulk_fcm_notifications(
        tokens=tokens,
        title=MESSAGE_PUSH_TITLE,
        body=text[:500],
        data={
            "type": MESSAGE_PUSH_TYPE,
            "target": MESSAGE_PUSH_TARGET,
            "link": link or "",
            "link_name": link_name or "",
        },
    )
    return len(user_ids), sent, failed
