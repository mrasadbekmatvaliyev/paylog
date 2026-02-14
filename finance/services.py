# services.py
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, Value, When

from .models import DebtorBalance, DebtorTransaction


def _signed_amount_expression():
    return Case(
        When(type=DebtorTransaction.Type.INCOME, then=F("amount")),
        When(type=DebtorTransaction.Type.EXPENSE, then=-F("amount")),
        default=Value(0),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def get_balance_data_for_queryset(qs):
    tx = qs.select_related("currency").first()
    if not tx:
        return {"balance": Decimal("0.00"), "currency": None}

    total = qs.aggregate(total=Sum(_signed_amount_expression()))["total"] or Decimal("0.00")
    return {"balance": total, "currency": str(tx.currency)}


def recompute_debtor_balance(*, user):
    qs = DebtorTransaction.objects.filter(user=user)
    balance_data = get_balance_data_for_queryset(qs)

    if balance_data["currency"] is None:
        DebtorBalance.objects.filter(user=user).delete()
        return None

    balance_obj, _ = DebtorBalance.objects.update_or_create(
        user=user,
        defaults={
            "balance": balance_data["balance"],
            "currency_id": qs.values_list("currency_id", flat=True).first(),
        },
    )
    return balance_obj


def apply_transaction_to_balance(*, user, tx: DebtorTransaction):
    return recompute_debtor_balance(user=user)
