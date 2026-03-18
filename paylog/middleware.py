import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


class TelegramApiActivityMiddleware:
    """
    Sends API activity events to Telegram:
    - which endpoint was called
    - what action was attempted (HTTP method)
    - user name and phone (when available)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._notify(request, response)
        return response

    def _notify(self, request, response):
        if not request.path.startswith("/api/"):
            return

        if not getattr(settings, "TELEGRAM_LOGGING_ENABLED", False):
            return

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return

        user_name = ""
        phone = ""
        user = getattr(request, "user", None)

        if user and getattr(user, "is_authenticated", False):
            first_name = (getattr(user, "first_name", "") or "").strip()
            last_name = (getattr(user, "last_name", "") or "").strip()
            user_name = f"{first_name} {last_name}".strip() or "Noma'lum"
            phone = getattr(user, "phone", "") or ""
        else:
            payload = self._extract_payload(request)
            first_name = (payload.get("first_name") or "").strip()
            last_name = (payload.get("last_name") or "").strip()
            user_name = f"{first_name} {last_name}".strip() or "Noma'lum"
            phone = str(payload.get("phone") or "")

        method = request.method.upper()
        action = self._action_name(method)
        endpoint = request.path
        status_code = getattr(response, "status_code", 0)
        now_str = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")

        text = (
            "Paylog API activity\n"
            f"Vaqt: {now_str}\n"
            f"User: {user_name}\n"
            f"Telefon: {phone or '-'}\n"
            f"Amal: {action}\n"
            f"Method: {method}\n"
            f"API: {endpoint}\n"
            f"Status: {status_code}"
        )
        self._send_telegram_message(token, chat_id, text)

    @staticmethod
    def _extract_payload(request):
        if request.method.upper() not in {"POST", "PUT", "PATCH"}:
            return {}
        content_type = (request.META.get("CONTENT_TYPE") or "").lower()
        if "application/json" not in content_type:
            return {}
        try:
            raw = request.body.decode("utf-8") if request.body else ""
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    @staticmethod
    def _action_name(method):
        actions = {
            "GET": "Ma'lumot ko'rish",
            "POST": "Yangi amal yaratish",
            "PUT": "Ma'lumotni to'liq yangilash",
            "PATCH": "Ma'lumotni qisman yangilash",
            "DELETE": "Ma'lumotni o'chirish",
        }
        return actions.get(method, "API ga murojaat")

    @staticmethod
    def _send_telegram_message(token, chat_id, text):
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
            req = urllib.request.Request(url, data=payload)
            with urllib.request.urlopen(req, timeout=5) as res:
                res.read()
        except Exception:
            logger.exception("Failed to send API activity to Telegram.")
