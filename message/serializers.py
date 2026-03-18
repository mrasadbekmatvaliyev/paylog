from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "text", "link", "link_name", "is_read", "created_at"]
        read_only_fields = fields
