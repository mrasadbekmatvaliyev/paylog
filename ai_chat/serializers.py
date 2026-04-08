from rest_framework import serializers

from .models import Chat, Message


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ("id", "title", "created_at", "updated_at")


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "chat", "role", "content", "created_at")
        read_only_fields = ("id", "created_at")


class SendMessageSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    content = serializers.CharField()

    def validate_content(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Content must not be empty.")
        return cleaned
