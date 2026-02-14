from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP, TelegramOTP, User
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    TelegramOTPVerifySerializer,
    TelegramOTPSendSerializer,
)
from .utils import (
    error_response,
    generate_otp_code,
    get_max_attempts,
    is_telegram_configured,
    OTP_EXPIRES_MINUTES,
    otp_expiration_time,
    send_telegram_otp,
    success_response,
)



def get_request_lang(request):
    raw = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    raw = raw.lower()
    for part in raw.split(","):
        code = part.strip().split(";")[0]
        if code.startswith("uz"):
            return "uz"
        if code.startswith("ru"):
            return "ru"
        if code.startswith("en"):
            return "en"
    return "en"


class OTPSendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_("Invalid request data."), status.HTTP_400_BAD_REQUEST, serializer.errors)
        phone = serializer.validated_data["phone"]
        lang = get_request_lang(request)
        if not is_telegram_configured():
            return error_response(_("Telegram bot not configured."), status.HTTP_503_SERVICE_UNAVAILABLE)

        active_otp = (
            OTP.objects.filter(phone=phone, is_used=False, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if active_otp:
            return error_response(
                _("SMS already sent. Please wait before requesting again."),
                status.HTTP_400_BAD_REQUEST,
            )

        OTP.objects.filter(phone=phone, is_used=False).update(is_used=True)
        otp = OTP.objects.create(
            phone=phone,
            code=generate_otp_code(),
            expires_at=otp_expiration_time(),
        )
        if not send_telegram_otp(phone, otp.code, lang):
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return error_response(_("Failed to send SMS."), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return success_response(_("SMS sent successfully."))


class OTPResendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_("Invalid request data."), status.HTTP_400_BAD_REQUEST, serializer.errors)
        phone = serializer.validated_data["phone"]
        lang = get_request_lang(request)
        if not is_telegram_configured():
            return error_response(_("Telegram bot not configured."), status.HTTP_503_SERVICE_UNAVAILABLE)

        OTP.objects.filter(phone=phone, is_used=False).update(is_used=True)
        otp = OTP.objects.create(
            phone=phone,
            code=generate_otp_code(),
            expires_at=otp_expiration_time(),
        )
        if not send_telegram_otp(phone, otp.code, lang):
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return error_response(_("Failed to send SMS."), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return success_response(_("SMS resent successfully."))


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_("Invalid request data."), status.HTTP_400_BAD_REQUEST, serializer.errors)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        otp = (
            OTP.objects.filter(phone=phone, is_used=False, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if not otp:
            return error_response(_("Invalid or expired SMS."), status.HTTP_400_BAD_REQUEST)

        if otp.attempts >= get_max_attempts():
            return error_response(
                _("Too many attempts. Please request a new SMS."),
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return error_response(_("Invalid or expired SMS."), status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        user, user_created = User.objects.get_or_create(phone=phone, defaults={"is_active": True})
        if not user.is_active:
            return error_response(_("User is inactive."), status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ProfileSerializer(user).data,
            "new_user": not bool(user.first_name),
        }
        return success_response(_("SMS verified successfully."), data)


class TelegramOTPSendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramOTPSendSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_("Invalid request data."), status.HTTP_400_BAD_REQUEST, serializer.errors)

        telegram_user_id = serializer.validated_data["telegram_user_id"]
        phone = serializer.validated_data["phone"]
        first_name = serializer.validated_data.get("first_name", "")
        last_name = serializer.validated_data.get("last_name", "")

        user = User.objects.filter(telegram_user_id=telegram_user_id).first()
        if user:
            if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
                return error_response(_("Phone already in use."), status.HTTP_400_BAD_REQUEST)
        else:
            user = User.objects.filter(phone=phone, telegram_user_id__isnull=True).first()
            if not user:
                user = User()

        updates = []
        if user.telegram_user_id != telegram_user_id:
            user.telegram_user_id = telegram_user_id
            updates.append("telegram_user_id")
        if phone and user.phone != phone:
            user.phone = phone
            updates.append("phone")
        if first_name != user.first_name:
            user.first_name = first_name
            updates.append("first_name")
        if last_name != user.last_name:
            user.last_name = last_name
            updates.append("last_name")
        if user.pk is None:
            user.is_active = True
            user.save()
        elif updates:
            user.save(update_fields=updates)

        if not user.is_active:
            return error_response(_("User is inactive."), status.HTTP_403_FORBIDDEN)

        active_otp = (
            TelegramOTP.objects.filter(
                telegram_user_id=telegram_user_id,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if active_otp:
            return error_response(
                _("SMS already sent. Please wait before requesting again."),
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        TelegramOTP.objects.filter(telegram_user_id=telegram_user_id, is_used=False).update(is_used=True)
        otp = TelegramOTP.objects.create(
            telegram_user_id=telegram_user_id,
            code=generate_otp_code(),
            expires_at=otp_expiration_time(),
        )
        return Response({"otp": otp.code, "expires_in": OTP_EXPIRES_MINUTES * 60}, status=status.HTTP_200_OK)


class TelegramOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_("Invalid request data."), status.HTTP_400_BAD_REQUEST, serializer.errors)

        telegram_user_id = serializer.validated_data["telegram_user_id"]
        code = serializer.validated_data["otp"]
        otp = (
            TelegramOTP.objects.filter(
                telegram_user_id=telegram_user_id,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if not otp:
            return error_response(_("Invalid or expired SMS."), status.HTTP_400_BAD_REQUEST)

        if otp.attempts >= get_max_attempts():
            return error_response(
                _("Too many attempts. Please request a new SMS."),
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        user = User.objects.filter(telegram_user_id=otp.telegram_user_id).first()
        if not user:
            return error_response(_("User not found."), status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return error_response(_("User is inactive."), status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return success_response(
            _("Profile fetched successfully."),
            {"user": ProfileSerializer(request.user).data},
        )

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(_("Invalid profile data."), status.HTTP_400_BAD_REQUEST, serializer.errors)
        serializer.save()
        return success_response(
            _("Profile updated successfully."),
            {"user": ProfileSerializer(request.user).data},
        )
