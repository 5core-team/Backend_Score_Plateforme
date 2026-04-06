from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import secrets

from .models import Country, Zone, SubZone, Subscription
from accounts.models import ScoreUser, AccountCredentials
from accounts.utils import send_account_setup_email


# ─────────────────────────────────────────────
# SUBSCRIPTION SERIALIZER
# ─────────────────────────────────────────────

class SubscriptionSerializer(serializers.ModelSerializer):
    is_active    = serializers.SerializerMethodField(help_text="Abonnement actif ou non")
    country_name = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model  = Subscription
        fields = ['id', 'country', 'country_name', 'created_at', 'expires_in', 'is_active']
        extra_kwargs = {
            'country':    {'write_only': True, 'help_text': "ID du pays"},
            'expires_in': {'help_text': "Date d'expiration de l'abonnement"},
            'created_at': {'read_only': True},
        }

    def get_is_active(self, obj):
        return obj.is_active()


# ─────────────────────────────────────────────
# COUNTRY SERIALIZER
# ─────────────────────────────────────────────

class CountrySerializer(serializers.ModelSerializer):
    email    = serializers.EmailField(write_only=True, help_text="Email du manager du pays")
    username = serializers.CharField(max_length=100, write_only=True, help_text="Nom d'utilisateur du manager")

    # ✅ Champs en lecture seule
    has_valid_subscription = serializers.BooleanField(read_only=True, help_text="Abonnement valide ou non")

    class Meta:
        model  = Country
        fields = [
            'id',
            'name',
            'iso_code',
            'phone_code',           # ✅ ajouté
            'licence_status',       # ✅ ajouté
            'has_valid_subscription', # ✅ ajouté
            'email',
            'username',
        ]
        extra_kwargs = {
            'name':           {'help_text': "Nom du pays"},
            'iso_code':       {'help_text': "Code ISO du pays (ex: BJ, FR)"},
            'phone_code':     {'help_text': "Indicatif téléphonique (ex: +229)", 'required': False},
            'licence_status': {'help_text': "Statut de la licence", 'read_only': True},
        }

    def validate(self, attrs: dict):
        data = super().validate(attrs)

        if ScoreUser.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({'email': 'Account already exists'})

        if Country.objects.filter(iso_code=data.get('iso_code')).exists():
            raise serializers.ValidationError({'iso_code': 'This country already exists'})

        return data

    @transaction.atomic
    def create(self, validated_data: dict):
        email    = validated_data.pop('email')
        username = validated_data.pop('username')

        user = ScoreUser(
            email=email,
            username=username,
            role='country',
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

        country = Country.objects.create(manager=user, **validated_data)
        send_account_setup_email(user, token)
        return country


# ─────────────────────────────────────────────
# ZONE SERIALIZER
# ─────────────────────────────────────────────

class ZoneSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source='country.name',
        read_only=True,
        help_text="Nom du pays"
    )

    class Meta:
        model  = Zone
        fields = ['id', 'name', 'country', 'country_name']
        extra_kwargs = {
            'country': {
                'write_only': True,
                'help_text':  "ID du pays",
                'required':   False,
            },
            'name': {'help_text': "Nom de la zone"},
        }


# ─────────────────────────────────────────────
# SUBZONE SERIALIZER
# ─────────────────────────────────────────────

class SubZoneSerializer(serializers.ModelSerializer):
    zone_name    = serializers.CharField(
        source='zone.name',
        read_only=True,
        help_text="Nom de la zone parente"
    )
    country_name = serializers.CharField(
        source='zone.country.name',
        read_only=True,
        help_text="Nom du pays"
    )

    class Meta:
        model  = SubZone
        fields = ['id', 'name', 'zone', 'zone_name', 'country_name']
        extra_kwargs = {
            'zone': {'write_only': True, 'help_text': "ID de la zone parente"},
            'name': {'help_text': "Nom de la sous-zone"},
        }