import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)

FOOD_KEYWORDS = (
    "food",
    "ovqat",
    "taom",
    "pizza",
    "burger",
    "lavash",
    "osh",
    "palov",
    "somsa",
    "sushi",
    "ichimlik",
)

ORDER_KEYWORDS = (
    "buyurt",
    "order",
    "zakaz",
    "olmoqchiman",
    "kerak",
    "bering",
    "yetkaz",
    "dostav",
)


def is_food_order_message(text):
    normalized = (text or "").strip().lower()
    if not normalized:
        return False

    has_food = any(keyword in normalized for keyword in FOOD_KEYWORDS)
    has_order = any(keyword in normalized for keyword in ORDER_KEYWORDS)
    return has_food and has_order


def notify_food_order(user, message_text, chat_id):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_room_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    if not token or not chat_room_id:
        return False

    first_name = (getattr(user, "first_name", "") or "").strip()
    last_name = (getattr(user, "last_name", "") or "").strip()
    full_name = f"{first_name} {last_name}".strip() or "Unknown"
    phone = getattr(user, "phone", "") or "-"
    now_str = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "Food order notification\n"
        f"Time: {now_str}\n"
        f"User: {full_name}\n"
        f"Phone: {phone}\n"
        f"Chat ID: {chat_id}\n"
        f"Message: {message_text}"
    )

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = urllib.parse.urlencode({"chat_id": chat_room_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True
    except Exception:
        logger.exception("Failed to send food order notification to Telegram")
        return False
