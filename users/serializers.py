from rest_framework import serializers

from finance.models import Currency
from finance.serializers import CurrencyLiteSerializer
from .models import User


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)
    code = serializers.RegexField(regex=r"^\d{5}$")


class TelegramOTPSendSerializer(serializers.Serializer):
    telegram_user_id = serializers.RegexField(regex=r"^\d{1,32}$", max_length=32)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)


class TelegramOTPVerifySerializer(serializers.Serializer):
    telegram_user_id = serializers.RegexField(regex=r"^\d{1,32}$", max_length=32)
    otp = serializers.RegexField(regex=r"^\d{5}$")


class ProfileSerializer(serializers.ModelSerializer):
    default_currency = CurrencyLiteSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "avatar", "is_premium", "default_currency"]
        read_only_fields = ["phone", "is_premium"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    default_currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.filter(is_active=True),
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "avatar", "default_currency"]
