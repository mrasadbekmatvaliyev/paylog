from rest_framework import serializers

from finance.models import DebtorTransaction
from finance.services import get_balance_data_for_queryset

from .models import PayNoteChat, DebtorChat


class ChatListSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = PayNoteChat
        fields = (
            "id",
            "type",
            "message",
            "photo_url",
            "created_at",
            "updated_at",
        )

    def get_type(self, obj):
        return "PAYNOTE"


class DebtorChatSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()

    class Meta:
        model = DebtorChat
        fields = (
            "id",
            "type",
            "full_name",
            "phone",
            "photo_url",
            "message",
            "total_balance",
            "created_at",
        )

    def get_type(self, obj):
        return "DEBTOR"

    def get_total_balance(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        balance_data = get_balance_data_for_queryset(
            DebtorTransaction.objects.filter(user=request.user, phone=obj.phone)
        )
        if balance_data["currency"] is None:
            return {"balance": 0, "currency": None}

        return balance_data


class DebtorChatCreateSerializer(serializers.ModelSerializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,32}$", max_length=32, min_length=3)

    class Meta:
        model = DebtorChat
        fields = ("full_name", "phone", "photo_url")
