from decimal import Decimal

from django.db.models import Case, DecimalField, Sum, Value, When
from rest_framework import status
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from finance.models import DebtorTransaction
from finance.serializers import DebtorTransactionSerializer
from finance.services import get_balance_data_for_queryset

from .models import DebtorChat, PayNoteChat
from .serializers import ChatListSerializer, DebtorChatSerializer, DebtorChatCreateSerializer


class ChatViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        paynote, _ = PayNoteChat.objects.get_or_create(
            owner=request.user,
            defaults={"message": None, "photo_url": None},
        )

        debtors = DebtorChat.objects.filter(owner=request.user).order_by("-updated_at")

        debtor_serializer = DebtorChatSerializer(
            debtors,
            many=True,
            context={"request": request},
        )

        results = [
            ChatListSerializer(paynote).data,
            *debtor_serializer.data,
        ]

        return Response({"results": results})

    def _get_totals(self, queryset):
        totals = queryset.aggregate(
            income=Sum(
                Case(
                    When(type=DebtorTransaction.Type.INCOME, then="amount"),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            expense=Sum(
                Case(
                    When(type=DebtorTransaction.Type.EXPENSE, then="amount"),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
        )
        return {
            "income_total": totals["income"] or Decimal("0.00"),
            "expense_total": totals["expense"] or Decimal("0.00"),
        }

    def retrieve(self, request, pk=None):
        chat_type = request.query_params.get("type")

        paynote = None
        debtor = None

        if chat_type == "PAYNOTE":
            paynote = PayNoteChat.objects.filter(owner=request.user, pk=pk).first()
        elif chat_type == "DEBTOR":
            debtor = DebtorChat.objects.filter(owner=request.user, pk=pk).first()
        elif chat_type:
            return Response(
                {"detail": _("Invalid chat type.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            paynote = PayNoteChat.objects.filter(owner=request.user, pk=pk).first()
            debtor = DebtorChat.objects.filter(owner=request.user, pk=pk).first()
            if paynote and debtor:
                return Response(
                    {"detail": _("Chat type is required for this id.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if paynote:
            return Response(ChatListSerializer(paynote).data)

        if not debtor:
            return Response(
                {"detail": _("Chat not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        tx_qs = DebtorTransaction.objects.filter(user=request.user, phone=debtor.phone)
        totals = self._get_totals(tx_qs)
        balance_data = get_balance_data_for_queryset(tx_qs)

        return Response(
            {
                "transactions": DebtorTransactionSerializer(tx_qs, many=True).data,
                "totals": totals,
                "balance": (
                    balance_data
                    if balance_data["currency"]
                    else {"balance": 0, "currency": None}
                ),
            }
        )


class DebtorViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = DebtorChatCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if DebtorChat.objects.filter(owner=request.user, phone=data["phone"]).exists():
            return Response(
                {"detail": _("Debtor already exists.")},
                status=status.HTTP_409_CONFLICT,
            )

        debtor = DebtorChat.objects.create(
            owner=request.user,
            full_name=data["full_name"],
            phone=data["phone"],
            photo_url=data.get("photo_url"),
            message=None,
        )

        serializer = DebtorChatSerializer(debtor, context={"request": request})

        return Response(
            {"chat": serializer.data},
            status=status.HTTP_201_CREATED,
        )
