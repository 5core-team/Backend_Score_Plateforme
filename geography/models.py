from django.db import models
from accounts.models import ScoreUser


class Country(models.Model):
    name       = models.CharField(max_length=255)
    iso_code   = models.CharField(max_length=10, unique=True)
    manager    = models.OneToOneField(ScoreUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.iso_code})"

    @property
    def has_valid_subscription(self):
        # À implémenter plus tard
        return False


class Zone(models.Model):
    name    = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='zones')

    class Meta:
        unique_together = ['name', 'country']

    def __str__(self):
        return f"{self.name} - {self.country.name}"


class SubZone(models.Model):
    name = models.CharField(max_length=255)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='subzones')
    # ✅ country supprimé — accessible via zone.country

    class Meta:
        unique_together = ['name', 'zone']

    def __str__(self):
        return f"{self.name} - {self.zone.name}"