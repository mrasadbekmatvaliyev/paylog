from decimal import Decimal
import secrets
import string

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


VIRTUAL_CARD_PREFIX = "9471"
VIRTUAL_CARD_LENGTH = 16
VIRTUAL_CARD_YEARS_VALID = 4


def generate_virtual_card_number():
    suffix_length = VIRTUAL_CARD_LENGTH - len(VIRTUAL_CARD_PREFIX)
    return VIRTUAL_CARD_PREFIX + "".join(
        secrets.choice(string.digits) for _ in range(suffix_length)
    )


def calculate_virtual_card_valid_until(base_date=None):
    base_date = base_date or timezone.localdate()
    try:
        return base_date.replace(year=base_date.year + VIRTUAL_CARD_YEARS_VALID)
    except ValueError:
        # Handle leap day by shifting to Feb 28 on non-leap target year.
        return base_date.replace(
            month=2,
            day=28,
            year=base_date.year + VIRTUAL_CARD_YEARS_VALID,
        )


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class Category(models.Model):
    name = models.CharField(max_length=100)
    name_uz = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    icon_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    class Type(models.TextChoices):
        INCOME = "INCOME", _("Income")
        EXPENSE = "EXPENSE", _("Expense")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    type = models.CharField(max_length=7, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    note = models.TextField(null=True, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.type} {self.amount} {self.currency}"


class DebtorBalance(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="debtor_balance",
    )
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user} - {self.balance} {self.currency}"


class DebtorTransaction(models.Model):
    class Type(models.TextChoices):
        INCOME = "INCOME", _("Income")
        EXPENSE = "EXPENSE", _("Expense")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="debtor_transactions",
    )
    type = models.CharField(max_length=7, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    phone = models.CharField(max_length=20, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class VirtualCard(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="virtual_card",
    )
    card_number = models.CharField(max_length=VIRTUAL_CARD_LENGTH, unique=True)
    valid_until = models.DateField()
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user_id} - {self.card_number}"


