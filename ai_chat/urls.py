from django.urls import path

from .views import (
    ChatDetailAPIView,
    ChatListAPIView,
    ChatMessagesListAPIView,
    SendMessageAPIView,
)


urlpatterns = [
    path("ai-chat/messages/", SendMessageAPIView.as_view(), name="ai-chat-send-message"),
    path("ai-chat/chats/", ChatListAPIView.as_view(), name="ai-chat-list"),
    path("ai-chat/chats/<int:pk>/", ChatDetailAPIView.as_view(), name="ai-chat-detail"),
    path("ai-chat/chats/<int:pk>/messages/", ChatMessagesListAPIView.as_view(), name="ai-chat-messages"),
]
