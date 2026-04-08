from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User

from .models import Chat, Message


class AIChatAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+19990000001", password="pass")
        self.other_user = User.objects.create_user(phone="+19990000002", password="pass")

    @patch("ai_chat.views.ai_service.generate_reply", return_value="Hello from AI")
    def test_first_message_creates_new_chat(self, generate_reply_mock):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("ai-chat-send-message"),
            {"chat_id": None, "content": "Hello"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created_new_chat"])
        self.assertEqual(Chat.objects.filter(user=self.user).count(), 1)
        chat = Chat.objects.get(user=self.user)
        self.assertEqual(chat.title, "Hello")

        msgs = Message.objects.filter(chat=chat).order_by("created_at", "id")
        self.assertEqual(msgs.count(), 2)
        self.assertEqual(msgs[0].role, Message.Role.USER)
        self.assertEqual(msgs[0].content, "Hello")
        self.assertEqual(msgs[1].role, Message.Role.ASSISTANT)
        self.assertEqual(msgs[1].content, "Hello from AI")
        generate_reply_mock.assert_called_once()

    @patch("ai_chat.views.notify_food_order")
    @patch("ai_chat.views.ai_service.generate_reply", return_value="Qabul qilindi")
    def test_food_order_message_triggers_telegram_notification(self, generate_reply_mock, notify_food_order_mock):
        self.client.force_authenticate(user=self.user)
        content = "Menga pizza buyurtma bermoqchiman"

        response = self.client.post(
            reverse("ai-chat-send-message"),
            {"chat_id": None, "content": content},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_chat_id = response.data["chat"]["id"]
        notify_food_order_mock.assert_called_once_with(self.user, content, created_chat_id)
        generate_reply_mock.assert_called_once()

    @patch("ai_chat.views.ai_service.generate_reply", return_value="Second reply")
    def test_second_message_uses_existing_chat(self, generate_reply_mock):
        chat = Chat.objects.create(user=self.user, title="Existing")

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("ai-chat-send-message"),
            {"chat_id": chat.id, "content": "Second"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["created_new_chat"])
        self.assertEqual(response.data["chat"]["id"], chat.id)
        self.assertEqual(Message.objects.filter(chat=chat).count(), 2)
        generate_reply_mock.assert_called_once()

    def test_user_cannot_access_another_users_chat(self):
        other_chat = Chat.objects.create(user=self.other_user, title="Secret")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("ai-chat-detail", args=[other_chat.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_chat_list_works(self):
        older = Chat.objects.create(user=self.user, title="Older")
        newer = Chat.objects.create(user=self.user, title="Newer")
        Chat.objects.create(user=self.other_user, title="Other")

        Chat.objects.filter(id=older.id).update(updated_at=timezone.now() - timedelta(days=1))
        Chat.objects.filter(id=newer.id).update(updated_at=timezone.now())

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("ai-chat-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual([item["id"] for item in response.data], [newer.id, older.id])

    def test_messages_list_works(self):
        chat = Chat.objects.create(user=self.user, title="My Chat")
        Message.objects.create(chat=chat, role=Message.Role.SYSTEM, content="System")
        Message.objects.create(chat=chat, role=Message.Role.USER, content="Hi")
        Message.objects.create(chat=chat, role=Message.Role.ASSISTANT, content="Hello")

        other_chat = Chat.objects.create(user=self.other_user, title="Other")
        Message.objects.create(chat=other_chat, role=Message.Role.USER, content="Not mine")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("ai-chat-messages", args=[chat.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual([item["content"] for item in response.data], ["System", "Hi", "Hello"])
