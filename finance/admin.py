from django.contrib import admin

from .models import (
    Category,
    Currency,
    DebtorBalance,
    DebtorTransaction,
    Transaction,
)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon_url", "created_at")
    search_fields = ("name",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("type", "amount", "currency", "category", "user", "date")
    list_filter = ("type", "currency")
    search_fields = ("user__phone", "category__name")


@admin.register(DebtorBalance)
class DebtorBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "balance")
    search_fields = ("user__phone",)
    list_filter = ("currency",)


@admin.register(DebtorTransaction)
class DebtorTransactionAdmin(admin.ModelAdmin):
    list_display = ("type", "amount", "currency", "user", "phone", "date")
    list_filter = ("type", "currency")
    search_fields = ("user__phone", "phone", "note")
