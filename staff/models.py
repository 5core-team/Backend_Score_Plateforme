from django.db import models
from accounts.models import ScoreUser
from geography.models import Zone, SubZone


class FrontOffice(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    # ✅ related_name explicite pour les annotations du dashboard
    zone      = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='frontoffices')
    name      = models.CharField(max_length=255, null=True, blank=True)
    npi       = models.CharField(max_length=200, null=True, blank=True)
    phone     = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FrontOffice({self.user.email})"


class Huissier(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    # ✅ related_name explicite
    zone      = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, related_name='huissiers')
    subZone   = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True, related_name='huissiers')
    npi       = models.CharField(max_length=100, null=True, blank=True)
    phone     = models.CharField(max_length=200, null=True, blank=True)
    picture   = models.ImageField(upload_to='huissiers/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Huissier({self.user.email})"


class FinancialAdvisor(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    # ✅ related_name explicite
    zone      = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, related_name='financial_advisors')
    subZone   = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True, related_name='financial_advisors')
    name      = models.CharField(max_length=255, null=True, blank=True)
    npi       = models.CharField(max_length=100, null=True, blank=True)
    phone     = models.CharField(max_length=100, null=True, blank=True)
    picture   = models.ImageField(upload_to='financials/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FinancialAdvisor({self.user.email})"