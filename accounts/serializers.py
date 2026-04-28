from rest_framework import serializers
from .models import ScoreUser


# ─────────────────────────────────────────────
# PROFIL UTILISATEUR — Lecture
# ─────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ScoreUser
        fields = [
            "role",
            "email",
            "username",
            "password_changed",
            "photo",
            "is_active",
        ]
        read_only_fields = ["email", "role", "is_active", "password_changed"]


# ─────────────────────────────────────────────
# UPDATE USERNAME — username uniquement
# ─────────────────────────────────────────────

class UpdateUsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ScoreUser
        fields = ["username"]

    def validate_username(self, value):
        qs = ScoreUser.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Ce nom d'utilisateur est déjà utilisé."
            )
        return value


# ─────────────────────────────────────────────
# UPDATE PHOTO — photo uniquement
# ─────────────────────────────────────────────

class UpdatePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ScoreUser
        fields = ["photo"]

    def validate_photo(self, value):
        # ✅ Vérifier que c'est bien une image
        if value:
            allowed = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            if hasattr(value, 'content_type') and value.content_type not in allowed:
                raise serializers.ValidationError(
                    "Format non supporté. Utilisez JPEG, PNG ou WEBP."
                )
        return value


# ─────────────────────────────────────────────
# CHANGEMENT MOT DE PASSE — Demande
# ─────────────────────────────────────────────

class ChangePasswordRequestSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        write_only=True,
        min_length=6,
        help_text="Nouveau mot de passe (minimum 6 caractères)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirmation du nouveau mot de passe"
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": "Les mots de passe ne correspondent pas."}
            )
        return attrs


# ─────────────────────────────────────────────
# LOGIN REQUEST
# ─────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        help_text="Adresse email de l'utilisateur"
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Mot de passe"
    )


# ─────────────────────────────────────────────
# LOGIN RESPONSE
# ─────────────────────────────────────────────

class LoginResponseSerializer(serializers.Serializer):
    access_token  = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    type_user     = serializers.CharField(help_text="Rôle de l'utilisateur")


# ─────────────────────────────────────────────
# ERROR FORMAT
# ─────────────────────────────────────────────

class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Message d'erreur")