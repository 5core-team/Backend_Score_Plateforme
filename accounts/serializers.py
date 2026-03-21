from rest_framework import serializers
from .models import ScoreUser

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = ScoreUser
        fields = [
            "role",
            "email",
            "username",
            "password_changed",
            "photo",
            "is_active",
            ]
        read_only_fields = ["email","role", "is_active", "password_chaneged"]