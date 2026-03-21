from django.db import models

# customer/models.py
from django.db import models
from users.models import ScoreUser  # Pour faire le lien avec les huissiers
from country.models import Country, FrontOffice, Huissier

class Customer(models.Model):
    uuid = models.CharField(max_length=200, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    npi = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20)
    credit_score = models.FloatField(default=0.0)
    front_office = models.ForeignKey(FrontOffice, on_delete=models.SET_NULL, null=True, blank=True)
    zone = models.CharField(max_length=500)
    huissier = models.ForeignKey(Huissier, on_delete=models.SET_NULL, null=True) # ID de l'huissier qui a créer le compte
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    # huissier = models.ForeignKey(ScoreUser, on_delete=models.CASCADE, limit_choices_to={'role': 'huissier'})

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Loan(models.Model):
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

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    creditor_npi = models.CharField(verbose_name="NPI du créancier", null=True)
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    periodicity = models.CharField(max_length=20, choices=PERIODICITY_CHOICES)
    # rate = models.FloatField()
    deadline_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField()
    verified = models.BooleanField(default=False)
    solvability = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Loan #{self.id} - {self.customer}"

class Repayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    date = models.DateField()

    def __str__(self):
        return f"Repayment on {self.date} for Loan #{self.loan.id}"

