from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from .models import Category, Currency, Transaction


class FinanceAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+10000000001", password="pass")
        self.other_user = User.objects.create_user(phone="+10000000002", password="pass")
        self.currency = Currency.objects.create(code="USD", name="US Dollar", is_active=True)
        self.inactive_currency = Currency.objects.create(code="EUR", name="Euro", is_active=False)
        self.category = Category.objects.create(name="Salary")
        self.other_category = Category.objects.create(name="Food")

    def test_category_list_returns_all(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_category_detail_is_available_to_authenticated_user(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("category-detail", args=[self.category.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.category.id)

    def test_currency_list_returns_active_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("currency-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.currency.id)

    def test_currency_detail_inactive_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("currency-detail", args=[self.inactive_currency.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_detail_is_owner_only(self):
        transaction = Transaction.objects.create(
            user=self.user,
            type=Transaction.Type.INCOME,
            amount=Decimal("10.00"),
            currency=self.currency,
            category=self.category,
            date=date(2025, 1, 1),
        )
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("transaction-detail", args=[transaction.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_allows_any_category(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "type": Transaction.Type.EXPENSE,
            "amount": "12.00",
            "currency": self.currency.id,
            "category": self.other_category.id,
            "note": "Lunch",
            "date": "2025-01-02",
        }
        response = self.client.post(reverse("transaction-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_transaction_requires_active_currency(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "type": Transaction.Type.EXPENSE,
            "amount": "12.00",
            "currency": self.inactive_currency.id,
            "category": self.category.id,
            "note": "Lunch",
            "date": "2025-01-02",
        }
        response = self.client.post(reverse("transaction-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency", response.data)

    def test_transaction_requires_positive_amount(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "type": Transaction.Type.EXPENSE,
            "amount": "0.00",
            "currency": self.currency.id,
            "category": self.category.id,
            "note": "Lunch",
            "date": "2025-01-02",
        }
        response = self.client.post(reverse("transaction-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_category_delete_blocked_when_transactions_exist(self):
        Transaction.objects.create(
            user=self.user,
            type=Transaction.Type.INCOME,
            amount=Decimal("100.00"),
            currency=self.currency,
            category=self.category,
            date=date(2025, 1, 3),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("category-detail", args=[self.category.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Category.objects.filter(id=self.category.id).exists())
