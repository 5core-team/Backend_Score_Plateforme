from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import secrets

from .models import FrontOffice, Huissier, FinancialAdvisor
from accounts.models import ScoreUser, AccountCredentials
from accounts.utils import send_account_setup_email


# ─────────────────────────────────────────────
# CHAMPS COMMUNS POUR CRÉATION D'UTILISATEUR
# ─────────────────────────────────────────────

class BaseStaffSerializer(serializers.ModelSerializer):
    email    = serializers.EmailField(write_only=True, help_text="Email du staff")
    username = serializers.CharField(max_length=100, write_only=True, help_text="Nom d'utilisateur")

    def validate_email(self, value):
        if ScoreUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value

    def _create_user(self, email, username, role):
        user = ScoreUser(
            email=email,
            username=username,
            role=role,
            is_active=False,
        )
        user.set_unusable_password()
        user.save()

        token = secrets.token_urlsafe(32)
        expiry_minutes = getattr(settings, "SETUP_TOKEN_EXPIRY_MINUTES", 1440)

        AccountCredentials.objects.create(
            user=user,
            token=token,
            expiry_date=timezone.now() + timedelta(minutes=expiry_minutes),
        )

        send_account_setup_email(user, token)
        return user


# ─────────────────────────────────────────────
# FRONT OFFICE
# ─────────────────────────────────────────────

class FrontOfficeSerializer(BaseStaffSerializer):
    class Meta:
        model  = FrontOffice
        fields = ['id', 'email', 'username', 'zone', 'is_active']
        extra_kwargs = {
            'zone':      {'help_text': "ID de la zone"},
            'is_active': {'read_only': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        email    = validated_data.pop('email')
        username = validated_data.pop('username')
        user     = self._create_user(email, username, role='front office')
        return FrontOffice.objects.create(user=user, **validated_data)


# ─────────────────────────────────────────────
# HUISSIER
# ─────────────────────────────────────────────

class HuissierSerializer(BaseStaffSerializer):
    class Meta:
        model  = Huissier
        fields = ['id', 'email', 'username', 'zone', 'subZone', 'is_active']
        extra_kwargs = {
            'zone':      {'help_text': "ID de la zone"},
            'subZone':   {'help_text': "ID de la sous-zone"},
            'is_active': {'read_only': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        email    = validated_data.pop('email')
        username = validated_data.pop('username')
        user     = self._create_user(email, username, role='huissier')
        return Huissier.objects.create(user=user, **validated_data)


# ─────────────────────────────────────────────
# FINANCIAL ADVISOR
# ─────────────────────────────────────────────

class FinancialAdvisorSerializer(BaseStaffSerializer):
    class Meta:
        model  = FinancialAdvisor
        fields = ['id', 'email', 'username', 'zone', 'subZone', 'is_active']
        extra_kwargs = {
            'zone':      {'help_text': "ID de la zone"},
            'subZone':   {'help_text': "ID de la sous-zone"},
            'is_active': {'read_only': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        email    = validated_data.pop('email')
        username = validated_data.pop('username')
        user     = self._create_user(email, username, role='conseiller')
        return FinancialAdvisor.objects.create(user=user, **validated_data)