from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import random
import uuid

from .models import Customer, ConsultationOTP, ConsultationSession, Debt, Repayment
from accounts.utils import send_email


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
            'zone':         {'read_only': True},    # ✅ déduit automatiquement
            'subZone':      {'read_only': True},    # ✅ déduit automatiquement
            'huissier':     {'read_only': True},    # ✅ déduit automatiquement
            'created_at':   {'read_only': True},
            'updated_at':   {'read_only': True},
        }


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
    class Meta:
        model  = Repayment
        fields = [
            'uuid',              # ✅
            'debt',
            'date',
            'validation_status',
        ]
        extra_kwargs = {
            'uuid':              {'read_only': True},
            'debt':              {'help_text': "ID de la dette"},
            'date':              {'help_text': "Date du remboursement"},
            'validation_status': {'read_only': True, 'help_text': "Statut de validation"},
        }


# ─────────────────────────────────────────────
# DEBT SERIALIZER
# ─────────────────────────────────────────────

class DebtSerializer(serializers.ModelSerializer):
    repayments    = RepaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_uuid = serializers.UUIDField(source='customer.uuid', read_only=True)
    creditor_name = serializers.CharField(source='creditor.full_name', read_only=True)

    class Meta:
        model  = Debt
        fields = [
            'uuid',              # ✅
            'id',
            'customer',
            'customer_uuid',
            'customer_name',
            'creditor',
            'creditor_name',
            'amount',
            'deadline_amount',
            'periodicity',
            'deadline',
            'verified',
            'status',
            'validation_status',
            'is_monitored',
            'created_at',
            'updated_at',
            'repayments',
        ]
        extra_kwargs = {
            'uuid':              {'read_only': True},
            'customer':          {'write_only': True, 'help_text': "ID du client débiteur"},
            'creditor':          {'write_only': True, 'help_text': "ID du client créditeur", 'required': False},
            'amount':            {'help_text': "Montant de la dette"},
            'deadline_amount':   {'help_text': "Montant dû à l'échéance"},
            'periodicity':       {'help_text': "Périodicité de remboursement"},
            'deadline':          {'help_text': "Date limite de remboursement"},
            'verified':          {'read_only': True, 'help_text': "Dette vérifiée ou non"},
            'status':            {'help_text': "Statut : pending ou done"},
            'validation_status': {'read_only': True, 'help_text': "Statut de validation"},
            'is_monitored':      {'read_only': True, 'help_text': "Suivi activé ou non"},
            'created_at':        {'read_only': True},
            'updated_at':        {'read_only': True},
        }