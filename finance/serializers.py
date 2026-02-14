from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import Category, Currency, Transaction, DebtorTransaction, DebtorBalance


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name_uz",
            "name_ru",
            "name_en",
            "icon_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "name_uz": {
                "error_messages": {
                    "blank": _("Category name (uz) is required."),
                    "required": _("Category name (uz) is required."),
                }
            },
            "name_ru": {
                "error_messages": {
                    "blank": _("Category name (ru) is required."),
                    "required": _("Category name (ru) is required."),
                }
            },
            "name_en": {
                "error_messages": {
                    "blank": _("Category name (en) is required."),
                    "required": _("Category name (en) is required."),
                }
            }
        }

    def _validate_unique_name(self, field_name, value):
        queryset = Category.objects.filter(**{field_name: value})
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(_("Category with this name already exists."))
        return value

    def validate_name_uz(self, value):
        return self._validate_unique_name("name_uz", value)

    def validate_name_ru(self, value):
        return self._validate_unique_name("name_ru", value)

    def validate_name_en(self, value):
        return self._validate_unique_name("name_en", value)

    def _sync_name(self, validated_data):
        primary_name = (
            validated_data.get("name_en")
            or validated_data.get("name_uz")
            or validated_data.get("name_ru")
        )
        if primary_name:
            validated_data["name"] = primary_name

    def create(self, validated_data):
        self._sync_name(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._sync_name(validated_data)
        return super().update(instance, validated_data)


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CurrencyLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["code"]


class CategoryLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name_uz", "name_ru", "name_en", "icon_url"]


class TransactionReadSerializer(serializers.ModelSerializer):
    currency = CurrencyLiteSerializer(read_only=True)
    category = CategoryLiteSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "amount",
            "currency",
            "category",
            "note",
            "date",
        ]
        read_only_fields = fields


class TransactionWriteSerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(
        choices=Transaction.Type.choices,
        error_messages={"invalid_choice": _("Invalid transaction type.")},
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        error_messages={"invalid": _("Invalid amount.")},
    )
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        error_messages={
            "does_not_exist": _("Currency does not exist."),
            "incorrect_type": _("Invalid currency id."),
            "invalid": _("Invalid currency id."),
        },
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        error_messages={
            "does_not_exist": _("Category does not exist."),
            "incorrect_type": _("Invalid category id."),
            "invalid": _("Invalid category id."),
        },
    )
    date = serializers.DateField(
        error_messages={
            "invalid": _("Invalid date."),
            "required": _("Date is required."),
        }
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "type",
            "amount",
            "currency",
            "category",
            "note",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Amount must be greater than zero."))
        return value

    def validate_category(self, value):
        return value

    def validate_currency(self, value):
        if not value.is_active:
            raise serializers.ValidationError(_("Selected currency is inactive."))
        return value

    def create(self, validated_data):
        return Transaction.objects.create(user=self.context["request"].user, **validated_data)


class DebtorTransactionSerializer(serializers.ModelSerializer):
    phone = serializers.RegexField(regex=r"^\+?\d{3,20}$", max_length=20, min_length=3)

    class Meta:
        model = DebtorTransaction
        fields = [
            "id",
            "type",
            "amount",
            "currency",
            "phone",
            "note",
            "date",
        ]


class DebtorBalanceSerializer(serializers.ModelSerializer):
    currency = serializers.StringRelatedField()

    class Meta:
        model = DebtorBalance
        fields = ["balance", "currency"]
