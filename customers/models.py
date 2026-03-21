from django.db import models
from geography.models import Zone, SubZone, Country
from staff.models import Huissier

class Customer(models.Model):
    uuid = models.CharField(max_length=200, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    npi = models.CharField(max_length=100, unique=True, verbose_name="National Person ID")
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    credit_score = models.FloatField(default=0.0)

    # Geography
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, related_name="customers")
    zubZone = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True, related_name="customers")
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, related_name='customers')

    huissier = models.ForeignKey(Huissier, on_delete=models.SET_NULL, null=True, related_name="customers")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Debt(models.Model):
    PERIODICITY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biannual', 'Biannual'),
        ('annual', 'Annual'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='debts')
    creditor = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="receivables")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deadline_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    periodicity = models.CharField(max_length=20, choices=PERIODICITY_CHOICES)
    deadline = models.DateField()
    
    verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending') # Check is a debt is ongoing or not


class Repayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='repayments')
    date = models.DateField()

    def __str__(self):
        return f"Repayment on {self.date} for Loan #{self.debt.id}"
