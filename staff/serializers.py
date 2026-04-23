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

    def validate_username(self, value):
        # ✅ Unicité du username parmi tous les utilisateurs
        if ScoreUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return value

    def validate_npi(self, value):
        if not value:
            return value
        # ✅ Unicité du NPI parmi tous les profils staff
        npi_exists = (
            FrontOffice.objects.filter(npi=value).exists() or
            Huissier.objects.filter(npi=value).exists() or
            FinancialAdvisor.objects.filter(npi=value).exists()
        )
        if npi_exists:
            raise serializers.ValidationError("Ce NPI est déjà utilisé par un autre utilisateur.")
        return value

    def validate_phone(self, value):
        if not value:
            return value
        # ✅ Unicité du téléphone parmi tous les profils staff
        phone_exists = (
            FrontOffice.objects.filter(phone=value).exists() or
            Huissier.objects.filter(phone=value).exists() or
            FinancialAdvisor.objects.filter(phone=value).exists()
        )
        if phone_exists:
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé par un autre utilisateur.")
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

        token          = secrets.token_urlsafe(32)
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
        fields = ['id', 'email', 'username', 'zone', 'name', 'npi', 'phone', 'is_active']
        extra_kwargs = {
            'zone': {
                'read_only': True,
                'help_text': "Déduite automatiquement depuis le représentant pays connecté",
            },
            'name':      {'help_text': "Nom du front office", 'required': False},
            'npi':       {'help_text': "Numéro de pièce d'identité (unique)", 'required': False},
            'phone':     {'help_text': "Numéro de téléphone (unique)", 'required': False},
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
        # ✅ Champ picture supprimé
        fields = ['id', 'email', 'username', 'zone', 'subZone', 'name', 'npi', 'phone', 'is_active']
        extra_kwargs = {
            'zone': {
                'read_only': True,
                'help_text': "Déduite automatiquement depuis le front office connecté",
            },
            'subZone': {
                'help_text': "ID de la sous-zone (doit appartenir à la zone du front office)",
                'required':  True,
            },
            'name':      {'help_text': "Nom de l'huissier", 'required': False},
            'npi':       {'help_text': "Numéro de pièce d'identité (unique)", 'required': False},
            'phone':     {'help_text': "Numéro de téléphone (unique)", 'required': False},
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
        # ✅ Champ picture supprimé
        fields = ['id', 'email', 'username', 'zone', 'subZone', 'name', 'npi', 'phone', 'is_active']
        extra_kwargs = {
            'zone': {
                'read_only': True,
                'help_text': "Déduite automatiquement depuis le front office connecté",
            },
            'subZone': {
                'help_text': "ID de la sous-zone (doit appartenir à la zone du front office)",
                'required':  True,
            },
            'name':      {'help_text': "Nom du conseiller financier", 'required': False},
            'npi':       {'help_text': "Numéro de pièce d'identité (unique)", 'required': False},
            'phone':     {'help_text': "Numéro de téléphone (unique)", 'required': False},
            'is_active': {'read_only': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        email    = validated_data.pop('email')
        username = validated_data.pop('username')
        user     = self._create_user(email, username, role='conseiller')
        return FinancialAdvisor.objects.create(user=user, **validated_data)