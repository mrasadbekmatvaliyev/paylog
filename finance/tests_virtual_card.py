import re

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User

from .models import (
    VIRTUAL_CARD_LENGTH,
    VIRTUAL_CARD_PREFIX,
    VirtualCard,
    calculate_virtual_card_valid_until,
)


class VirtualCardSignalTests(TestCase):
    def test_virtual_card_is_created_for_new_user(self):
        user = User.objects.create_user(phone="+998900001111", password="pass")

        card = VirtualCard.objects.get(user=user)

        self.assertEqual(len(card.card_number), VIRTUAL_CARD_LENGTH)
        self.assertTrue(card.card_number.startswith(VIRTUAL_CARD_PREFIX))
        self.assertTrue(card.card_number.isdigit())
        self.assertEqual(card.valid_until, calculate_virtual_card_valid_until())
        self.assertEqual(str(card.balance), "0.00")

    def test_virtual_card_is_not_duplicated_on_user_update(self):
        user = User.objects.create_user(phone="+998900001112", password="pass")
        original_card = VirtualCard.objects.get(user=user)

        user.first_name = "Ali"
        user.save(update_fields=["first_name"])

        self.assertEqual(VirtualCard.objects.filter(user=user).count(), 1)
        self.assertEqual(VirtualCard.objects.get(user=user).id, original_card.id)


class VirtualCardApiTests(APITestCase):
    def test_virtual_card_endpoint_returns_holder_name(self):
        user = User.objects.create_user(
            phone="+998900001113",
            password="pass",
            first_name="Aziz",
            last_name="Karimov",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("virtual-card"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["holder_first_name"], "Aziz")
        self.assertEqual(response.data["holder_last_name"], "Karimov")
        self.assertEqual(len(response.data["card_number"]), VIRTUAL_CARD_LENGTH)
        self.assertTrue(response.data["card_number"].startswith(VIRTUAL_CARD_PREFIX))
        self.assertEqual(response.data["balance"], "0.00")
        self.assertTrue(re.fullmatch(r"\d{2}/\d{2}", response.data["valid_until"]))
