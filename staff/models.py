from django.db import models
from accounts.models import ScoreUser
from geography.models import Zone, SubZone


class FrontOffice(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone      = models.ForeignKey(Zone, on_delete=models.CASCADE)
    name      = models.CharField(max_length=255, null=True, blank=True)  # ✅ ajouté
    npi       = models.CharField(max_length=200, null=True, blank=True)  # ✅ ajouté
    phone     = models.CharField(max_length=100, null=True, blank=True)  # ✅ ajouté
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FrontOffice({self.user.email})"


class Huissier(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone      = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    subZone   = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True)
    npi       = models.CharField(max_length=100, null=True, blank=True)  # ✅ ajouté
    phone     = models.CharField(max_length=200, null=True, blank=True)  # ✅ ajouté
    picture   = models.ImageField(upload_to='huissiers/', null=True, blank=True)  # ✅ ajouté
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Huissier({self.user.email})"


class FinancialAdvisor(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone      = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    subZone   = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True)
    name      = models.CharField(max_length=255, null=True, blank=True)  # ✅ ajouté
    npi       = models.CharField(max_length=100, null=True, blank=True)  # ✅ ajouté
    phone     = models.CharField(max_length=100, null=True, blank=True)  # ✅ ajouté
    picture   = models.ImageField(upload_to='financials/', null=True, blank=True)  # ✅ ajouté
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FinancialAdvisor({self.user.email})"