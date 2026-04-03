from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import secrets

from .models import Country, Zone, SubZone
from accounts.models import ScoreUser, AccountCredentials


# ─────────────────────────────────────────────
# COUNTRY SERIALIZER
# ─────────────────────────────────────────────

class CountrySerializer(serializers.ModelSerializer):
    # Champs write-only liés au manager, pas au modèle Country directement
    email = serializers.EmailField(
        write_only=True,
        help_text="Email du manager du pays"
    )
    username = serializers.CharField(
        max_length=100,
        write_only=True,
        help_text="Nom d'utilisateur du manager"
    )

    class Meta:
        model = Country
        fields = ['name', 'iso_code', 'email', 'username']
        extra_kwargs = {  # ✅ extra_kwargs et non extras_fields
            'name':     {'help_text': "Nom du pays"},
            'iso_code': {'help_text': "Code ISO du pays (ex: BJ, FR)"},
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
        # Extraire les champs non liés au modèle Country
        email    = validated_data.pop('email')
        username = validated_data.pop('username')

        # Créer l'utilisateur manager
        user = ScoreUser(
            email=email,
            username=username,
            role='country',
            is_active=False,
        )
        user.set_unusable_password()
        user.save()

        # Créer les credentials avec expiry_date
        expiry_minutes = getattr(settings, "SETUP_TOKEN_EXPIRY_MINUTES", 1440)  # 24h par défaut
        AccountCredentials.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expiry_date=timezone.now() + timedelta(minutes=expiry_minutes),  # ✅ ajouté
        )

        # Créer le pays
        country = Country.objects.create(
            manager=user,
            **validated_data  # iso_code + name restants
        )

        return country


# ─────────────────────────────────────────────
# ZONE SERIALIZER
# ─────────────────────────────────────────────

class ZoneSerializer(serializers.ModelSerializer):
    # Lecture : affiche le nom du pays | Écriture : on passe l'id
    country_name = serializers.CharField(
        source='country.name',
        read_only=True,
        help_text="Nom du pays associé à la zone"
    )

    class Meta:
        model = Zone
        fields = ['id', 'name', 'country', 'country_name']
        extra_kwargs = {
            'country': {
                'write_only': True,   # on envoie l'id en écriture
                'help_text': "ID du pays"
            },
            'name': {'help_text': "Nom de la zone"},
        }


# ─────────────────────────────────────────────
# SUBZONE SERIALIZER
# ─────────────────────────────────────────────

class SubZoneSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(
        source='zone.name',
        read_only=True,
        help_text="Nom de la zone parente"
    )
    country_name = serializers.CharField(
        source='zone.country.name',  # ✅ accès via zone → country
        read_only=True,
        help_text="Nom du pays"
    )

    class Meta:
        model = SubZone
        fields = ['id', 'name', 'zone', 'zone_name', 'country_name']
        extra_kwargs = {
            'zone': {
                'write_only': True,
                'help_text': "ID de la zone parente"
            },
            'name': {'help_text': "Nom de la sous-zone"},
        }