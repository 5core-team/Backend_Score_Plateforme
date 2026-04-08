from rest_framework import serializers
from .models import ScoreUser


# ─────────────────────────────────────────────
# PROFIL UTILISATEUR
# ─────────────────────────────────────────────

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
        read_only_fields = ["email", "role", "is_active", "password_changed"]  # ✅ DANS Meta


# ─────────────────────────────────────────────
# LOGIN REQUEST
# ─────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        help_text="Adresse email de l'utilisateur"  # apparaît dans Swagger
    )
    password = serializers.CharField(
        write_only=True,           # ✅ n'apparaît pas dans les réponses
        style={"input_type": "password"},
        help_text="Mot de passe"
    )


# ─────────────────────────────────────────────
# LOGIN RESPONSE
# ─────────────────────────────────────────────

class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    type_user = serializers.CharField(help_text="Rôle de l'utilisateur (ex: admin, user)")


# ─────────────────────────────────────────────
# ERROR FORMAT
# ─────────────────────────────────────────────

class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Message d'erreur")