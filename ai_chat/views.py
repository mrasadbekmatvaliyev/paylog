from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer, SendMessageSerializer
from .services.ai_service import AIServiceError, OpenAICompatibleAIService
from .services.product_search_service import (
    find_best_product_from_message,
    format_product_reply,
    serialize_product,
)
from .services.telegram_service import is_food_order_message, notify_food_order


ai_service = OpenAICompatibleAIService()


class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat_id = serializer.validated_data.get("chat_id")
        content = serializer.validated_data["content"]

        if chat_id is None:
            chat = Chat.objects.create(user=request.user, title=content[:40])
            created_new_chat = True
        else:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
            created_new_chat = False

        user_message = Message.objects.create(
            chat=chat,
            role=Message.Role.USER,
            content=content,
        )

        if is_food_order_message(content):
            notify_food_order(request.user, content, chat.id)

        best_product = find_best_product_from_message(content)
        best_product_data = serialize_product(best_product)

        if best_product is not None:
            assistant_message = Message.objects.create(
                chat=chat,
                role=Message.Role.ASSISTANT,
                content=format_product_reply(best_product),
            )
            assistant_data = MessageSerializer(assistant_message).data
            ai_error = None
            response_status = status.HTTP_201_CREATED
        else:
            allowed_phone = getattr(settings, "AI_CHAT_ALLOWED_PHONE", "")
            if allowed_phone and request.user.phone == allowed_phone:
                assistant_message = Message.objects.create(
                    chat=chat,
                    role=Message.Role.ASSISTANT,
                    content=getattr(settings, "AI_CHAT_STATIC_REPLY", ""),
                )
                assistant_data = MessageSerializer(assistant_message).data
                ai_error = None
                response_status = status.HTTP_201_CREATED
            else:
                history = list(
                    Message.objects.filter(chat=chat)
                    .order_by("created_at", "id")
                    .values("role", "content")
                )

                try:
                    ai_reply = ai_service.generate_reply(history)
                    assistant_message = Message.objects.create(
                        chat=chat,
                        role=Message.Role.ASSISTANT,
                        content=ai_reply,
                    )
                    assistant_data = MessageSerializer(assistant_message).data
                    ai_error = None
                    response_status = status.HTTP_201_CREATED
                except AIServiceError as exc:
                    assistant_data = None
                    ai_error = str(exc)
                    response_status = status.HTTP_502_BAD_GATEWAY

        return Response(
            {
                "chat": ChatSerializer(chat).data,
                "created_new_chat": created_new_chat,
                "user_message": MessageSerializer(user_message).data,
                "assistant_message": assistant_data,
                "best_product": best_product_data,
                "ai_error": ai_error,
            },
            status=response_status,
        )


class ChatListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user).order_by("-updated_at", "-id")


class ChatDetailAPIView(RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)


class ChatMessagesListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat = get_object_or_404(Chat, id=self.kwargs["pk"], user=self.request.user)
        return Message.objects.filter(chat=chat).order_by("created_at", "id")
