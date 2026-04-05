from django.db import models
from accounts.models import ScoreUser
from geography.models import Zone, SubZone


class FrontOffice(models.Model):
    user      = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone      = models.ForeignKey(Zone, on_delete=models.CASCADE)  # ✅ ForeignKey et non OneToOne
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FrontOffice({self.user.email})"


class Huissier(models.Model):
    user    = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone    = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    subZone = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Huissier({self.user.email})"


class FinancialAdvisor(models.Model):
    user    = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone    = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    subZone = models.ForeignKey(SubZone, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"FinancialAdvisor({self.user.email})"