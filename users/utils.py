from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
import logging
import random
import urllib.parse
import urllib.request


OTP_EXPIRES_MINUTES = 2
MAX_OTP_ATTEMPTS = 5


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)


def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
    payload = {"success": False, "error": {"message": message}}
    if errors is not None:
        payload["error"]["details"] = errors
    return Response(payload, status=status_code)


def generate_otp_code():
    return f"{random.randint(0, 99999):05d}"


def otp_expiration_time():
    return timezone.now() + timezone.timedelta(minutes=OTP_EXPIRES_MINUTES)


def get_max_attempts():
    return getattr(settings, "MAX_OTP_ATTEMPTS", MAX_OTP_ATTEMPTS)


def is_telegram_configured():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    return bool(token and chat_id)


def send_telegram_otp(phone, code, lang="en"):
    if not is_telegram_configured():
        logging.getLogger(__name__).warning("Telegram bot not configured.")
        return False
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    messages = {
        "en": f"Paylog Platform: Operation confirmation code: {code}",
        "ru": f"Платформа Paylog: Код подтверждения операции: {code}",
        "uz": f"Paylog platformasi: Amaliyotni tasdiqlash kodi: {code}",
    }
    message = messages.get(lang) or messages["en"]

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        request = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
        return True
    except Exception:
        logging.getLogger(__name__).exception("Failed to send SMS via Telegram.")
        return False
