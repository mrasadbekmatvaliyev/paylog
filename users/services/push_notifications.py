from pathlib import Path
import logging
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)
_firebase_app = None


def _resolve_service_account_path() -> Path | None:
    raw_path = getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", "").strip()
    if not raw_path:
        return None

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(settings.BASE_DIR) / path
    return path


def _get_firebase_app():
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app, ""

    service_account_path = _resolve_service_account_path()
    if service_account_path is None:
        return None, "FCM_SERVICE_ACCOUNT_PATH is not configured."
    if not service_account_path.exists():
        return None, f"Service account file not found: {service_account_path}"

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None, "firebase-admin package is not installed."

    try:
        _firebase_app = firebase_admin.initialize_app(
            credentials.Certificate(str(service_account_path))
        )
        return _firebase_app, ""
    except ValueError:
        # App already initialized in this process.
        _firebase_app = firebase_admin.get_app()
        return _firebase_app, ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("Firebase app initialization failed")
        return None, str(exc)


def send_fcm_notification(token: str, title: str, body: str, data: dict | None = None) -> tuple[bool, str]:
    app, init_error = _get_firebase_app()
    if init_error:
        return False, init_error

    try:
        from firebase_admin import messaging

        normalized_data = {str(k): str(v) for k, v in (data or {}).items()}
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=normalized_data,
        )
        messaging.send(message, app=app)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("FCM send failed for token: %s", token)
        return False, str(exc)


def send_bulk_fcm_notifications(tokens: Iterable[str], title: str, body: str, data: dict | None = None) -> tuple[int, int]:
    sent = 0
    failed = 0
    for token in tokens:
        ok, _ = send_fcm_notification(token=token, title=title, body=body, data=data)
        if ok:
            sent += 1
        else:
            failed += 1
    return sent, failed
