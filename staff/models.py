from django.db import models
from accounts.models import ScoreUser
from geography.models import Zone, SubZone

class FrontOffice(models.Model):
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone = models.OneToOneField(Zone, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True)

class Huissier(models.Model):
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone = models.OneToOneField(Zone, on_delete=models.SET_NULL, null=True)
    subZone = models.OneToOneField(SubZone, on_delete=models.SET_NULL, null=True)

    is_active = models.BooleanField(default=True)

class FinancialAdvisor(models.Model):
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)
    zone = models.OneToOneField(Zone, on_delete=models.SET_NULL, null=True)
    subZone = models.OneToOneField(SubZone, on_delete=models.SET_NULL, null=True)

    is_active = models.BooleanField(default=True)