from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import random
import uuid

from .models import Customer, ConsultationOTP, ConsultationSession, Debt, Repayment
from accounts.utils import send_email, send_customer_creation_email


# ─────────────────────────────────────────────
# CUSTOMER SERIALIZER
# ─────────────────────────────────────────────

class CustomerSerializer(serializers.ModelSerializer):
    full_name    = serializers.CharField(read_only=True)
    country_name = serializers.CharField(source='zone.country.name', read_only=True)
    zone_name    = serializers.CharField(source='zone.name', read_only=True)
    subzone_name = serializers.CharField(source='subZone.name', read_only=True)

    class Meta:
        model  = Customer
        fields = [
            'uuid',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'npi',
            'phone_number',
            'credit_score',
            'zone',
            'zone_name',
            'subZone',
            'subzone_name',
            'country_name',
            'huissier',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'uuid':         {'read_only': True},
            'credit_score': {'read_only': True},
            'zone':         {'read_only': True},
            'subZone':      {'read_only': True},
            'huissier':     {'read_only': True},
            'created_at':   {'read_only': True},
            'updated_at':   {'read_only': True},
        }

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields['first_name'].read_only   = True
            fields['last_name'].read_only    = True
            fields['email'].read_only        = True
            fields['npi'].read_only          = True
            fields['phone_number'].read_only = True
        return fields

    def validate_email(self, value):
        from accounts.models import ScoreUser
        if ScoreUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Cet email est déjà utilisé par un utilisateur du système."
            )
        qs = Customer.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Un client avec cet email existe déjà."
            )
        return value

    def validate_npi(self, value):
        qs = Customer.objects.filter(npi=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Un client avec ce NPI existe déjà."
            )
        return value

    def validate_phone_number(self, value):
        if not value:
            return value
        qs = Customer.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Un client avec ce numéro de téléphone existe déjà."
            )
        return value

    def create(self, validated_data):
        customer = super().create(validated_data)
        if customer.huissier and customer.huissier.user:
            huissier_username = (
                customer.huissier.name
                if customer.huissier.name
                else customer.huissier.user.username
            )
        else:
            huissier_username = "un huissier"
        send_customer_creation_email(customer, huissier_username)
        return customer


# ─────────────────────────────────────────────
# CUSTOMER SEARCH SERIALIZER
# ─────────────────────────────────────────────

class CustomerSearchSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = Customer
        fields = ['uuid', 'full_name', 'npi', 'email', 'phone_number']


# ─────────────────────────────────────────────
# OTP REQUEST SERIALIZER
# ─────────────────────────────────────────────

class ConsultationOTPRequestSerializer(serializers.Serializer):
    customer_uuid = serializers.UUIDField(help_text="UUID du client à consulter")

    def validate_customer_uuid(self, value):
        if not Customer.objects.filter(uuid=value).exists():
            raise serializers.ValidationError("Client introuvable.")
        return value

    def send_otp(self):
        customer_uuid = self.validated_data['customer_uuid']
        customer      = Customer.objects.get(uuid=customer_uuid)

        last_otp = ConsultationOTP.objects.filter(
            customer=customer,
            is_used=False
        ).order_by('-created_at').first()

        if last_otp and timezone.now() - last_otp.created_at < timedelta(seconds=60):
            raise serializers.ValidationError(
                {"error": "Veuillez attendre avant de demander un nouveau code."}
            )

        code        = str(random.randint(100000, 999999))
        expiry_mins = getattr(settings, "CONSULTATION_OTP_EXPIRY_MINUTES", 10)

        ConsultationOTP.objects.create(
            customer=customer,
            code=code,
            expiry_date=timezone.now() + timedelta(minutes=expiry_mins),
        )

        send_email({
            "subject": "Code d'autorisation de consultation Score",
            "message": (
                f"Bonjour {customer.full_name},\n\n"
                f"Un huissier ou conseiller financier souhaite consulter votre compte.\n\n"
                f"Votre code d'autorisation est : {code}\n\n"
                f"Ce code est valable {expiry_mins} minutes.\n\n"
                f"Si vous n'avez pas demandé cette consultation, ignorez ce message.\n\n"
                f"Cordialement,\nL'équipe Score"
            ),
            "to": customer.email,
        })

        return customer


# ─────────────────────────────────────────────
# OTP VERIFY SERIALIZER
# ─────────────────────────────────────────────

class ConsultationOTPVerifySerializer(serializers.Serializer):
    customer_uuid = serializers.UUIDField(help_text="UUID du client")
    code          = serializers.CharField(max_length=6, help_text="Code OTP reçu par le client")

    def validate(self, attrs):
        customer_uuid = attrs.get('customer_uuid')
        code          = attrs.get('code')

        try:
            customer = Customer.objects.get(uuid=customer_uuid)
        except Customer.DoesNotExist:
            raise serializers.ValidationError({"customer_uuid": "Client introuvable."})

        otp = ConsultationOTP.objects.filter(
            customer=customer,
            code=code,
            is_used=False,
        ).order_by('-created_at').first()

        if not otp:
            raise serializers.ValidationError({"code": "Code invalide."})

        if not otp.is_valid():
            raise serializers.ValidationError({"code": "Code expiré."})

        attrs['customer'] = customer
        attrs['otp']      = otp
        return attrs


# ─────────────────────────────────────────────
# CONSULTATION SESSION SERIALIZER
# ─────────────────────────────────────────────

class ConsultationSessionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    is_valid      = serializers.SerializerMethodField()

    class Meta:
        model  = ConsultationSession
        fields = [
            'id',
            'token',
            'customer',
            'customer_name',
            'created_at',
            'expiry_date',
            'is_active',
            'is_valid',
        ]
        extra_kwargs = {
            'token':      {'read_only': True},
            'created_at': {'read_only': True},
        }

    def get_is_valid(self, obj):
        return obj.is_valid()


# ─────────────────────────────────────────────
# REPAYMENT SERIALIZER
# ─────────────────────────────────────────────

class RepaymentSerializer(serializers.ModelSerializer):

    # ✅ Champs write_only visibles dans Swagger — gérés par la vue, supprimés avant save()
    session_token = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Token de session OTP valide — récupéré depuis la réponse de verify-otp"
    )
    debt_uuid = serializers.UUIDField(
        write_only=True,
        required=True,
        help_text="UUID de la dette concernée par le remboursement"
    )

    class Meta:
        model  = Repayment
        fields = [
            'uuid',
            'session_token',
            'debt_uuid',
            'amount',
            'date',
            'debt',
            'validation_status',
        ]
        extra_kwargs = {
            'uuid':              {'read_only': True},
            'debt':              {'read_only': True, 'help_text': "Déduit automatiquement depuis debt_uuid"},
            'amount':            {'help_text': "Montant remboursé lors de ce versement (ex: 5000.00)"},
            'date':              {'help_text': "Date du remboursement (YYYY-MM-DD)"},
            'validation_status': {'read_only': True, 'help_text': "Statut : pending | validated | rejected"},
        }

    def validate(self, attrs):
        attrs.pop('session_token', None)
        attrs.pop('debt_uuid', None)
        return attrs


# ─────────────────────────────────────────────
# DEBT SERIALIZER
# ─────────────────────────────────────────────

class DebtSerializer(serializers.ModelSerializer):
    repayments    = RepaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_uuid = serializers.UUIDField(source='customer.uuid', read_only=True)
    creditor_name = serializers.CharField(
        source='creditor.full_name',
        read_only=True,
        default=None
    )
    # ✅ UUID du créditeur retourné en réponse
    creditor_uuid = serializers.UUIDField(
        source='creditor.uuid',
        read_only=True,
        default=None
    )

    # ✅ Champs write_only visibles dans Swagger — gérés par la vue, supprimés avant save()
    session_token = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Token de session OTP valide — récupéré depuis la réponse de verify-otp"
    )
    customer_uuid_field = serializers.UUIDField(
        write_only=True,
        required=True,
        help_text="UUID du client — récupéré depuis la réponse de verify-otp"
    )
    # ✅ CORRECTION : UUID du créditeur au lieu de son ID numérique
    creditor_uuid_field = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="UUID du client créditeur (optionnel) — retourné à la création du client"
    )

    class Meta:
        model  = Debt
        fields = [
            'uuid',
            'id',
            # ✅ Champs à envoyer par le frontend
            'session_token',
            'customer_uuid_field',
            'creditor_uuid_field',
            'amount',
            'deadline_amount',
            'periodicity',
            'deadline',
            'status',
            # ✅ Champs retournés en réponse uniquement
            'customer',
            'customer_uuid',
            'customer_name',
            'creditor_uuid',
            'creditor_name',
            'verified',
            'validation_status',
            'is_monitored',
            'created_at',
            'updated_at',
            'repayments',
        ]
        extra_kwargs = {
            'uuid': {'read_only': True},
            'customer': {
                'read_only': True,
                'help_text': "Déduit automatiquement depuis la session — ne pas envoyer",
            },
            'amount':            {'help_text': "Montant total de la dette (ex: 150000.00)"},
            'deadline_amount':   {'help_text': "Montant dû à chaque échéance (ex: 12500.00)"},
            'periodicity':       {'help_text': "Fréquence : daily | weekly | monthly | quarterly | biannual | annual"},
            'deadline':          {'help_text': "Date limite de remboursement (YYYY-MM-DD)"},
            'status':            {'help_text': "Statut à la création : toujours 'pending'"},
            'verified':          {'read_only': True, 'help_text': "True si validée par le client"},
            'validation_status': {'read_only': True, 'help_text': "pending | validated | rejected"},
            'is_monitored':      {'read_only': True, 'help_text': "Suivi activé — false par défaut"},
            'created_at':        {'read_only': True},
            'updated_at':        {'read_only': True},
        }

    def validate(self, attrs):
        attrs.pop('session_token', None)
        attrs.pop('customer_uuid_field', None)
        attrs.pop('creditor_uuid_field', None)
        return attrs