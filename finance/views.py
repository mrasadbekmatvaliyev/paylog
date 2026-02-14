from decimal import Decimal

from datetime import timedelta

from django.db.models import Case, DecimalField, Sum, Value, When
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import viewsets, permissions
from rest_framework.response import Response

from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from .models import Category, Currency, Transaction, DebtorTransaction
from .pagination import DefaultPagination
from .permissions import IsAuthenticated, IsOwner
from .serializers import (
    CategorySerializer,
    CurrencySerializer,
    TransactionReadSerializer,
    TransactionWriteSerializer,
    
    DebtorTransactionSerializer,
)
from .services import apply_transaction_to_balance, get_balance_data_for_queryset, recompute_debtor_balance



class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if Transaction.objects.filter(category=category).exists():
            raise ValidationError({"detail": _("Cannot delete category because it is used by transactions.")})
        return super().destroy(request, *args, **kwargs)


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Currency.objects.filter(is_active=True)


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = DefaultPagination

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return TransactionReadSerializer
        return TransactionWriteSerializer

    def get_queryset(self):
        queryset = (
            Transaction.objects.filter(user=self.request.user)
            .select_related("currency", "category")
        )

        period_param = self.request.query_params.get("period")
        type_param = self.request.query_params.get("type")
        if type_param:
            if type_param not in Transaction.Type.values:
                raise ValidationError({"type": _("Invalid transaction type.")})
            queryset = queryset.filter(type=type_param)

        category_id = self.request.query_params.get("categoryId")
        if category_id:
            if not category_id.isdigit():
                raise ValidationError({"categoryId": _("Invalid category id.")})
            queryset = queryset.filter(category_id=int(category_id))

        currency_id = self.request.query_params.get("currency")
        if currency_id:
            if not currency_id.isdigit():
                raise ValidationError({"currency": _("Invalid currency id.")})
            queryset = queryset.filter(currency_id=int(currency_id))

        from_param = self.request.query_params.get("from")
        to_param = self.request.query_params.get("to")
        if period_param and (from_param or to_param):
            raise ValidationError({"period": _("Cannot combine period with from/to filters.")})

        if period_param:
            period_value = period_param.lower()
            today = timezone.localdate()
            if period_value == "daily":
                queryset = queryset.filter(date=today)
            elif period_value == "weekly":
                queryset = queryset.filter(date__gte=today - timedelta(days=6), date__lte=today)
            elif period_value == "monthly":
                queryset = queryset.filter(date__year=today.year, date__month=today.month)
            else:
                raise ValidationError({"period": _("Invalid period. Use daily, weekly, or monthly.")})

        if from_param:
            from_date = parse_date(from_param)
            if not from_date:
                raise ValidationError({"from": _("Invalid from date.")})
            queryset = queryset.filter(date__gte=from_date)

        if to_param:
            to_date = parse_date(to_param)
            if not to_date:
                raise ValidationError({"to": _("Invalid to date.")})
            queryset = queryset.filter(date__lte=to_date)

        return queryset

    def _get_totals(self, queryset):
        totals = queryset.aggregate(
            income=Sum(
                Case(
                    When(type=Transaction.Type.INCOME, then="amount"),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            expense=Sum(
                Case(
                    When(type=Transaction.Type.EXPENSE, then="amount"),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
        )
        return {
            "income_total": totals["income"] or Decimal("0.00"),
            "expense_total": totals["expense"] or Decimal("0.00"),
        }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        totals = self._get_totals(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["totals"] = totals
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "totals": totals})

    def perform_create(self, serializer):
        serializer.save()



class DebtorTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = DebtorTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DebtorTransaction.objects.filter(user=self.request.user)

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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        totals = self._get_totals(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["totals"] = totals
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "totals": totals})

    def perform_create(self, serializer):
        tx = serializer.save(user=self.request.user)
        apply_transaction_to_balance(user=self.request.user, tx=tx)

    def perform_update(self, serializer):
        serializer.save()
        recompute_debtor_balance(user=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()
        recompute_debtor_balance(user=self.request.user)

    @action(detail=False, methods=["get"])
    def balance(self, request):
        balance_data = get_balance_data_for_queryset(
            DebtorTransaction.objects.filter(user=request.user)
        )
        if balance_data["currency"] is None:
            return Response({"balance": 0})

        return Response(balance_data)
