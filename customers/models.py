from django.db import models
from django.utils import timezone
import uuid

from geography.models import Zone, SubZone
from staff.models import Huissier


class Customer(models.Model):
    uuid         = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # ✅ auto-généré
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField(max_length=50)
    npi          = models.CharField(max_length=100, unique=True, verbose_name="National Person ID")
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    credit_score = models.FloatField(default=0.0)

    # Geography
    zone     = models.ForeignKey(Zone,    on_delete=models.SET_NULL, null=True, related_name="customers")
    subZone  = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True, related_name="customers")  # ✅ faute corrigée

    # Staff
    huissier = models.ForeignKey(Huissier, on_delete=models.SET_NULL, null=True, related_name="customers")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def country(self):
        return self.zone.country if self.zone else None  # ✅ via zone

    def __str__(self):
        return f"{self.full_name} ({self.npi})"

    class Meta:
        verbose_name        = "Client"
        verbose_name_plural = "Clients"


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

    customer        = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='debts')
    creditor        = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="receivables")
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    deadline_amount = models.DecimalField(max_digits=10, decimal_places=2)
    periodicity     = models.CharField(max_length=20, choices=PERIODICITY_CHOICES)
    deadline        = models.DateField()
    verified        = models.BooleanField(default=False)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at      = models.DateField(auto_now_add=True)
    updated_at      = models.DateField(auto_now=True)

    def __str__(self):
        return f"Debt({self.customer} → {self.creditor} : {self.amount})"

    class Meta:
        verbose_name        = "Dette"
        verbose_name_plural = "Dettes"


class Repayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='repayments')
    date = models.DateField()

    def __str__(self):
        return f"Repayment on {self.date} for Debt #{self.debt.id}"

    class Meta:
        verbose_name        = "Remboursement"
        verbose_name_plural = "Remboursements"