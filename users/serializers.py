from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from finance.models import Currency
from finance.serializers import CurrencyLiteSerializer
from .models import User, UserDevice


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)
    code = serializers.RegexField(regex=r"^\d{5}$")


class DeleteAccountVerifySerializer(serializers.Serializer):
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

class AIChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)

class DeviceRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            "fcm_token",
            "platform",
            "notifications_enabled",
            "device_id",
            "locale",
            "app_version",
        ]

    def validate_fcm_token(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("fcm_token is required.")
        return value

    def validate_device_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("device_id is required.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        fcm_token = validated_data["fcm_token"]
        device_id = validated_data["device_id"]

        with transaction.atomic():
            instance = (
                UserDevice.objects.select_for_update()
                .filter(Q(device_id=device_id) | Q(fcm_token=fcm_token))
                .first()
            )
            if instance:
                for field, value in validated_data.items():
                    setattr(instance, field, value)
                instance.user = user
                instance.save()
                return instance

            return UserDevice.objects.create(user=user, **validated_data)

