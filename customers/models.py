from django.db import models
from django.utils import timezone
import uuid
import secrets

from geography.models import Zone, SubZone
from staff.models import Huissier
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class Customer(models.Model):
    uuid         = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField(max_length=50)
    npi          = models.CharField(max_length=100, unique=True, verbose_name="National Person ID")
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    credit_score = models.FloatField(default=0.0)

    zone     = models.ForeignKey(Zone,     on_delete=models.SET_NULL, null=True, related_name="customers")
    subZone  = models.ForeignKey(SubZone,  on_delete=models.SET_NULL, null=True, related_name="customers")
    huissier = models.ForeignKey(Huissier, on_delete=models.SET_NULL, null=True, related_name="customers")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def country(self):
        return self.zone.country if self.zone else None

    def __str__(self):
        return f"{self.full_name} ({self.npi})"

    class Meta:
        verbose_name        = "Client"
        verbose_name_plural = "Clients"


# ─────────────────────────────────────────────
# OTP
# ─────────────────────────────────────────────

class ConsultationOTP(models.Model):
    customer    = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='otps')
    code        = models.CharField(max_length=6)
    created_at  = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_used     = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expiry_date

    def __str__(self):
        return f"OTP({self.customer.full_name} - {self.code})"

    class Meta:
        verbose_name        = "OTP de consultation"
        verbose_name_plural = "OTPs de consultation"


# ─────────────────────────────────────────────
# SESSION DE CONSULTATION
# ─────────────────────────────────────────────

class ConsultationSession(models.Model):
    customer    = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sessions')
    token       = models.UUIDField(default=uuid.uuid4, unique=True)
    created_by  = models.ForeignKey('accounts.ScoreUser', on_delete=models.CASCADE)
    created_at  = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_active   = models.BooleanField(default=True)

    def is_valid(self):
        return self.is_active and timezone.now() < self.expiry_date

    def __str__(self):
        return f"Session({self.customer.full_name} - {self.created_by.email})"

    class Meta:
        verbose_name        = "Session de consultation"
        verbose_name_plural = "Sessions de consultation"


# ─────────────────────────────────────────────
# DEBT
# ─────────────────────────────────────────────

class Debt(models.Model):

    PERIODICITY_CHOICES = [
        ('daily',     'Daily'),
        ('weekly',    'Weekly'),
        ('monthly',   'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biannual',  'Biannual'),
        ('annual',    'Annual'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done',    'Done'),
    ]

    VALIDATION_STATUS_CHOICES = [
        ('pending',   'En attente de validation'),
        ('validated', 'Validée par le client'),
        ('rejected',  'Refusée par le client'),
    ]

    uuid            = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # ✅
    customer        = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='debts')
    creditor        = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="receivables")
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    deadline_amount = models.DecimalField(max_digits=10, decimal_places=2)
    periodicity     = models.CharField(max_length=20, choices=PERIODICITY_CHOICES)
    deadline        = models.DateField()
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at      = models.DateField(auto_now_add=True)
    updated_at      = models.DateField(auto_now=True)

    validation_status = models.CharField(
        max_length=10,
        choices=VALIDATION_STATUS_CHOICES,
        default='pending',
        verbose_name="Statut de validation"
    )

    validation_token        = models.CharField(max_length=100, null=True, blank=True, unique=True)
    validation_token_expiry = models.DateTimeField(null=True, blank=True)
    is_monitored            = models.BooleanField(default=False, verbose_name="Suivi activé")
    last_alert_sent         = models.DateField(null=True, blank=True, verbose_name="Dernière alerte envoyée")

    @property
    @extend_schema_field(OpenApiTypes.BOOL)
    def verified(self) -> bool:
        return self.validation_status == 'validated'

    def is_editable(self):
        return self.validation_status != 'validated'

    def generate_validation_token(self):
        self.validation_token        = secrets.token_urlsafe(32)
        self.validation_token_expiry = timezone.now() + timezone.timedelta(days=7)
        self.validation_status       = 'pending'
        self.save(update_fields=[
            'validation_token',
            'validation_token_expiry',
            'validation_status',
        ])
        return self.validation_token

    def is_validation_token_valid(self):
        return (
            self.validation_token is not None and
            self.validation_token_expiry is not None and
            timezone.now() < self.validation_token_expiry and
            self.validation_status == 'pending'
        )

    def __str__(self):
        return f"Debt({self.customer} → {self.creditor} : {self.amount})"

    class Meta:
        verbose_name        = "Dette"
        verbose_name_plural = "Dettes"


# ─────────────────────────────────────────────
# REPAYMENT
# ─────────────────────────────────────────────

class Repayment(models.Model):

    VALIDATION_STATUS_CHOICES = [
        ('pending',   'En attente de validation'),
        ('validated', 'Validé par le client'),
        ('rejected',  'Refusé par le client'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # ✅
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='repayments')
    date = models.DateField()

    validation_status = models.CharField(
        max_length=10,
        choices=VALIDATION_STATUS_CHOICES,
        default='pending',
        verbose_name="Statut de validation"
    )

    validation_token        = models.CharField(max_length=100, null=True, blank=True, unique=True)
    validation_token_expiry = models.DateTimeField(null=True, blank=True)

    @property
    @extend_schema_field(OpenApiTypes.BOOL)
    def verified(self) -> bool:
        return self.validation_status == 'validated'

    def is_editable(self):
        return self.validation_status != 'validated'

    def generate_validation_token(self):
        self.validation_token        = secrets.token_urlsafe(32)
        self.validation_token_expiry = timezone.now() + timezone.timedelta(days=7)
        self.validation_status       = 'pending'
        self.save(update_fields=[
            'validation_token',
            'validation_token_expiry',
            'validation_status',
        ])
        return self.validation_token

    def is_validation_token_valid(self):
        return (
            self.validation_token is not None and
            self.validation_token_expiry is not None and
            timezone.now() < self.validation_token_expiry and
            self.validation_status == 'pending'
        )

    def __str__(self):
        return f"Repayment on {self.date} for Debt #{self.debt.id}"

    class Meta:
        verbose_name        = "Remboursement"
        verbose_name_plural = "Remboursements"