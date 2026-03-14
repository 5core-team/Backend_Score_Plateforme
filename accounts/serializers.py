from rest_framework import serializers
from .models import User

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "role",
            "email",
            "username",
            "password_changed",
            "photo",
            "is_active",
            ]
        read_only_fields = ["email","role", "is_active", "password_chaneged"]