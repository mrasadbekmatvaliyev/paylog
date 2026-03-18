from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User, UserDevice

from .models import Message
from .services import create_messages_for_users, send_push_for_message


class MessageAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+10000000011", password="pass")
        self.other_user = User.objects.create_user(phone="+10000000012", password="pass")
        self.message = Message.objects.create(
            user=self.user,
            text="First message",
            link="https://example.com/first",
            link_name="Open first",
        )
        self.unread_message = Message.objects.create(
            user=self.user,
            text="Unread message",
            is_read=False,
        )
        self.other_message = Message.objects.create(
            user=self.other_user,
            text="Other user message",
            is_read=False,
        )

    def test_list_returns_only_current_user_messages(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("message-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({item["id"] for item in response.data}, {self.message.id, self.unread_message.id})

    def test_list_includes_link_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("message-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_message = next(item for item in response.data if item["id"] == self.message.id)
        self.assertEqual(first_message["link_name"], "Open first")

    def test_unread_count_returns_only_current_user_count(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("message-unread-count"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 2)

    def test_read_marks_single_message_as_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("message-read", args=[self.message.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)

    def test_read_all_marks_all_user_messages_as_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("message-read-all"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertFalse(Message.objects.filter(user=self.user, is_read=False).exists())
        self.assertTrue(Message.objects.filter(user=self.other_user, is_read=False).exists())


class MessagePushTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+10000000021", password="pass")
        self.other_user = User.objects.create_user(phone="+10000000022", password="pass")
        UserDevice.objects.create(
            user=self.user,
            fcm_token="token-1",
            platform=UserDevice.PLATFORM_ANDROID,
            device_id="device-1",
        )
        UserDevice.objects.create(
            user=self.other_user,
            fcm_token="token-2",
            platform=UserDevice.PLATFORM_ANDROID,
            device_id="device-2",
        )

    @patch("message.services.send_bulk_fcm_notifications", return_value=(1, 0))
    def test_send_push_for_message_uses_user_devices(self, send_bulk_mock):
        message = Message.objects.create(user=self.user, text="Hello push")
        send_bulk_mock.reset_mock()

        sent, failed = send_push_for_message(message)

        self.assertEqual((sent, failed), (1, 0))
        send_bulk_mock.assert_called_once()
        self.assertEqual(send_bulk_mock.call_args.kwargs["tokens"], ["token-1"])
        self.assertEqual(
            send_bulk_mock.call_args.kwargs["data"],
            {"message_id": str(message.id), "type": "in_app_message", "target": "system_messages"},
        )

    @patch("message.services.send_bulk_fcm_notifications", return_value=(2, 0))
    def test_create_messages_for_users_creates_messages_and_sends_push(self, send_bulk_mock):
        created_count, sent, failed = create_messages_for_users(
            user_qs=User.objects.filter(id__in=[self.user.id, self.other_user.id]),
            text="Bulk message",
            link="https://example.com",
            link_name="Open",
        )

        self.assertEqual(created_count, 2)
        self.assertEqual((sent, failed), (2, 0))
        self.assertEqual(Message.objects.filter(text="Bulk message").count(), 2)
        self.assertEqual(set(send_bulk_mock.call_args.kwargs["tokens"]), {"token-1", "token-2"})
        self.assertEqual(
            send_bulk_mock.call_args.kwargs["data"],
            {
                "type": "in_app_message",
                "target": "system_messages",
                "link": "https://example.com",
                "link_name": "Open",
            },
        )
