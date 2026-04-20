from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from finance.models import VirtualCard
from users.models import User

from .models import Category, Order, Product


class OrderVirtualCardPaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+998901112233", password="pass")
        self.category = Category.objects.create(name="Food")
        self.product = Product.objects.create(
            name="Burger",
            price=Decimal("25000.00"),
            category=self.category,
            stock=10,
            is_available=True,
        )
        self.url = reverse("market-order-list")
        self.client.force_authenticate(user=self.user)

    def test_cash_order_is_created_without_charging_virtual_card(self):
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("0.00")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 2,
                "location": "Tashkent, Chilonzor 10",
                "latitude": "41.285680",
                "longitude": "69.203460",
                "note": "Call before delivery",
                "payment_method": Order.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["location"], "Tashkent, Chilonzor 10")
        self.assertEqual(response.data["latitude"], "41.285680")
        self.assertEqual(response.data["longitude"], "69.203460")
        self.assertEqual(response.data["note"], "Call before delivery")
        self.assertEqual(response.data["payment_method"], Order.PaymentMethod.CASH)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.location, "Tashkent, Chilonzor 10")
        self.assertEqual(order.latitude, Decimal("41.285680"))
        self.assertEqual(order.longitude, Decimal("69.203460"))
        self.assertEqual(order.note, "Call before delivery")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertTrue(self.product.is_available)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("0.00"))

    def test_order_rejects_invalid_coordinates(self):
        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 1,
                "latitude": "91.000000",
                "longitude": "69.203460",
                "payment_method": Order.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("latitude", response.data)

    def test_virtual_card_order_is_created_when_balance_is_enough(self):
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("60000.00")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 2,
                "payment_method": Order.PaymentMethod.VIRTUAL_CARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["payment_method"], Order.PaymentMethod.VIRTUAL_CARD)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertTrue(self.product.is_available)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("10000.00"))

    def test_order_rejects_when_product_stock_is_not_enough(self):
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("500000.00")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 11,
                "payment_method": Order.PaymentMethod.VIRTUAL_CARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.product.is_available)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("500000.00"))

    def test_order_marks_product_unavailable_when_stock_reaches_zero(self):
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("250000.00")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 10,
                "payment_method": Order.PaymentMethod.VIRTUAL_CARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertFalse(self.product.is_available)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("0.00"))

    def test_virtual_card_order_is_rejected_when_balance_is_not_enough(self):
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("49999.99")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 2,
                "payment_method": Order.PaymentMethod.VIRTUAL_CARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("balance", response.data)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.product.is_available)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("49999.99"))

    def test_virtual_card_order_uses_discount_price_when_available(self):
        self.product.discount_price = Decimal("20000.00")
        self.product.save(update_fields=["discount_price"])
        card = VirtualCard.objects.get(user=self.user)
        card.balance = Decimal("40000.00")
        card.save(update_fields=["balance"])

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "quantity": 2,
                "payment_method": Order.PaymentMethod.VIRTUAL_CARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("0.00"))
